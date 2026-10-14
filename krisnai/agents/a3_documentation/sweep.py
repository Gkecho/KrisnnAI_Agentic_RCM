"""The sweeper: turns "this visit has a documentation gap" into an event the engine can act on.

On each sweep date every visit is checked as of that date. A visit with an actionable gap gets a `visit.doc_check`
event when it first shows a gap, again when its set of gaps changes, and every `repeat_days` while it stays open. When a
previously flagged visit comes clean one closing event (no gaps) is raised so the agent can close its card. Events are
append-only and carry `known_at`; running the same sweep twice adds nothing.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256

from sqlalchemy import select

import krisnai.model as m
from krisnai.agents.a3_documentation import config, rules
from krisnai.model import tenant_session

EVENT_TYPE = "visit.doc_check"


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool  # True when this exact sweep was already recorded


def load_notes(session) -> dict[str, rules.Note]:
    return {
        n.visit_ref: rules.Note(
            n.note_date, n.signed_date, n.minutes, tuple(e for e in n.elements.split(",") if e)
        )
        for n in session.scalars(select(m.VisitNote))
    }


def load_charge_dates(session) -> dict[str, list[date]]:
    out: dict[str, list[date]] = defaultdict(list)
    for ref, entered in session.execute(select(m.Charge.visit_ref, m.Charge.entered_date)):
        out[ref].append(entered)
    return out


def load_billed(session) -> dict[tuple, date]:
    """(payer, patient, service date, cpt) -> the day the first claim carrying that service became known."""
    out: dict[tuple, date] = {}
    rows = session.execute(
        select(m.Claim.payer_id, m.Claim.patient_ref_id, m.Claim.service_date, m.ClaimLine.cpt, m.Event.known_at)
        .join(m.ClaimLine, m.ClaimLine.claim_id == m.Claim.id)
        .join(m.Event, m.Event.id == m.Claim.event_id)
    )
    for payer, patient, dos, cpt, known in rows:
        key = (payer, patient, dos, cpt)
        if key not in out or known.date() < out[key]:
            out[key] = known.date()
    return out


def sweep(engine, tenant_id: int, start: date, end: date, every_days: int = 7, repeat_days: int = config.REPEAT_DAYS):
    digest = sha256(f"a3sweep|{tenant_id}|{start}|{end}|{every_days}|{repeat_days}".encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        visits = list(s.scalars(select(m.Visit).order_by(m.Visit.id)))
        notes, charges, billed = load_notes(s), load_charge_dates(s), load_billed(s)
        last: dict[str, tuple[date, tuple[str, ...]]] = {}  # visit ref -> (day, gap kinds) of its latest event
        rounds: dict[str, int] = defaultdict(int)
        for payload in s.scalars(select(m.Event.payload).where(m.Event.event_type == EVENT_TYPE)):
            p = json.loads(payload)
            day, kinds = date.fromisoformat(p["due_on"]), tuple(p["gaps"])
            if p["visit"] not in last or day >= last[p["visit"]][0]:
                last[p["visit"]] = (day, kinds)
            rounds[p["visit"]] += 1

        sf = m.SourceFile(
            file_name=f"a3sweep_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0, status="loaded"
        )
        s.add(sf)
        s.flush()
        added = 0
        day = start
        while day <= end:
            at = datetime.combine(day, time.min)
            for v in visits:
                if v.service_date > day:
                    continue
                key = (v.payer_id, v.patient_ref_id, v.service_date, v.cpt)
                is_billed = key in billed and billed[key] <= day
                gaps = [
                    g for g in rules.check(
                        v.service_date, v.cpt, notes.get(v.visit_ref), charges.get(v.visit_ref, []), is_billed, day
                    )
                    if g.actionable
                ]  # fmt: skip
                kinds = tuple(g.kind for g in gaps)
                prev = last.get(v.visit_ref)
                if kinds:
                    due = prev is None or not prev[1] or prev[1] != kinds or (day - prev[0]).days >= repeat_days
                else:
                    due = prev is not None and bool(prev[1])  # a flagged visit came clean: close it
                if not due:
                    continue
                rounds[v.visit_ref] += 1
                last[v.visit_ref] = (day, kinds)
                payload = {"visit": v.visit_ref, "due_on": day.isoformat(), "gaps": list(kinds),
                           "round": rounds[v.visit_ref]}  # fmt: skip
                s.add(
                    m.Event(
                        source_file_id=sf.id, event_type=EVENT_TYPE, isa13=day.strftime("%Y%m%d"),
                        gs06=str(v.id), st02=str(rounds[v.visit_ref]), seq_in_file=added + 1, known_at=at,
                        payload=json.dumps(payload, sort_keys=True),
                    )
                )  # fmt: skip
                added += 1
            day += timedelta(days=every_days)
        s.commit()
    return SweepResult(added, False)
