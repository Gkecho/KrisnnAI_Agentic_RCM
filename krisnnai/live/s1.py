# ruff: noqa: E501
"""S1 of the live encounter stream: ONE encounter through the whole chain, deterministic, one payer.

appointment (OpenEMR REST) -> eligibility 270/271 (mock clearinghouse, answered by the payer sim)
-> visit and note (OpenEMR REST) -> charge and 837P (OpenEMR's own generator) -> clearinghouse 999 + 277CA
-> payer decision (835) -> the engine's daily run -> a queue item.

Demo only, synthetic data, local only (docs/plan_live_encounter_stream.md, ADR-0002). The payer's decision is written
to `truth.jsonl` outside the inbox: agents never see it, only the X12 files it produced.
"""

from __future__ import annotations

import json
import shutil
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import uvicorn
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a14_tower import open_cards
from krisnnai.ingest.eligibility import parse_271
from krisnnai.ingest.x12 import X12Error, read_transactions
from krisnnai.integrations.clearinghouse.client import ClearinghouseClient
from krisnnai.integrations.clearinghouse.mock_server import create_app as create_clearinghouse
from krisnnai.integrations.clearinghouse.x12_out import write_270
from krisnnai.integrations.openemr import billing, seed
from krisnnai.live.coder import Coder, CodingRecord, Policy
from krisnnai.live.payer import PayerSim, remit_day
from krisnnai.live.transcripts import Visit
from krisnnai.live.world import LiveWorld
from krisnnai.model import Base
from krisnnai.ops import run_period
from krisnnai.synthea import x12out

SALT = "live-salt"
TOKEN = "live-local-token"
PAYER_ID, PAYER_NAME = "SYNAETNA", "SYNAETNA Demo Payer"
CPT, CPT_TEXT, FEE = "99213", "Office visit, established patient", "110.00"
DX = ("J02.9", "Acute pharyngitis, unspecified")
ELEMENTS = "assessment|plan"
FEES = {"99213": "110.00", "99214": "160.00", "99203": "150.00", "99204": "220.00"}
CARD_FIELDS = ("agent", "action_type", "owner", "title", "expected_value")


@dataclass
class Event:
    step: str
    tool: str
    bot: str
    subject: str
    outcome: str
    detail: str


@dataclass
class S1Result:
    events: list[Event] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


class _Srv:
    def __init__(self, app, port: int):
        self.server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.url = f"http://127.0.0.1:{port}"

    def __enter__(self):
        self.thread.start()
        for _ in range(100):
            if self.server.started:
                return self
            time.sleep(0.1)
        raise RuntimeError("local clearinghouse did not start")

    def __exit__(self, *exc):
        self.server.should_exit = True
        self.thread.join(timeout=10)


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _engine(path: Path):
    eng = create_engine(f"sqlite:///{path}")

    @event.listens_for(eng, "connect")
    def _fk(conn, _rec):  # noqa: ANN001
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(m.Tenant(name="live", patient_salt_key="LIVE_SALT"))
        s.commit()
    return eng


def _w(folder: Path, name: str, text: str) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text, encoding="utf-8")
    return name


