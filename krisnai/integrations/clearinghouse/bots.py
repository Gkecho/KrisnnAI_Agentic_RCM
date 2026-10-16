"""Bots that act on what the agents flagged, through a clearinghouse client.

    eligibility bot   A1 appointments needing a check          -> 270 -> 271 -> file in the inbox
    status bot        A7 claims needing a status check         -> 276 -> 277 -> file in the inbox
    resubmission bot  A6 claims returned by the clearinghouse  -> replacement 837 -> 999 + 277CA -> files in the inbox

Each response is written as an X12 file where the daily loader will pick it up, so the same agents re-run on the new
facts. Every request and response is logged (identifiers masked). A bot only reads what the practice's own extract
holds and only talks to the client it was given; it changes nothing in any system of record.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.engine import NO_ACTION
from krisnai.integrations.clearinghouse.claim_store import PmExtract
from krisnai.integrations.clearinghouse.client import ClearinghouseClient
from krisnai.integrations.clearinghouse.x12_out import (
    parse_277_status,
    write_270,
    write_276,
    write_corrected_837,
)
from krisnai.ingest.eligibility import parse_271
from krisnai.ingest.x12 import X12Error, read_transactions
from krisnai.model import tenant_session

SALT_FOR_PARSE = "bot-parse-only"  # 271 member ids are hashed by the parser; the hash is discarded here


def mask(value: str) -> str:
    return ("*" * max(len(value) - 3, 0)) + value[-3:] if value else ""


@dataclass
class BotEvent:
    bot: str
    subject: str  # appointment id or claim id
    outcome: str
    detail: str
    request_file: str = ""
    response_files: list[str] = field(default_factory=list)


@dataclass
class BotReport:
    bot: str
    events: list[BotEvent] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.events:
            out[e.outcome] = out.get(e.outcome, 0) + 1
        return out


def latest_decisions(engine: Engine, tenant_id: int, agent_id: str, key: str) -> dict[str, tuple[str, dict]]:
    """key value -> (action, payload) of the latest decision, by the event's known_at."""
    out: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == agent_id)):
            p = json.loads(rec.action_payload)
            values = p.get(key)
            for v in (values if isinstance(values, list) else [values]):
                if not v:
                    continue
                at = known[rec.event_id]
                if v not in out or at >= out[v][0]:
                    out[v] = (at, rec.action_type, p)
    return {k: (a, p) for k, (_, a, p) in out.items() if a != NO_ACTION}


def _write(out_dir: Path, name: str, text: str) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(text, encoding="ascii", newline="")
    return path.name


def _log(log_path: Path | None, ev: BotEvent) -> None:
    if log_path is None:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(ev), sort_keys=True) + "\n")


def eligibility_bot(engine: Engine, tenant_id: int, extract: PmExtract, client: ClearinghouseClient, out_dir: Path,
                    when: date, limit: int = 25, log_path: Path | None = None) -> BotReport:  # fmt: skip
    rep = BotReport("eligibility")
    todo = latest_decisions(engine, tenant_id, "a1_clearance", "appt")
    ctrl = 90000
    # only visits that have not happened yet, soonest first: that is where a fresh answer can still change the outcome
    upcoming = [a for a in todo if a in extract.appointments
                and date.fromisoformat(extract.appointments[a]["appt_date"]) >= when]  # fmt: skip
    for appt_id in sorted(upcoming, key=lambda a: (extract.appointments[a]["appt_date"], a))[:limit]:
        action, p = todo[appt_id]
        row = extract.appointments.get(appt_id)
        claim = next((c for c in extract.claims.values() if c.member_id == (row or {}).get("patient_ref")), None)
        if row is None:
            ev = BotEvent("eligibility", appt_id, "skipped", "appointment not in the practice extract")
        else:
            ctrl += 1
            dos = date.fromisoformat(row["appt_date"])
            payer_name = claim.payer_name if claim and claim.payer_id == row["payer_id"] else row["payer_id"]
            last = claim.last if claim else ""
            first = claim.first if claim else ""
            dob = claim.dob if claim else ""
            req = write_270(row["payer_id"], payer_name, row["patient_ref"], last, first, dob, dos,
                            f"BOT{appt_id}", ctrl, when)  # fmt: skip
            try:
                text = client.check_eligibility(req)
                name = _write(out_dir, f"271_{appt_id}.x12", text)
                recs = parse_271(read_transactions(text)[0], SALT_FOR_PARSE)
                r = recs[0]
                outcome = ("coverage_inactive" if not r.active else "other_payer" if r.other_payer else "active")
                ev = BotEvent("eligibility", appt_id, outcome,
                              f"member {mask(row['patient_ref'])}, {row['payer_id']}, visit {dos}", "",
                              [name])  # fmt: skip
            except X12Error:
                name = _write(out_dir, f"271_{appt_id}.x12", text)
                ev = BotEvent("eligibility", appt_id, "not_found",
                              f"payer could not find member {mask(row['patient_ref'])}", "", [name])  # fmt: skip
        rep.events.append(ev)
        _log(log_path, ev)
    return rep


