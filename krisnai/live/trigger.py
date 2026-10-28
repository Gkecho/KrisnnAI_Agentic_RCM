# ruff: noqa: E501
"""Trigger: a new appointment appears in the EMR -> eligibility 270 -> mock clearinghouse -> payer sim -> 271, with every detail.

A watcher polls the EMR (read-only: it only GETs /appointment and /patient) and remembers which appointment versions it has already
seen, so the same booking never fires twice and a restart does not replay the past. For each new booking it builds the 270 for
the visit date, sends it through the mock clearinghouse (answered by the payer sim), reads the 271 back and decodes it.

Demo only, synthetic data, local only. Polling is the approach that needs nothing from the EMR vendor; a real feed (HL7 SIU or a
FHIR notification) would call `check()` in the same way. If a booking has no payer written on it (a hand-typed one has none), the
demo payer is assumed and the member is enrolled with it; that assumption is printed, never hidden.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from krisnai.agents.a1_clearance import config as a1_config
from krisnai.agents.a1_clearance import rules as a1_rules
from krisnai.agents.a1_clearance.agent import ACTION_BY_GAP
from krisnai.ingest.eligibility import parse_271
from krisnai.ingest.x12 import X12Error, read_transactions
from krisnai.integrations.clearinghouse.client import ClearinghouseClient
from krisnai.integrations.clearinghouse.mock_server import create_app as create_clearinghouse
from krisnai.integrations.clearinghouse.x12_out import write_270
from krisnai.integrations.openemr import seed
from krisnai.live import cob_order, prior_auth
from krisnai.live.insurance import InsuranceReader, Policy
from krisnai.live.payer import PayerSim
from krisnai.live.s1 import PAYER_ID, PAYER_NAME, TOKEN, _free_port, _Srv
from krisnai.live.shadow_book import ShadowBook
from krisnai.live.world import LiveWorld
from krisnai.live.writeback import WriteBack, WriteBackError

RELATION_CODE = {"spouse": "01", "child": "19"}  # INS02; anything else is sent as G8 (other relationship). Confirm with the payer.
CANCELLED = {"x", "%"}  # OpenEMR appointment statuses for cancelled
NOTE = {  # what each kind of line is, in plain words
    "ISA": "Envelope: who sent it and who receives it", "GS": "Group header: 270 = HS, 271 = HB", "ST": "Start of the message",
    "BHT": "Start of the question or the answer", "HL": "A level marker (payer, clinic, patient)",
    "NM1*PR": "The insurer (payer)", "NM1*1P": "The provider the visit is with", "NM1*IL": "The policyholder (subscriber) and member ID", "NM1*03": "The dependent: the patient, when not the policyholder",
    "INS": "How the dependent relates to the policyholder (19 child, 01 spouse)",
    "TRN": "Trace number that ties the answer to the question", "DMG": "Patient birth date", "DTP*291": "Date of the visit the answer applies to",
    "DTP*346": "Plan start date", "DTP*347": "Plan end date", "EQ": "The question: general benefits (service type 30)",
    "EB*1": "Answer: coverage is ACTIVE", "EB*6": "Answer: coverage is NOT active", "EB*R": "Another payer is primary",
    "EB*A": "Coinsurance: share of the cost the patient pays", "EB*C": "Deductible still to be met", "EB*B": "Copayment due at the visit",
    "AAA": "Rejection reason: the payer could not find this member",
    "UM": "What is being asked: a health-services review, initial request", "HCR": "The payer's review answer (A1 certified, A3 not certified, A4 pended) and the authorization number",
    "HSD": "Units (visits) approved", "SV1": "The service asked about: procedure code and units", "HI": "Diagnosis code the request is for",
    "NM1*X3": "The payer that decides the authorization", "MSG": "Free-text message from the payer", "SE": "End of the message", "GE": "End of the group", "IEA": "End of the envelope",
}  # fmt: skip


def _note(seg) -> str:  # noqa: ANN001
    for key in (f"{seg.id}*{seg[1]}", seg.id):
        if key in NOTE:
            return NOTE[key]
    return ""


def explain(x12: str) -> list[dict]:
    """Every line of an X12 message with its plain-words meaning."""
    out = []
    for tx in read_transactions(x12):
        out += [{"text": "*".join(s.els), "note": _note(s)} for s in tx.segments]
    return out


class AppointmentWatcher:
    """Read-only. `poll()` returns appointments (with their patient's member id) not seen before; `mark()` records them as handled."""

    def __init__(self, server, state: Path):  # noqa: ANN001
        self.server, self.state = server, state
        self.seen: set[str] = set(json.loads(state.read_text(encoding="utf-8"))) if state.exists() else set()

    @staticmethod
    def key(row: dict) -> str:
        return f"{row['pc_eid']}:{row.get('pc_eventDate')}:{row.get('pc_startTime')}"  # a moved appointment is a new version

    def _save(self) -> None:
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self.state.write_text(json.dumps(sorted(self.seen)), encoding="utf-8")

    def baseline(self) -> int:
        """Mark everything already in the EMR as seen, so only bookings made from now on fire."""
        self.seen |= {self.key(r) for r in self.server.rest_rows("/appointment")}
        self._save()
        return len(self.seen)

    def _with_patient(self, rows: list[dict]) -> list[dict]:
        who = {str(p["pid"]): p for p in self.server.rest_rows("/patient")}
        out = []
        for r in sorted(rows, key=lambda r: int(r["pc_eid"])):
            p = who.get(str(r["pid"]), {})
            out.append(
                {**r, "member": p.get("pubpid") or r["lname"], "uuid": p.get("uuid", ""), "event_id": self.key(r)}
            )
        return out

    def poll(self) -> list[dict]:
        rows = [r for r in self.server.rest_rows("/appointment") if self.key(r) not in self.seen]
        return self._with_patient(rows) if rows else []

    def current(self, eids: set[str]) -> dict[str, dict]:
        """The appointments with these ids as they are in the EMR now (a re-check must not use yesterday's picture)."""
        rows = [r for r in self.server.rest_rows("/appointment") if str(r["pc_eid"]) in eids]
        return {str(r["pc_eid"]): r for r in self._with_patient(rows)}

    def mark(self, event_id: str) -> None:
        self.seen.add(event_id)
        self._save()


class Trigger:
    """Owns the watcher, a local mock clearinghouse and the payer sim. `tick()` handles whatever is new or due.

    For each booking it reads the patient's insurance records from the EMR, sends one 270 per policy (primary first), and applies the
    Gatekeeper (A1) rules to the answers. 3 days and 1 day before each visit it checks again. A booking whose patient has no insurance
    on file is an exception for the front desk; no payer is assumed unless `assume_missing` is set (demo only).
    """

    def __init__(
        self,
        server,
        out: Path,
        as_of: date | None = None,
        log=print,
        assume_missing: bool = False,
        writeback: WriteBack | None = None,
        book: ShadowBook | None = None,
        default_service: dict | None = None,
        auth_deny: dict[tuple[str, str], str] | None = None,
    ):  # noqa: ANN001
        self.out, self.log, self.assume_missing, self.writeback, self.book = out, log, assume_missing, writeback, book
        self.default_service = default_service  # demo: the planned procedure for sources that do not carry one (e.g. {"cpt": "72148"})
        self.auth_payer = prior_auth.MockAuthPayer(auth_deny)
        self.as_of = as_of or date.today()
        self.watcher = AppointmentWatcher(server, out / "seen.json")
        self.reader = InsuranceReader(server)
        self.visits_file = out / "visits.json"  # appointments being followed for the 3-day and 1-day re-checks
        self.visits: dict[str, dict] = (
            json.loads(self.visits_file.read_text(encoding="utf-8")) if self.visits_file.exists() else {}
        )
        self.payers: dict[str, PayerSim] = {PAYER_ID: PayerSim(PAYER_ID, PAYER_NAME)}
        self.world = LiveWorld(self.payers[PAYER_ID], self.as_of, self.payers)
        self._srv = _Srv(create_clearinghouse(self.world, token=TOKEN, today=self.as_of), _free_port())
        self.client: ClearinghouseClient | None = None
        self._n = 0

    def __enter__(self) -> Trigger:
        self._srv.__enter__()
        self.client = ClearinghouseClient(self._srv.url, TOKEN)
        self.out.mkdir(parents=True, exist_ok=True)
        if not self.watcher.state.exists():
            self.log(f"first run: {self.watcher.baseline()} existing appointments marked as already seen")
        return self

    def __exit__(self, *exc):  # noqa: ANN002
        if self.client:
            self.client.close()
        self._srv.__exit__(*exc)

    def advance(self, day: date) -> None:
        """Move the clock (the demo can show the 3-day and 1-day re-checks without waiting)."""
        self.as_of = day
        self.world.advance(day)

    # ------------------------------------------------------------------------------------------------- which policies
    def _policies(self, appt: dict, visit: date) -> tuple[list[Policy], list[str]]:
        """The policies to check, primary first, and the assumptions made to get them. Empty list = no insurance known."""
        notes: list[str] = []
        if appt.get("_policies") is not None:  # a drop-folder source carries the insurance in the same file
            return [p for p in appt["_policies"] if p.covers(visit)], notes
        if appt.get("uuid"):
            found = self.reader.policies(appt["uuid"], visit)
            if found:
                return found, notes
        info = seed.decode(appt.get("pc_title")) or {}
        dob = str(appt.get("DOB", ""))
        if info.get("payer"):  # a booking made by the demo seed names its payer in the title
            notes.append(f"no insurance record in the EMR: payer {info['payer']} taken from the booking title")
            return [
                Policy(
                    1,
                    appt["member"],
                    info["payer"],
                    info["payer"],
                    "",
                    "",
                    "self",
                    appt["lname"],
                    appt["fname"],
                    dob,
                    None,
                    None,
                    None,
                )
            ], notes
        if self.assume_missing:
            notes.append(f"no insurance record and no payer written on the booking: assumed {PAYER_ID}")
            return [
                Policy(
                    1,
                    appt["member"],
                    PAYER_ID,
                    PAYER_NAME,
                    "",
                    "",
                    "self",
                    appt["lname"],
                    appt["fname"],
                    dob,
                    None,
                    None,
                    None,
                )
            ], notes
        return [], notes

    # --------------------------------------------------------------------------------------------------- one policy
    def _send(self, appt: dict, pol: Policy, ref: str, primary: Policy | None) -> dict:
        """One 270 to this policy's payer and its 271 back, decoded. The payer sim is told what the plan says (copay, who is primary)."""
        t0 = time.perf_counter()
        notes: list[str] = []
        payer = self.payers.setdefault(pol.payer_code, PayerSim(pol.payer_code, pol.payer_name or pol.payer_code))
        member = pol.member
        if member not in payer.members:
            payer.enrol(member)
            notes.append(f"member {member} was not known to the payer sim: enrolled as active (demo)")
        if pol.copay is not None:
            payer.copays[member] = pol.copay
        if primary is not None:  # this payer knows another plan pays first
            payer.cob[member] = primary.payer_name or primary.payer_code
        dependent = None
        if pol.relationship not in ("self", ""):
            dependent = (appt["lname"], appt["fname"], str(appt.get("DOB", "")).replace("-", ""), RELATION_CODE.get(pol.relationship, "G8"))
            notes.append(
                f"patient is the {pol.relationship} of the policyholder: the 270 asks about the patient in a dependent level (HL 23) under the policyholder"
            )
        visit = date.fromisoformat(appt["pc_eventDate"])
        self._n += 1
        last, first = pol.holder_last or appt["lname"], pol.holder_first or appt["fname"]
        dob = (pol.holder_dob or str(appt.get("DOB", ""))).replace("-", "")
        req = write_270(pol.payer_code, payer.name, member, last, first, dob, visit, ref, 91000 + self._n, self.as_of, dependent=dependent)
        t271 = self.client.check_eligibility(req)
        ms = round((time.perf_counter() - t0) * 1000)
        gaps: list[a1_rules.Gap]
        decoded: dict
        try:
            r = parse_271(read_transactions(t271)[0], "live")[0]
            decoded = {
                "found": True, "active": r.active, "payer": f"{r.payer_name} ({r.payer_code})", "member": member,
                "trace": r.response_ref, "visit_date": str(r.service_date), "plan_begin": str(r.plan_begin),
                "plan_end": str(r.plan_end) if r.plan_end else "open ended", "other_payer": r.other_payer,
                "copay": f"{r.copay:.2f}" if r.copay is not None else "not given by this payer",
                "coinsurance": f"{r.coinsurance:.0%}" if r.coinsurance is not None else "not given",
                "deductible_remaining": f"{r.deductible_remaining:.2f}" if r.deductible_remaining is not None else "not given",
                "dependent": f"{dependent[1]} {dependent[0]} ({pol.relationship})" if dependent else None,
            }  # fmt: skip
            answer = a1_rules.Response(
                self.as_of,
                r.active,
                r.plan_begin,
                r.plan_end,
                r.other_payer,
                r.copay,
                r.coinsurance,
                r.deductible_remaining,
            )
            gaps = a1_rules.check(visit, answer, self.as_of)
        except X12Error:
            decoded = {
                "found": False,
                "active": None,
                "why": "the payer could not find this member (271 with a rejection)",
            }
            gaps = [a1_rules.Gap(a1_rules.NO_CHECK, "the payer could not find this member")]
        if primary is not None:  # a secondary plan's 271 naming the primary is exactly what it should say
            names = {n.lower() for n in (primary.payer_name, primary.payer_code) if n}
            gaps = [g for g in gaps if not (g.kind == a1_rules.COB and any(n in g.detail.lower() for n in names))]
        return {
            "order": pol.label, "payer": pol.payer_code, "payer_name": pol.payer_name or pol.payer_code, "member": member, "plan": pol.plan,
            "ms_270_to_271": ms, "notes": notes, "decoded": decoded,
            "gaps": [{"payer": pol.payer_code, "order": pol.label, "kind": g.kind, "detail": g.detail} for g in gaps],
            "x12_270": req, "x12_271": t271, "lines_270": explain(req), "lines_271": explain(t271),
        }  # fmt: skip

    # ------------------------------------------------------------------------------------------------- prior authorization (A2)
    def _prior_auth(self, appt: dict, policies: list[Policy], visit: date, ref: str) -> dict:
        """Does the planned service need an authorization with the primary payer? If so and none is on file, ask the (mock) payer."""
        pol = policies[0]
        svc = {**(self.default_service or {}), **{k: v for k, v in (appt.get("_service") or {}).items() if v not in (None, "")}}
        cpt = str(svc.get("cpt") or "").strip()
        need = prior_auth.need(pol.payer_code, cpt, visit, self.as_of)
        res: dict = {"cpt": cpt, "payer": pol.payer_code, "need": need, "outcome": need["status"], "note": need["why"],
                     "scope": "primary payer only; synthetic rules, not a real payer's policy"}  # fmt: skip
        if need["status"] == prior_auth.REQUIRED and svc.get("auth_number"):
            res.update(outcome=prior_auth.ON_FILE, auth_number=str(svc["auth_number"]))
        elif need["status"] == prior_auth.REQUIRED:
            payer = self.payers[pol.payer_code]
            self._n += 1
            units = int(svc.get("units") or 1)
            req = prior_auth.write_278(pol.payer_code, payer.name, pol.member, pol.holder_last or appt["lname"], pol.holder_first or appt["fname"],
                                       (pol.holder_dob or str(appt.get("DOB", ""))).replace("-", ""), cpt, units, str(svc.get("dx") or ""), visit,
                                       f"{ref}-A", 92000 + self._n, self.as_of)  # fmt: skip
            ans = self.auth_payer.answer(req, payer.name, pol.member in payer.members, svc.get("docs", True) is not False, need.get("valid_days") or 90, self.as_of)
            dec = prior_auth.decode_278(ans)
            res.update(outcome=dec["outcome"], decoded=dec, x12_278=req, x12_278_response=ans, lines_278=explain(req), lines_278_response=explain(ans))
            if dec["outcome"] == prior_auth.CERTIFIED:
                payer.grant_auth(pol.member, cpt)  # the payer sim now knows: a later claim for this service is not denied with CARC 197
                res["note"] = f"certified: {dec['auth_number']} valid {dec['valid_from']} to {dec['valid_to']}, {dec['units']} unit(s)"
            else:
                res["note"] = dec["message"] or dec["outcome"]
        res["suggestion"] = prior_auth.SUGGESTION.get(res["outcome"], "a person must read the payer's answer")
        return res

    # ------------------------------------------------------------------------------------------------- one booking
    def check(self, appt: dict, kind: str = "booking") -> dict:
        """Eligibility for one booking: read the insurance, send a 270 per policy, decode every 271, apply the A1 rules."""
        visit = date.fromisoformat(appt["pc_eventDate"])
        policies, assumed = self._policies(appt, visit)
        ref = f"TRG{int(appt['pc_eid']):06d}"
        suffix = "" if kind == "booking" else "_" + kind.replace("-", "")
        checks: list[dict] = []
        for i, pol in enumerate(policies):
            c = self._send(appt, pol, ref if i == 0 else f"{ref}-{i + 1}", policies[0] if i else None)
            assumed = assumed + c["notes"]
            checks.append(c)
        auth = self._prior_auth(appt, policies, visit, ref) if policies else None
        gaps = [g for c in checks for g in c["gaps"]]
        order_review = cob_order.check_order(policies)  # the order the front desk entered, judged by well-known COB rules
        gaps += [
            {"payer": f["payer"], "order": f["order"], "kind": a1_rules.COB, "detail": f"coverage order to confirm ({f['rule']}): {f['detail']}"}
            for f in order_review
        ]
        if not policies:
            gaps = [
                {
                    "payer": "",
                    "order": "",
                    "kind": a1_rules.NO_CHECK,
                    "detail": "no insurance on file for this patient: nothing to check",
                }
            ]
        gaps.sort(key=lambda g: a1_rules.PRIORITY.index(g["kind"]))
        top = gaps[0] if gaps else None
        none = {"payer": "", "decoded": {"found": False, "active": None, "why": "no insurance on file for this patient"},
                "x12_270": "", "x12_271": "", "lines_270": [], "lines_271": [], "ms_270_to_271": 0}  # fmt: skip
        first = checks[0] if checks else none
        copay = first["decoded"].get("copay", "")
        result = {
            "kind": kind, "event_id": appt["event_id"], "detected_at": datetime.now().isoformat(timespec="seconds"), "as_of": self.as_of.isoformat(),
            "appointment": {k: appt.get(k) for k in ("pc_eid", "pid", "fname", "lname", "DOB", "pc_eventDate", "pc_startTime", "pc_apptstatus", "pc_title")},
            "member": appt["member"], "payer": first["payer"], "assumed": assumed, "ms_270_to_271": sum(c["ms_270_to_271"] for c in checks),
            "route": "watcher -> read insurance -> 270 per payer -> mock clearinghouse -> payer sim -> 271 -> Gatekeeper rules",
            "coverage_order": [{"order": c["order"], "payer": c["payer"], "member": c["member"], "plan": c["plan"]} for c in checks],
            "order_review": order_review, "prior_auth": auth, "checks": checks, "decoded": first["decoded"], "x12_270": first["x12_270"], "x12_271": first["x12_271"],
            "lines_270": first["lines_270"], "lines_271": first["lines_271"],
            "clearance": {
                "cleared": not gaps, "gaps": gaps, "action": ACTION_BY_GAP[top["kind"]] if top else None, "owner": "front_desk" if top else None,
                "top_gap": top["kind"] if top else None, "copay_due": copay if copay[:1].isdigit() else None,
                "mode": "shadow: a task is proposed for the front desk; nothing is written to the EMR",
            },
        }  # fmt: skip
        if self.writeback is not None:  # proposes only; a send needs the adapter on and a named approver
            result["writeback"] = self.writeback.propose(result)
        if self.book is not None:  # the full A1 agent on the same data: writes a decision record (shadow, L0)
            result["agent"] = self.book.record(result)
        d = self.out / f"{ref}{suffix}"
        d.mkdir(parents=True, exist_ok=True)
        (self.out / "inbox").mkdir(exist_ok=True)
        for i, c in enumerate(checks):
            tag = "" if i == 0 else f"_{i + 1}"
            (d / f"270{tag}.x12").write_text(c["x12_270"], encoding="utf-8")
            (d / f"271{tag}.x12").write_text(c["x12_271"], encoding="utf-8")
            (self.out / "inbox" / f"271_{ref}{suffix}{tag}.x12").write_text(c["x12_271"], encoding="utf-8")
        if auth and auth.get("x12_278"):
            (d / "278.x12").write_text(auth["x12_278"], encoding="utf-8")
            (d / "278_response.x12").write_text(auth["x12_278_response"], encoding="utf-8")
        (d / "result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
        line = {
            k: result[k]
            for k in (
                "kind",
                "event_id",
                "detected_at",
                "member",
                "payer",
                "ms_270_to_271",
                "decoded",
                "coverage_order",
                "clearance",
            )
        }
        with (self.out / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
        return result

    # ------------------------------------------------------------------------------------------------------ the loop
    def _save_visits(self) -> None:
        self.visits_file.write_text(json.dumps(self.visits, indent=1), encoding="utf-8")

    def _follow(self, appt: dict) -> None:
        days = (date.fromisoformat(appt["pc_eventDate"]) - self.as_of).days
        covered = [
            str(x) for x in a1_config.CHECKPOINT_DAYS if days <= x
        ]  # the booking check already serves those checkpoints
        self.visits[str(appt["pc_eid"])] = {
            "event_id": appt["event_id"],
            "visit": appt["pc_eventDate"],
            "done": covered,
        }
        self._save_visits()

    def _unfollow(self, eid: str) -> None:
        if self.visits.pop(eid, None) is not None:
            self._save_visits()

    def tick(self) -> list[dict]:
        out = []
        for appt in self.watcher.poll():
            if str(appt.get("pc_apptstatus")) in CANCELLED:
                self.watcher.mark(appt["event_id"])
                self._unfollow(str(appt["pc_eid"]))
                self.log(f"skipped {appt['event_id']}: appointment is cancelled")
                continue
            res = self.check(appt)
            self.watcher.mark(
                appt["event_id"]
            )  # only after the answer is saved: a crash replays it, and the files are overwritten
            self._follow(appt)
            out.append(res)
            self.log(show(res))
        return out + self.recheck()

    def recheck(self) -> list[dict]:
        """3 days and 1 day before a visit, ask again: coverage can lapse between booking and the visit."""
        due: dict[str, int] = {}
        for eid, v in self.visits.items():
            days = (date.fromisoformat(v["visit"]) - self.as_of).days
            hit = [d for d in a1_config.CHECKPOINT_DAYS if days <= d]
            if days >= 0 and hit and str(min(hit)) not in v["done"]:
                due[eid] = min(hit)
        if not due:
            return []
        now, out = self.watcher.current(set(due)), []
        for eid, d in due.items():
            v, appt = self.visits[eid], now.get(eid)
            v["done"] += [str(x) for x in a1_config.CHECKPOINT_DAYS if x >= d]
            if appt is None or str(appt.get("pc_apptstatus")) in CANCELLED or appt["event_id"] != v["event_id"]:
                self._unfollow(eid)  # cancelled or moved: a moved one was picked up as a new booking
                self.log(f"re-check dropped for {v['event_id']}: the appointment is cancelled or has moved")
                continue
            res = self.check(appt, kind=f"recheck-{d}d")
            res["clearance"]["checkpoint_days"] = d
            out.append(res)
            self.log(show(res))
        self._save_visits()
        return out

    def watch(self, interval: float = 3.0, seconds: float | None = None) -> None:
        end = time.monotonic() + seconds if seconds else None
        self.log(f"watching OpenEMR every {interval:g}s (read-only). Book an appointment now. Ctrl+C to stop.")
        while end is None or time.monotonic() < end:
            self.tick()
            time.sleep(interval)


def _plain(d: dict) -> list[str]:
    if not d["found"]:
        return [f"  NOT FOUND: {d['why']}"]
    who = [f"  Dependent       {d['dependent']}: asked in its own level under the policyholder"] if d.get("dependent") else []
    return who + [f"  Coverage        {'ACTIVE' if d['active'] else 'NOT ACTIVE'}", f"  Payer           {d['payer']}", f"  Member          {d['member']}",
            f"  Trace number    {d['trace']}", f"  Visit date      {d['visit_date']}", f"  Plan            {d['plan_begin']} to {d['plan_end']}",
            f"  Other payer     {d['other_payer'] or 'none (this payer says it is primary)'}", f"  Copay           {d['copay']}",
            f"  Coinsurance     {d['coinsurance']}", f"  Deductible left {d['deductible_remaining']}"]  # fmt: skip


def show(res: dict) -> str:
    a = res["appointment"]
    head = "NEW APPOINTMENT DETECTED" if res["kind"] == "booking" else f"RE-CHECK ({res['kind']})"
    lines = [
        "", "=" * 100, f"{head}  {res['event_id']}   at {res['detected_at']}", "=" * 100,
        f"Patient     {a['fname']} {a['lname']}  born {a['DOB']}   member {res['member']}   (OpenEMR pid {a['pid']})",
        f"Visit       {a['pc_eventDate']} {a['pc_startTime']}   status {a['pc_apptstatus']!r}   title {a['pc_title']!r}   (checked as of {res['as_of']})",
        f"Route       {res['route']}",
        f"Round trip  {res['ms_270_to_271']} ms for {len(res['checks'])} payer(s)",
    ]  # fmt: skip
    lines += [f"ASSUMED     {x}" for x in res["assumed"]]
    if not res["checks"]:
        lines += ["", "--- insurance on file ---", "  none: no 270 was sent"]
    for c in res["checks"]:
        lines += [
            "",
            f"--- {c['order'].upper()} payer {c['payer']} ({c['plan'] or 'plan not named'}), member {c['member']} ---",
            "  270 (the question)",
        ]
        lines += [f"    {x['text']:<76} {x['note']}" for x in c["lines_270"]] + ["  271 (the answer)"]
        lines += (
            [f"    {x['text']:<76} {x['note']}" for x in c["lines_271"]] + ["  in plain words"] + _plain(c["decoded"])
        )
    cl = res["clearance"]
    lines += ["", "--- Gatekeeper (A1) rules applied to the answers ---"]
    if cl["cleared"]:
        lines += [f"  CLEARED. Copay due at the visit: {cl['copay_due'] or 'not reported'}"]
    else:
        lines += [
            f"  {g['kind']}: {g['detail']}" + (f"  [{g['order']} {g['payer']}]" if g["payer"] else "")
            for g in cl["gaps"]
        ]
        lines += [f"  proposed: {cl['action']} for the {cl['owner']}", f"  {cl['mode']}"]
    au = res.get("prior_auth")
    if au:
        lines += ["", "--- Prior authorization (A2 Permit Clerk, mock payer) ---",
                  f"  planned procedure {au['cpt'] or 'none on the booking'} with {au['payer']}: {au['outcome'].upper().replace('_', ' ')}  ({au['note']})"]  # fmt: skip
        if au.get("x12_278"):
            lines += ["  278 (the request)"] + [f"    {x['text']:<76} {x['note']}" for x in au["lines_278"]]
            lines += ["  278 (the answer)"] + [f"    {x['text']:<76} {x['note']}" for x in au["lines_278_response"]]
        lines += [f"  suggestion: {au['suggestion']}", f"  ({au['scope']})"]
    ag = res.get("agent")
    if ag:
        lines += [
            "", "--- Gatekeeper (A1) agent run: the decision record ---",
            *([f"  record {ag['record_id']}  outcome {ag['outcome']}  action {ag['action']}  {ag['level']} / {ag['mode']}  confidence {ag['confidence']}",
               f"  rules: {', '.join(ag['rules'])}", f"  patient estimate: {ag['patient_estimate'] or 'not available (no fee schedule in the demo)'}"]
              if ag["ran"] else [f"  not run: {ag['why']}"]),
        ]  # fmt: skip
    if res.get("writeback"):
        lines += [
            f"  write-back: note {res['writeback']['state']} (not sent, needs approval): {res['writeback']['title']}"
        ]
    lines += [
        f"\nSaved in out/trigger/TRG{int(a['pc_eid']):06d}{'' if res['kind'] == 'booking' else '_' + res['kind'].replace('-', '')}/ (270.x12, 271.x12, result.json)"
    ]
    return "\n".join(lines)


def _server(work: Path):  # noqa: ANN202
    from krisnai.integrations.openemr.auth import OpenEmrAuth

    return seed._Server(OpenEmrAuth(work))


def dry_run(
    work: Path, out: Path, log=print, plans: tuple[str, ...] = ("primary",), propose: bool = False,
    agent: bool = False,
    service: dict | None = None,
) -> list[dict]:
    """Baseline, then enter a new patient with insurance and an appointment in OpenEMR as a person would, and watch the trigger fire.

    `plans` is the insurance entered on the patient: "primary", "secondary" or both; empty means none (the exception case).
    """
    from krisnai.live import demo_insurance

    server = _server(work)
    book = ShadowBook(out) if agent else None
    with Trigger(server, out, log=log, writeback=WriteBack(server, out) if propose else None, book=book, default_service=service) as t:
        n = t.watcher.baseline()
        log(f"step 1. watcher started, {n} existing appointments ignored")
        member = f"SYNLV{len(server.rest_rows('/patient')) + 1:05d}"
        visit = date.today() + timedelta(days=3)
        body = {"fname": "Synthetic", "lname": member, "pubpid": member, "street": "100 Synthetic Way", "city": "Testville", "state": "TX",
                "postal_code": "75001", "country_code": "US", **seed._synthetic_person(member)}  # fmt: skip
        made = server.rest_json("POST", "/patient", json=body)["data"]
        patient = next(p for p in server.rest_rows("/patient") if p["pid"] == made["pid"])
        log(f"step 2. new patient {member} entered in OpenEMR (pid {made['pid']})")
        if plans:
            demo_insurance.add_policy(server, patient, "primary", "SYNAETNA", "SYNAETNA Demo Payer", member, copay="25")
            if "secondary" in plans:
                demo_insurance.add_policy(
                    server,
                    patient,
                    "secondary",
                    "SYNBLUE",
                    "SYNBLUE Demo Payer",
                    f"{member}B",
                    copay="10",
                    plan="SUPPLEMENT",
                )
            log(f"        insurance entered by the front desk: {', '.join(plans)}")
        else:
            log("        no insurance entered")
        prac = server.rest_rows("/practitioner")
        t0 = time.perf_counter()
        server.rest_json("POST", f"/patient/{made['pid']}/appointment", json={
            "pc_catid": seed.OFFICE_VISIT, "pc_title": "Office Visit", "pc_hometext": "booked by hand", "pc_duration": "1800",
            "pc_apptstatus": "-", "pc_eventDate": visit.isoformat(), "pc_startTime": "10:30", "pc_facility": seed.FACILITY_ID,
            "pc_billing_location": seed.FACILITY_ID, "pc_aid": prac[0]["id"] if prac else 1,
        })  # fmt: skip
        log(f"step 3. appointment for {visit} saved in OpenEMR; waiting for the watcher")
        got: list[dict] = []
        for _ in range(20):
            got = t.tick()
            if got:
                log(f"\nstep 4. trigger fired {round(time.perf_counter() - t0, 1)} s after the appointment was saved")
                break
            time.sleep(1)
        if not got:
            raise SystemExit("the trigger did not fire within 20 s")
        log(f"step 5. polled again: {len(t.tick())} new (the same booking does not fire twice)")
        return got


def main() -> None:
    ap = argparse.ArgumentParser(description="Trigger an eligibility check on every new OpenEMR appointment")
    ap.add_argument("--work", type=Path, default=Path("out/openemr"))
    ap.add_argument("--out", type=Path, default=Path("out/trigger"))
    ap.add_argument(
        "--demo",
        action="store_true",
        help="enter a test patient with insurance and an appointment in OpenEMR and show the trigger fire",
    )
    ap.add_argument(
        "--plans",
        default="primary",
        help="with --demo: insurance entered on the patient: primary, primary,secondary, or none",
    )
    ap.add_argument(
        "--assume-missing",
        action="store_true",
        help="with no insurance on file, assume the demo payer instead of raising an exception",
    )
    ap.add_argument(
        "--writeback", action="store_true", help="also propose a note for the front desk per check (nothing is sent)"
    )
    ap.add_argument("--folder", type=Path, help="read appointments from a drop folder of HL7 (*.hl7) and CSV files instead of OpenEMR")
    ap.add_argument("--db-url", help="read appointments from a database view (read-only SQLAlchemy URL), with --db-view")
    ap.add_argument("--db-view", help="name of the view to read with --db-url")
    ap.add_argument("--upload", type=Path, help="check a CSV or HL7 file and, if it is clean, copy it into --folder (manual upload)")
    ap.add_argument("--cpt", help="demo: the planned procedure for bookings whose source does not carry one (starts the prior authorization check)")
    ap.add_argument("--no-docs", action="store_true", help="demo: the clinical documents are missing, so the mock payer pends the authorization")
    ap.add_argument("--agent", action="store_true", help="also run the full A1 agent per check and save its decision record")
    ap.add_argument("--pending", action="store_true", help="list the proposed notes and exit")
    ap.add_argument(
        "--approve", metavar="KEY", help="send one proposed note to the EMR (needs --by and --enable-writeback)"
    )
    ap.add_argument("--by", default="", help="name of the person approving the note")
    ap.add_argument(
        "--enable-writeback",
        action="store_true",
        help="switch the write-back adapter on for this command (off by default)",
    )
    ap.add_argument("--interval", type=float, default=3.0)
    ap.add_argument("--seconds", type=float, default=None, help="stop watching after this many seconds")
    a = ap.parse_args()
    service = {"cpt": a.cpt, "docs": not a.no_docs} if a.cpt else None
    if a.demo:
        dry_run(a.work, a.out, plans=() if a.plans == "none" else tuple(a.plans.split(",")), propose=a.writeback, agent=a.agent, service=service)
        return
    if a.upload:
        from krisnai.live.intake import upload

        if not a.folder:
            raise SystemExit("--upload needs --folder (where the checked file is placed)")
        dest, problems = upload(a.upload, a.folder)
        if problems:
            raise SystemExit("not uploaded:" + chr(10) + chr(10).join("  " + x for x in problems))
        print(f"uploaded: {dest}")
        return
    if a.db_url:
        from krisnai.live.intake import DatabaseView

        if not a.db_view:
            raise SystemExit("--db-url needs --db-view")
        if a.writeback or a.approve or a.pending:
            raise SystemExit("write-back needs the EMR's API: it is not available with --db-url")
        server = DatabaseView(a.db_url, a.db_view)
    elif a.folder:
        if a.writeback or a.approve or a.pending:
            raise SystemExit("write-back needs the EMR's API: it is not available with --folder")
        from krisnai.live.intake import DropFolder

        server = DropFolder(a.folder)
    else:
        server = _server(a.work)
    wb = WriteBack(server, a.out, enabled=a.enable_writeback)
    if a.pending:
        for k, v in wb.pending().items():
            note = v["proposal"]
            print(k, note["title"], *["  " + x for x in note["body"].splitlines()], sep=chr(10))
        return
    if a.approve:
        try:
            print(f"sent: {wb.approve(a.approve, a.by)['sent_at']} approved by {a.by}")
        except WriteBackError as e:
            raise SystemExit(f"not sent: {e}") from e
        return
    with Trigger(server, a.out, assume_missing=a.assume_missing, writeback=wb if a.writeback else None,
                 book=ShadowBook(a.out) if a.agent else None, default_service=service) as t:
        try:
            t.watch(a.interval, a.seconds)
        except KeyboardInterrupt:
            print("stopped")


if __name__ == "__main__":
    main()