def run_s1(work: Path, out: Path, as_of: date, *, deny_cpt: str | None = CPT, carc: str = "50",
           approval: str = "policy:demo-s1-single-code", server=None, log=print, visit: Visit | None = None,
           coder: Coder | None = None) -> S1Result:  # noqa: ANN001
    """Run the chain once. `server` is an OpenEMR seed._Server (built from the work folder when omitted).

    With a `visit` (S2) the transcript is coded by the exception-only coder: a visit that passes every check is charged by
    policy; any other stops here, routed to a coder, with nothing billed.
    """
    res = S1Result()

    def ev(step: str, tool: str, bot: str, subject: str, outcome: str, detail: str) -> None:
        res.events.append(Event(step, tool, bot, subject, outcome, detail))
        log(f"  [{step}] {tool}: {outcome} - {detail}")

    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    inbox = out / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    if server is None:
        from krisnnai.integrations.openemr.auth import OpenEmrAuth

        server = seed._Server(OpenEmrAuth(work))

    # 1. a dummy patient and appointment, booked today for three days out
    n = len(server.rest_rows("/patient")) + 1
    member = f"SYNLV{n:05d}"
    visit_day, booked = as_of + timedelta(days=3), as_of
    body = {"fname": "Synthetic", "lname": member, "pubpid": member, "street": "100 Synthetic Way", "city": "Testville",
            "state": "TX", "postal_code": "75001", "country_code": "US", **seed._synthetic_person(member)}  # fmt: skip
    pat = server.rest_json("POST", "/patient", json=body)["data"]
    pid, puuid = pat["pid"], pat["uuid"]
    prac = server.rest_rows("/practitioner")
    aid = prac[0]["id"] if prac else 1
    appt_id = f"SYNAPL{n:05d}"
    title = seed.encode(appt=appt_id, cpt=CPT, payer=PAYER_ID, booked=booked.isoformat(), status="booked")
    server.rest_json("POST", f"/patient/{pid}/appointment", json={
        "pc_catid": seed.OFFICE_VISIT, "pc_title": title, "pc_hometext": "Synthetic appointment", "pc_duration": "1800",
        "pc_apptstatus": "-", "pc_eventDate": visit_day.isoformat(), "pc_startTime": "09:00",
        "pc_facility": seed.FACILITY_ID, "pc_billing_location": seed.FACILITY_ID, "pc_aid": aid,
    })  # fmt: skip
    ev("1 appointment", "OpenEMR", "openemr", appt_id, "ok", f"booked {booked} for {visit_day} (pid {pid})")

    # 2. the payer sim and the clearinghouse that answers from it
    payer = PayerSim(PAYER_ID, PAYER_NAME, deny={deny_cpt: carc} if deny_cpt else {})
    payer.enrol(member)
    world = LiveWorld(payer, as_of)
    app = create_clearinghouse(world, token=TOKEN, today=as_of)
    with _Srv(app, _free_port()) as ch:
        client = ClearinghouseClient(ch.url, TOKEN)

        # 3. Gatekeeper: eligibility 270 -> 271
        dob = seed._synthetic_person(member)["DOB"].replace("-", "")
        req = write_270(PAYER_ID, PAYER_NAME, member, member, "Synthetic", dob, visit_day, appt_id, 90001, as_of)
        t271 = client.check_eligibility(req)
        _w(inbox, f"271_{appt_id}.x12", t271)
        try:
            r = parse_271(read_transactions(t271)[0], "live")[0]
            ev("2 eligibility", "Eligibility bot", "eligibility", appt_id, "active" if r.active else "inactive",
               "coverage confirmed by the payer sim" if r.active else "coverage not active")  # fmt: skip
        except X12Error:
            ev("2 eligibility", "Eligibility bot", "eligibility", appt_id, "not_found",
               "payer could not find the member")

        # 4. the visit happens: encounter and note in OpenEMR
        when = f"{visit_day} 09:00:00"
        vid = f"SYNVL{n:05d}L1"
        enc = server.rest_json("POST", f"/patient/{puuid}/encounter", json={
            "pc_catid": seed.OFFICE_VISIT, "class_code": "AMB", "sensitivity": "normal", "date": when,
            "onset_date": when,
            "reason": seed.encode(visit=vid, cpt=CPT, units="1", payer=PAYER_ID), "facility_id": seed.FACILITY_ID,
            "billing_facility": seed.FACILITY_ID, "provider_id": aid, "referral_source": "",
        })  # fmt: skip
        eno = int(enc["data"]["encounter"] if "encounter" in enc.get("data", {}) else enc["data"]["id"])
        rec: CodingRecord | None = None
        if visit is not None:
            rec = (coder or Coder(Policy(enabled=True))).code(vid, visit.text, visit.signed, visit_day)
        elements = "|".join(rec.elements) if rec else ELEMENTS
        signed = visit_day.isoformat() if (visit is None or visit.signed) else ""
        note = seed.encode(visit=vid, note_date=visit_day.isoformat(), signed=signed, minutes="",
                           elements=elements)  # fmt: skip
        server.rest_json("POST", f"/patient/{pid}/document", params={"path": seed.DOC_CATEGORY},
                         files={"document": (f"note_{vid}.txt", note.encode(), "text/plain")})  # fmt: skip
        if visit is not None:
            server.rest_json("POST", f"/patient/{pid}/document", params={"path": seed.DOC_CATEGORY},
                             files={"document": (f"transcript_{vid}.txt", visit.text.encode(), "text/plain")})  # fmt: skip
        ev("3 visit", "OpenEMR", "openemr", vid, "ok",
           f"encounter {eno}, a {'signed' if signed else 'UNSIGNED'} note on {visit_day}" + (" and the transcript" if visit else ""))
        cpt, dx, fee = CPT, DX, FEE
        if rec is not None:
            res.summary["coding"] = rec.to_dict()
            if rec.route != "auto":
                ev("3b coder", "Transcript coder", "coder", vid, "routed", f"to a coder: {rec.reason} ({rec.note})")
                res.summary.update({"member": member, "patient_pid": pid, "encounter": eno, "routed_to_coder": rec.reason,
                                    "payer_outcome": None, "cards_for_this_claim": []})  # fmt: skip
                client.close()
                (out / "events.jsonl").write_text("".join(json.dumps(e.__dict__) + "\n" for e in res.events), encoding="utf-8")
                (out / "summary.json").write_text(json.dumps(res.summary, indent=1), encoding="utf-8")
                return res
            cpt, dx, fee, approval = rec.cpt, rec.dx[0], FEES[rec.cpt], rec.approval
            ev("3b coder", "Transcript coder", "coder", vid, "auto-accepted", f"{cpt}, {dx[0]}; {rec.approval}")

        # 5. the charge (S1: one fixed code; S2 replaces this with the transcript coder) and OpenEMR's 837P
        made = billing.charge_and_837(
            billing.Charge(pid, eno, member, PAYER_ID, PAYER_NAME, [dx], [(cpt, CPT_TEXT, 1, fee)]), approval)
        x837 = made["x12"]
        _w(inbox, f"837_{pid}-{eno}.837", x837)
        ev("4 claim", "OpenEMR billing", "openemr", f"{pid}-{eno}", "ok",
           f"837P written by OpenEMR; approval {approval}")

        # 6. clearinghouse: 999 and 277CA
        got = client.submit_claim(x837)
        _w(inbox, f"999_{pid}-{eno}.999", got["999"])
        _w(inbox, f"277CA_{pid}-{eno}.277ca", got["277CA"])
        bad = [r for r in got["results"] if not r["ok"]]
        ev("5 clearinghouse", "Mock clearinghouse", "mock", f"{pid}-{eno}", "rejected" if bad else "accepted",
           bad[0]["reason"] if bad else "999 accepted; 277CA accepted for the payer")  # fmt: skip
        client.close()
        accepted = list(world.accepted)

    # 7. the payer decides on its own; the engine sees only the 835
    truth = []
    for claim in accepted:
        remit = remit_day(visit_day)
        d = payer.decide(claim, remit)
        _w(inbox, f"835_{claim.claim_id}.835", x12out.write_835(claim.payer, remit, [claim], 7001))
        truth.append({"claim": claim.claim_id, "outcome": d.outcome, "reason": d.reason, "remit": remit.isoformat()})
        ev("6 payer", "Payer sim", "mock", claim.claim_id, d.outcome, f"{d.reason}; remit {remit}")
    (out / "truth.csv").write_text(payer.truth_csv(), encoding="utf-8")
    (out / "truth.jsonl").write_text("".join(json.dumps(t) + "\n" for t in truth), encoding="utf-8")

    # 8. the feeds, read back out of OpenEMR through FHIR, for this patient only
    pulled = out / "pull"
    seed.pull(server, pulled)
    for name in ("appointments", "visits", "notes"):
        _filter_feed(pulled / f"{name}.csv", inbox / f"{name}.csv", appt_id if name == "appointments" else vid, name)
    ev("7 feeds", "OpenEMR FHIR", "fhir", member, "ok", "appointment, visit and note read back through FHIR")

    # 9. the engine's daily run, a day after the remit
    day = (truth[0]["remit"] and date.fromisoformat(truth[0]["remit"]) + timedelta(days=1)) if truth else visit_day
    eng = _engine(out / "live.sqlite")
    rep = run_period(eng, 1, SALT, day, inbox=inbox, archive=out / "archive", mode="daily", allow_failed=True)
    cards = open_cards(eng, 1, day)
    mine = [c for c in cards if str(c.get("claim", "")) in {t["claim"] for t in truth}]
    res.summary |= {
        "member": member, "patient_pid": pid, "encounter": eno, "claim": f"{pid}-{eno}", "engine_day": day.isoformat(),
        "engine_status": rep.status, "files_loaded": rep.files_loaded, "files_failed": rep.files_failed,
        "payer_outcome": truth[0]["outcome"] if truth else None,
        "cards_for_this_claim": [{k: str(v) for k, v in c.items() if k in CARD_FIELDS}
                                 for c in mine],  # fmt: skip
        "all_cards": len(cards),
    }
    eng.dispose()
    for c in mine:
        ev("8 agents", f"{c.get('agent')}", "engine", str(c.get("claim")), str(c.get("action_type")),
           str(c.get("title"))[:120])
    (out / "events.jsonl").write_text("".join(json.dumps(e.__dict__) + "\n" for e in res.events), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(res.summary, indent=1), encoding="utf-8")
    return res


def _filter_feed(src: Path, dst: Path, key: str, kind: str) -> None:
    import csv

    col = {"appointments": "appointment_id", "visits": "visit_id", "notes": "visit_id"}[kind]
    with src.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        rows = [r for r in rd if r[col] == key]
        fields = rd.fieldnames or []
    with dst.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