def status_bot(engine: Engine, tenant_id: int, extract: PmExtract, client: ClearinghouseClient, out_dir: Path,
               when: date, limit: int = 25, log_path: Path | None = None) -> BotReport:  # fmt: skip
    rep = BotReport("status")
    todo = latest_decisions(engine, tenant_id, "a7_ar", "claim")
    ctrl = 91000
    for claim_id in sorted(todo)[:limit]:
        claim = extract.claims.get(claim_id)
        if claim is None:
            ev = BotEvent("status", claim_id, "skipped", "claim not in the practice extract")
        else:
            ctrl += 1
            ans = extract.answers.get(claim_id)
            req = write_276(claim, ans.payer_claim_no if ans else "", f"BOT{claim_id}", ctrl, when)
            text = client.claim_status(req)
            name = _write(out_dir, f"277_{claim_id}.x12", text)
            st = parse_277_status(text)[0]
            meaning = {"A1": "acknowledged", "A2": "accepted", "A3": "rejected", "A4": "rejected", "P1": "pending",
                       "F1": "paid", "F2": "denied", "E1": "not_found"}.get(st.category, st.category)
            ev = BotEvent("status", claim_id, meaning, f"{claim.payer_id}, category {st.category}:{st.code}",
                          "", [name])  # fmt: skip
        rep.events.append(ev)
        _log(log_path, ev)
    return rep


def resubmission_bot(engine: Engine, tenant_id: int, extract: PmExtract, client: ClearinghouseClient, out_dir: Path,
                     when: date, limit: int = 25, log_path: Path | None = None) -> BotReport:  # fmt: skip
    rep = BotReport("resubmission")
    todo = latest_decisions(engine, tenant_id, "a6_submission", "claims")
    ctrl = 92000
    for claim_id in sorted(todo)[:limit]:
        claim, ans = extract.claims.get(claim_id), extract.answers.get(claim_id)
        if claim is None:
            ev = BotEvent("resubmission", claim_id, "skipped", "claim not in the practice extract")
        elif ans is None or ans.state != "rejected":
            ev = BotEvent("resubmission", claim_id, "skipped", "claim is not currently rejected")
        else:
            ctrl += 1
            text = write_corrected_837(claim, ans.payer_claim_no, ctrl, when)
            sent = _write(out_dir, f"837P_{claim_id}_corrected.x12", text)
            res = client.submit_claim(text)
            names = [sent,
                     _write(out_dir, f"999_{claim_id}.x12", res["999"]),
                     _write(out_dir, f"277CA_{claim_id}.x12", res["277CA"])]  # fmt: skip
            ok = bool(res["results"]) and all(r["ok"] for r in res["results"])
            ev = BotEvent("resubmission", claim_id, "accepted" if ok else "rejected_again",
                          "; ".join(r["reason"] for r in res["results"]), sent, names[1:])
        rep.events.append(ev)
        _log(log_path, ev)
    return rep
