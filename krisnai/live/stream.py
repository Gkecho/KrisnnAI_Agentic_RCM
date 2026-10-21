# ruff: noqa: E501
"""S4 of the live encounter stream: the orchestrator and the simulated clock.

It pushes synthetic encounters through the whole chain one at a time, day by day on a simulated clock, with nobody typing
data in:

  booking day     patient and appointment in the EMR, eligibility 270/271 through the clearinghouse (Gatekeeper's check)
  visit day       encounter, signed note and transcript in the EMR; the transcript coder decides auto-accept or coder queue
  billing         charge and 837P from the EMR, 999 and 277CA from the clearinghouse, then the payer decides (hidden truth log)
  remit day       the payer's 835; status and portal bots read the payer's live state
  every day       the engine's daily run (all agents, shadow mode) over whatever files arrived

Everything is demo-only and synthetic (ADR-0002). Every state change is saved before the next step, every EMR write looks
for the record first, and every payer decision comes from a (seed, claim id) random stream, so a run killed at any point
resumes without repeating or losing an encounter and finishes with the same decisions as an uninterrupted run.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from pathlib import Path

from krisnai.agents.a14_tower import open_cards
from krisnai.ingest.eligibility import parse_271
from krisnai.ingest.x12 import X12Error, read_transactions
from krisnai.integrations.clearinghouse.bots import status_bot
from krisnai.integrations.clearinghouse.client import ClearinghouseClient
from krisnai.integrations.clearinghouse.mock_server import create_app as create_clearinghouse
from krisnai.integrations.clearinghouse.x12_out import write_270
from krisnai.integrations.openemr import seed
from krisnai.integrations.openemr.billing import Charge
from krisnai.integrations.portal.bots import claim_status_bot
from krisnai.integrations.portal.driver import HttpDriver
from krisnai.integrations.portal.mock_portal import create_app as create_portal
from krisnai.knowledge.demo import demo_book
from krisnai.live.coder import Coder, Policy
from krisnai.live.emr import PROVIDER_NPI, EmrPort
from krisnai.live.payer import PayerConfig, PayerSim
from krisnai.live.s1 import FEES, PAYER_ID, PAYER_NAME, SALT, TOKEN, _engine, _free_port, _Srv
from krisnai.live.transcripts import TYPES, Visit, generate
from krisnai.live.world import LiveWorld
from krisnai.ops import run_period
from krisnai.synthea import x12out

PORTAL_USER, PORTAL_PASSWORD = "live-user", "live-pass"  # a local mock portal only
CPT_TEXT = "Office visit"
SIMULATED_CODER = "person:simulated-coder (demo)"


class SimulatedCrash(Exception):
    """Raised by the crash hook in tests: the process 'dies' after a side effect and before the state is saved."""


@dataclass
class StreamConfig:
    count: int = 50
    seed: int = 7
    start: date = date(2026, 10, 21)
    per_day: int = 5  # bookings a day
    lead_days: int = 3  # booking to visit
    confirm_days: int = 2  # the simulated coder's turnaround on a clean visit routed for a quality check
    settle_days: int = 10  # simulated days after the last remit is due
    policy_on: bool = True
    inactive_rate: float = 0.06  # share of patients whose coverage has lapsed
    pend_rate: float = 0.10
    deny_rate: float = 0.12
    deviation_rate: float = 0.15
    engine: bool = True
    bots: bool = True
    serve: bool = True  # real local servers (False: in-process, for tests)
    tag: str = ""  # makes every id unique to one run (a typed-in visit must never reuse an earlier run's patient)
    early_stop: bool = False  # stop once every claim is settled and the agents have had `react_days` to react (single visits)
    react_days: int = 8
    sample_rate: float = 0.10  # the share of auto-accepts a coder still checks (0 for typed-in visits: the same transcript must always get the same answer)
    # switches for the three parallel pieces of work; each is off by default so existing behaviour and tests are unchanged
    payers: str = "single"  # S6: "single" (one payer, as before) or "network" (several payers, one picked per visit)
    reader: str = "rules"  # S7: how transcripts are read: "rules" or "rules+ai" (an AI proposal, checked by the rules)
    replies: bool = False  # S8: the bots answer the payer's replies (corrected claims, appeals, disputes, records)
    reject_rate: float = 0.0  # S8: the share of claims sent with a data-entry error the clearinghouse will reject
    lapsed_ids: tuple[int, ...] = ()  # visits (1-based) whose coverage has lapsed, when chosen one by one

    def key(self) -> dict:
        d = asdict(self)
        for k in ("engine", "bots", "serve"):
            d.pop(k)
        d["start"] = self.start.isoformat()
        d["lapsed_ids"] = list(self.lapsed_ids)  # JSON has no tuples: compare like with like when a saved run resumes
        return d


@dataclass
class Result:
    summary: dict = field(default_factory=dict)


class Stream:
    def __init__(self, cfg: StreamConfig, out: Path, emr: EmrPort, log=print, crash_after: int | None = None, visits: list[Visit] | None = None):  # noqa: ANN001
        self.cfg, self.out, self.emr, self.log, self.crash_after = cfg, out, emr, log, crash_after
        self.mutations = 0
        for d in ("inbox", "archive", "claims", "evidence"):
            (out / d).mkdir(parents=True, exist_ok=True)
        self.visits: list[Visit] = visits if visits is not None else generate(cfg.seed, cfg.count, cfg.start)
        self.state = self._load()
        self.seen_events = {json.loads(ln)["key"] for ln in (out / "events.jsonl").read_text("utf-8").splitlines() if ln} if (out / "events.jsonl").exists() else set()
        self.coder = Coder(Policy(enabled=cfg.policy_on, seed=cfg.seed, sample_rate=cfg.sample_rate), reader=cfg.reader)
        self.coder.per_day = dict(self.state.get("coder_per_day", {}))
        self.payer = PayerSim(PAYER_ID, PAYER_NAME, book=demo_book(), config=PayerConfig(
            seed=cfg.seed, pend_rate=cfg.pend_rate, deny_rate=cfg.deny_rate, deviation_rate=cfg.deviation_rate))
        self.payers: dict[str, PayerSim] = {PAYER_ID: self.payer}  # one payer today; the network of payers fills this in
        self.world = LiveWorld(self.payer, cfg.start)
        for member, active in self.state["members"].items():
            self.payers[self.state["enc"].get(member, {}).get("payer_id", PAYER_ID)].enrol(member, active)
        self._rebuild_payer()

    # ------------------------------------------------------------------------------------------ state
    def _load(self) -> dict:
        p = self.out / "state.json"
        if p.exists():
            st = json.loads(p.read_text("utf-8"))
            if st["config"] != self.cfg.key():
                raise SystemExit("the saved run used different settings; use a fresh output folder or --fresh")
            return st
        return {"config": self.cfg.key(), "day": None, "members": {}, "enc": {}, "issued": [], "ctrl835": 7000, "coder_per_day": {}}

    def _save(self) -> None:
        self.state["coder_per_day"] = dict(self.coder.per_day)
        tmp = self.out / "state.json.tmp"
        text = json.dumps(self.state, indent=1, sort_keys=True)
        tmp.write_text(text, encoding="utf-8")
        for attempt in range(25):  # a sync client or virus scanner can hold the target for a moment (seen on OneDrive)
            try:
                os.replace(tmp, self.out / "state.json")
                return
            except PermissionError:
                time.sleep(0.2 * (attempt + 1) ** 0.5)
        (self.out / "state.json").write_text(text, encoding="utf-8")  # last resort: still a whole file, written in one call

    def _commit(self) -> None:
        """Called after a step's side effects and before the state is saved: the worst moment to be killed."""
        self.mutations += 1
        if self.crash_after is not None and self.mutations == self.crash_after:
            raise SimulatedCrash(f"simulated crash at mutation {self.mutations}")
        self._save()

    def _event(self, key: str, day: date, step: str, tool: str, bot: str, subject: str, outcome: str, detail: str) -> None:
        if key in self.seen_events:
            return
        self.seen_events.add(key)
        row = {"key": key, "day": day.isoformat(), "step": step, "tool": tool, "bot": bot, "subject": subject, "outcome": outcome, "detail": detail}
        with (self.out / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        self.log(f"  {day} [{step}] {tool}: {outcome} - {detail}")

    def _write(self, name: str, text: str, folder: str = "inbox") -> None:
        (self.out / folder / name).write_text(text, encoding="utf-8")

    def _rebuild_payer(self) -> None:
        """After a restart: replay the claims already submitted so the world and the payer hold what they held before."""
        for eid in sorted(self.state["enc"]):
            e = self.state["enc"][eid]
            f = self.out / "claims" / f"{e.get('claim', '')}.837"
            if e.get("billed_on") and f.exists() and e["stage"] in ("adjudicated", "rejected"):
                billed = date.fromisoformat(e["billed_on"])
                self.world.accept_claims(f.read_text("utf-8"), billed)
                if e["stage"] == "adjudicated" and e.get("claim") not in self.world.rejected:
                    c = next(c for c in self.world.accepted if c.claim_id == e["claim"])
                    self.payer_for(e).adjudicate(c, billed)
        for d in self._all_cases().values():
            d.issued = d.claim.claim_id in set(self.state["issued"])

    # ------------------------------------------------------------------------------------------ payers
    def assign_payer(self, visit: Visit, eid: str) -> str:
        """The id of the payer this visit's patient is insured with. One payer for now; the payer network replaces this."""
        return PAYER_ID

    def payer_for(self, e: dict) -> PayerSim:
        return self.payers[e.get("payer_id", PAYER_ID)]

    def _all_cases(self) -> dict:
        return {cid: d for p in self.payers.values() for cid, d in p.cases.items()}

    def _all_truth_csv(self) -> str:
        """The truth log of every payer in one file, sorted by claim id."""
        if len(self.payers) == 1:
            return self.payer.truth_csv()
        import io

        rows, header = [], None
        for p in self.payers.values():
            r = list(csv.reader(io.StringIO(p.truth_csv())))
            header = header or r[0]
            rows += r[1:]
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(header)
        w.writerows(sorted(rows))
        return buf.getvalue()

    # ------------------------------------------------------------------------------------------ the schedule
    def schedule(self) -> list[tuple[int, Visit, date, date]]:
        return [(i, v, v.day, v.day + timedelta(days=self.cfg.lead_days)) for i, v in enumerate(self.visits, start=1)]

    def end_day(self) -> date:
        last_visit = max(v for _, _, _, v in self.schedule())
        return last_visit + timedelta(days=self.cfg.confirm_days + 14 + 21 + self.cfg.settle_days)

    # ------------------------------------------------------------------------------------------ one encounter
    def _inactive(self, member: str) -> bool:
        import hashlib

        if self.cfg.lapsed_ids:  # chosen one by one (a typed-in batch): the visit's number is the last five digits of its id
            return int(member[-5:]) in self.cfg.lapsed_ids

        h = int(hashlib.sha256(f"{self.cfg.seed}:inactive:{member}".encode()).hexdigest(), 16)
        return (h % 10_000) < int(self.cfg.inactive_rate * 10_000)

    def _advance_encounter(self, i: int, v: Visit, booking: date, visit_day: date, day: date, client: ClearinghouseClient, feeds: dict) -> None:
        eid = f"SYNST{self.cfg.tag}{i:05d}"
        e = self.state["enc"].setdefault(eid, {"stage": "new", "member": eid, "visit_id": f"SYNVS{self.cfg.tag}{i:05d}L1", "appt": f"SYNAPS{self.cfg.tag}{i:05d}",
                                               "booking": booking.isoformat(), "visit_day": visit_day.isoformat(), "visit_type": v.visit_type})  # fmt: skip
        member = e["member"]
        if e["stage"] == "new" and day >= booking:
            pid, puuid = self.emr.ensure_patient(member)
            active = not self._inactive(member)
            appt_cpt = "99203" if TYPES.get(v.visit_type, ("", "", "established", ""))[2] == "new" else "99213"
            self.emr.ensure_appointment(pid, e["appt"], visit_day, appt_cpt, PAYER_ID, booking)
            e["payer_id"] = self.assign_payer(v, eid)
            self.payer_for(e).enrol(member, active)
            self.state["members"][member] = active
            e.update(pid=pid, puuid=puuid, appt_cpt=appt_cpt, active=active)
            feeds["appointments"].append({"appointment_id": e["appt"], "payer_id": PAYER_ID, "provider_npi": PROVIDER_NPI, "patient_ref": member,
                                          "appt_date": visit_day.isoformat(), "booked_on": booking.isoformat(), "cpt": appt_cpt, "status": "booked"})  # fmt: skip
            self._event(f"{eid}:book", day, "1 appointment", "OpenEMR", "openemr", e["appt"], "ok", f"booked {booking} for {visit_day} (pid {pid})")
            self._advance(e, "booked")
        if e["stage"] == "booked":
            dob = seed._synthetic_person(member)["DOB"].replace("-", "")
            req = write_270(PAYER_ID, PAYER_NAME, member, member, "Synthetic", dob, visit_day, e["appt"], 90000 + i, day)
            t271 = client.check_eligibility(req)
            self._write(f"271_{e['appt']}.x12", t271)
            try:
                r = parse_271(read_transactions(t271)[0], "live")[0]
                outcome = "active" if r.active else "inactive"
            except X12Error:
                outcome = "not_found"
            self._event(f"{eid}:elig", day, "2 eligibility", "Eligibility bot", "eligibility", e["appt"], outcome,
                        {"active": "coverage confirmed", "inactive": "coverage is NOT active: flagged before the visit", "not_found": "payer could not find the member"}[outcome])
            self._advance(e, "eligible")
        if e["stage"] == "eligible" and day >= visit_day:
            vid = e["visit_id"]
            if "coding" not in e:  # decided once; a restart reuses it (the daily cap must not count a visit twice)
                e["coding"] = self.coder.code(vid, v.text, v.signed, visit_day).to_dict()
            rec = e["coding"]
            signed = visit_day.isoformat() if v.signed else ""
            note = seed.encode(visit=vid, note_date=visit_day.isoformat(), signed=signed, minutes="", elements="|".join(rec["elements"]))
            eno = self.emr.ensure_visit(e["pid"], e["puuid"], vid, visit_day, PAYER_ID, rec["cpt"] or "pending", note, v.text)
            e.update(eno=eno, claim=f"{e['pid']}-{eno}")
            feeds["notes"].append({"visit_id": vid, "note_date": visit_day.isoformat(), "signed_date": signed, "minutes": "", "elements": ",".join(rec["elements"])})
            self._event(f"{eid}:visit", day, "3 visit", "OpenEMR", "openemr", vid, "ok", f"encounter {eno}, a {'signed' if v.signed else 'UNSIGNED'} note and the transcript")
            if rec["route"] == "auto":
                self._event(f"{eid}:coder", day, "3b coder", "Transcript coder", "coder", vid, "auto-accepted", f"{rec['cpt']}, {rec['dx'][0][0]}; {rec['approval']}")
                self._advance(e, "ready_to_bill")
            elif rec["reason"] in ("qa_sample", "policy_off"):
                e["confirm_on"] = (visit_day + timedelta(days=self.cfg.confirm_days)).isoformat()
                self._event(f"{eid}:coder", day, "3b coder", "Transcript coder", "coder", vid, "routed", f"to a coder: {rec['reason']}")
                self._advance(e, "awaiting_coder")
            else:
                self._event(f"{eid}:coder", day, "3b coder", "Transcript coder", "coder", vid, "routed", f"to a coder: {rec['reason']} ({rec['note']})")
                self._advance(e, "pending_coder")
        if e["stage"] == "awaiting_coder" and day >= date.fromisoformat(e["confirm_on"]):
            e["approval"] = SIMULATED_CODER
            self._event(f"{eid}:confirm", day, "3c coder", "Simulated coder", "coder", e["visit_id"], "confirmed",
                        f"{e['coding']['cpt']} confirmed in a quality check (a simulated person, labelled as such)")
            self._advance(e, "ready_to_bill")
        if e["stage"] == "ready_to_bill":
            rec = e["coding"]
            approval = e.get("approval") or rec["approval"]
            dx = (rec["dx"][0][0], rec["dx"][0][1])
            x837 = self.emr.charge_837(Charge(e["pid"], e["eno"], member, PAYER_ID, PAYER_NAME, [dx], [(rec["cpt"], CPT_TEXT, 1, FEES[rec["cpt"]])]), approval, visit_day)
            self._write(f"837_{e['claim']}.837", x837)
            self._write(f"{e['claim']}.837", x837, "claims")
            e.update(billed_on=day.isoformat(), approval=approval)
            feeds["visits"].append({"visit_id": e["visit_id"], "payer_id": PAYER_ID, "provider_npi": PROVIDER_NPI, "patient_ref": member,
                                    "dos": visit_day.isoformat(), "cpt": rec["cpt"], "units": "1"})  # fmt: skip
            self._event(f"{eid}:claim", day, "4 claim", "OpenEMR billing", "openemr", e["claim"], "ok", f"837P written by the EMR; approval {approval}")
            self._advance(e, "billed")
        if e["stage"] == "billed":
            text = (self.out / "claims" / f"{e['claim']}.837").read_text("utf-8")
            got = client.submit_claim(text)
            self._write(f"999_{e['claim']}.999", got["999"])
            self._write(f"277CA_{e['claim']}.277ca", got["277CA"])
            bad = [r for r in got["results"] if not r["ok"]]
            self._event(f"{eid}:ch", day, "5 clearinghouse", "Mock clearinghouse", "mock", e["claim"], "rejected" if bad else "accepted", bad[0]["reason"] if bad else "999 and 277CA accepted")
            if bad:
                self._advance(e, "rejected")
            else:
                c = next(c for c in self.world.accepted if c.claim_id == e["claim"])
                d = self.payer_for(e).adjudicate(c, day)
                e["remit_date"] = d.remit_date.isoformat()
                self._event(f"{eid}:payer", day, "6 payer", "Payer sim", "mock", e["claim"], "received", f"claim received; remit expected {d.remit_date}")
                self._advance(e, "adjudicated")

    def _advance(self, e: dict, stage: str) -> None:
        self._commit()
        e["stage"] = stage
        self._save()

    # ------------------------------------------------------------------------------------------ one day
    def tick(self, day: date, client: ClearinghouseClient, portal_url: str | None, eng) -> None:  # noqa: ANN001
        self.world.advance(day)
        feeds: dict[str, list] = {"appointments": [], "visits": [], "notes": []}
        if not self.state.get("fee_schedule"):  # the practice's copy of its contract rates, from day one (A10 compares payments to it)
            rows = ["payer_id,cpt,modifier,allowed_amount,effective_date"] + [f"{PAYER_ID},{c},,{a},2020-01-01" for c, a in sorted(self.payer.fees.items())]
            self._write("fee_schedule.csv", "\n".join(rows) + "\n")
            self.state["fee_schedule"] = True
            self._commit()
        for i, v, booking, visit_day in self.schedule():
            if day >= booking:
                self._advance_encounter(i, v, booking, visit_day, day, client, feeds)
        for d in [x for p in self.payers.values() for x in p.remits_due(day)]:
            cid = d.claim.claim_id
            if cid in self.state["issued"]:
                continue
            self.state["ctrl835"] += 1
            self._write(f"835_{cid}.835", x12out.write_835(d.claim.payer, day, [d.claim], self.state["ctrl835"]))
            self.state["issued"].append(cid)
            self._event(f"{cid}:835", day, "7 remit", "Payer sim", "mock", cid, d.outcome, f"835 issued: {d.outcome}" + (f" CARC {d.carc}" if d.carc else ""))
            self._commit()
        for kind, cols in (("appointments", ["appointment_id", "payer_id", "provider_npi", "patient_ref", "appt_date", "booked_on", "cpt", "status"]),
                           ("visits", ["visit_id", "payer_id", "provider_npi", "patient_ref", "dos", "cpt", "units"]),
                           ("notes", ["visit_id", "note_date", "signed_date", "minutes", "elements"])):  # fmt: skip
            if feeds[kind]:
                with (self.out / "inbox" / f"{kind}_{day}.csv").open("w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=cols)
                    w.writeheader()
                    w.writerows(feeds[kind])
        if eng is not None:
            rep = run_period(eng, 1, SALT, day, inbox=self.out / "inbox", archive=self.out / "archive", mode="daily", allow_failed=True)
            if rep.status != "ok" or rep.files_failed:
                self._event(f"{day}:engine", day, "8 agents", "Engine", "engine", str(day), "problem", f"status {rep.status}, {rep.files_failed} files failed")
            if self.cfg.bots:
                self._bots(day, client, portal_url, eng)
        self.state["day"] = day.isoformat()
        self._commit()

    def _bots(self, day: date, client: ClearinghouseClient, portal_url: str | None, eng) -> None:  # noqa: ANN001
        rep = status_bot(eng, 1, self.world.extract, client, self.out / "inbox", day, limit=10)
        for ev in rep.events:
            self._event(f"status:{ev.subject}:{ev.outcome}:{ev.detail}", day, "9 status bot", "Status bot", "status", ev.subject, ev.outcome, ev.detail)
        if portal_url and day.toordinal() % 7 == 0:
            pend = [cid for cid, d in sorted(self._all_cases().items()) if not d.issued and d.received and (day - d.received).days >= 10][:5]
            if pend:
                drv = HttpDriver(portal_url)
                try:
                    for r in claim_status_bot(drv, PORTAL_USER, PORTAL_PASSWORD, pend, self.out / "evidence" / str(day)):
                        self._event(f"portal:{r.claim}:{r.status}:{r.reason}", day, "9 portal bot", "Portal bot (Runner)", "portal", r.claim, r.outcome, f"{r.status}; {r.reason}".strip("; "))
                finally:
                    drv.close()

    # ------------------------------------------------------------------------------------------ the whole run
    def run(self) -> Result:
        eng = _engine_for(self.out) if self.cfg.engine else None
        app = create_clearinghouse(self.world, token=TOKEN, today=self.cfg.start)
        portal_app = create_portal(self.world, PORTAL_USER, PORTAL_PASSWORD)
        try:
            if self.cfg.serve:
                with _Srv(app, _free_port()) as ch, _Srv(portal_app, _free_port()) as portal:
                    self._loop(ClearinghouseClient(ch.url, TOKEN), portal.url, eng)
            else:
                from fastapi.testclient import TestClient

                self._loop(ClearinghouseClient("http://testserver", TOKEN, http=TestClient(app)), None, eng)
        finally:
            if eng is not None:
                eng.dispose()
        return Result(self.finish())

    def _loop(self, client: ClearinghouseClient, portal_url: str | None, eng) -> None:  # noqa: ANN001
        first = min(b for _, _, b, _ in self.schedule())
        day = date.fromisoformat(self.state["day"]) + timedelta(days=1) if self.state["day"] else first
        end = self.end_day()
        while day <= end:
            self.tick(day, client, portal_url, eng)
            if self.cfg.early_stop and self._settled(day):
                break
            day += timedelta(days=1)
        client.close()

    def _settled(self, day: date) -> bool:
        """Every encounter is billed and paid out, waiting for a coder, or rejected, and `react_days` have passed since the last remit."""
        encs = list(self.state["enc"].values())
        if len(encs) < len(self.visits) or any(e["stage"] not in ("adjudicated", "rejected", "pending_coder") for e in encs):
            return False
        remits = [date.fromisoformat(e["remit_date"]) for e in encs if e.get("remit_date")]
        if any(e.get("claim") and e["stage"] == "adjudicated" and e["claim"] not in self.state["issued"] for e in encs):
            return False
        last = max(remits) if remits else date.fromisoformat(max(e["visit_day"] for e in encs))
        return day >= last + timedelta(days=self.cfg.react_days)

    def finish(self) -> dict:
        (self.out / "truth.csv").write_text(self._all_truth_csv(), encoding="utf-8")
        stages: dict[str, int] = {}
        for e in self.state["enc"].values():
            stages[e["stage"]] = stages.get(e["stage"], 0) + 1
        pend = [{"encounter": k, "visit": e["visit_id"], "reason": e["coding"]["reason"], "note": e["coding"]["note"]} for k, e in sorted(self.state["enc"].items()) if e["stage"] == "pending_coder"]
        (self.out / "coder_queue.jsonl").write_text("".join(json.dumps(p) + "\n" for p in pend), encoding="utf-8")
        truth = list(csv.DictReader((self.out / "truth.csv").read_text("utf-8").splitlines()))
        cards = {}
        if self.cfg.engine and (self.out / "engine.sqlite").exists():
            eng = _engine_for(self.out)
            mine = {e["claim"] for e in self.state["enc"].values() if e.get("claim")}
            for c in open_cards(eng, 1, self.end_day()):
                if str(c.get("claim")) in mine:
                    k = f"{c.get('agent')}:{c.get('action_type')}"
                    cards[k] = cards.get(k, 0) + 1
            eng.dispose()
        summary = {
            "encounters": len(self.state["enc"]), "stages": stages, "end_day": self.state["day"],
            "coding": _count(e["coding"]["route"] + (":" + e["coding"]["reason"] if e["coding"]["reason"] else "") for e in self.state["enc"].values() if e.get("coding")),
            "payer_outcomes": _count(r["outcome"] for r in truth), "payer_deviations": _count(r["deviation"] for r in truth if r["deviation"]),
            "pended": sum(int(r["pended"]) for r in truth), "remits_issued": len(self.state["issued"]),
            "cards_for_stream_claims": cards, "coder_queue": len(pend), "emr": self.emr.counts(),
        }  # fmt: skip
        (self.out / "summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
        return summary


def _count(items) -> dict:  # noqa: ANN001
    out: dict[str, int] = {}
    for i in items:
        out[i] = out.get(i, 0) + 1
    return out


def _engine_for(out: Path):  # noqa: ANN201
    from sqlalchemy import create_engine, event

    path = out / "engine.sqlite"
    if not path.exists():
        eng = _engine(path)
        eng.dispose()
    eng = create_engine(f"sqlite:///{path}")

    @event.listens_for(eng, "connect")
    def _fk(conn, _rec):  # noqa: ANN001
        conn.execute("PRAGMA foreign_keys=ON")

    return eng


def run_stream(out: Path, cfg: StreamConfig, emr: EmrPort, fresh: bool = False, log=print, crash_after: int | None = None, visits: list[Visit] | None = None) -> dict:  # noqa: ANN001
    if fresh and out.exists():
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    return Stream(cfg, out, emr, log, crash_after, visits).run().summary
