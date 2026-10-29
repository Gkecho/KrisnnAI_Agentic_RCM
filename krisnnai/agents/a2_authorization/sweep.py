"""The sweeper: raises an authorization checkpoint event 7 and 2 days before each booked appointment that needs one.

Only appointments whose payer + CPT is in `auth_requirement` get events. Events are append-only and carry `known_at`
(the checkpoint day); running the same sweep twice adds nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256

from sqlalchemy import select

import krisnnai.model as m
from krisnnai.agents.a2_authorization import config
from krisnnai.model import tenant_session

EVENT_TYPE = "appointment.auth_check"


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool  # True when this exact sweep was already recorded


def required_pairs(session) -> set[tuple[int, str]]:
    return {(r.payer_id, r.cpt) for r in session.scalars(select(m.AuthRequirement))}


def sweep(engine, tenant_id: int, start: date, end: date, checkpoints: tuple[int, ...] = config.CHECKPOINT_DAYS):
    digest = sha256(f"a2sweep|{tenant_id}|{start}|{end}|{checkpoints}".encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        required = required_pairs(s)
        appts = [
            a for a in s.scalars(
                select(m.Appointment).where(m.Appointment.status != "cancelled").order_by(m.Appointment.id))
            if (a.payer_id, a.cpt) in required
        ]  # fmt: skip
        sf = m.SourceFile(
            file_name=f"a2sweep_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0, status="loaded"
        )
        s.add(sf)
        s.flush()
        added = 0
        for a in appts:
            for offset in sorted(checkpoints, reverse=True):
                due = a.appt_date - timedelta(days=offset)
                if due < start or due > end or due < a.booked_on:
                    continue
                added += 1
                payload = {"appt": a.appt_ref, "checkpoint_days": offset, "due_on": due.isoformat()}
                s.add(
                    m.Event(
                        source_file_id=sf.id, event_type=EVENT_TYPE, isa13=due.strftime("%Y%m%d"),
                        gs06=str(a.id), st02=str(offset), seq_in_file=added,
                        known_at=datetime.combine(due, time.min), payload=json.dumps(payload, sort_keys=True),
                    )
                )  # fmt: skip
        s.commit()
    return SweepResult(added, False)


def seed_defaults(session) -> int:
    """Insert any default payer + CPT requirement the tenant lacks, for every payer it has."""
    have = required_pairs(session)
    added = 0
    for payer in session.scalars(select(m.Payer)):
        for cpt in config.DEFAULT_CPTS:
            if (payer.id, cpt) not in have:
                session.add(m.AuthRequirement(payer_id=payer.id, cpt=cpt, validity_days=config.VALIDITY_DAYS))
                added += 1
    session.flush()
    return added
