"""The sweeper: raises a clearance checkpoint event 3 days and 1 day before each booked appointment.

Events are append-only and carry `known_at` (the checkpoint day), so a replay sees what the front desk would have seen
that morning. Running the same sweep twice adds nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256

from sqlalchemy import select

import krisnnai.model as m
from krisnnai.agents.a1_clearance import config
from krisnnai.model import tenant_session

EVENT_TYPE = "appointment.clearance_due"


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool  # True when this exact sweep was already recorded


def sweep(engine, tenant_id: int, start: date, end: date, checkpoints: tuple[int, ...] = config.CHECKPOINT_DAYS):
    digest = sha256(f"a1sweep|{tenant_id}|{start}|{end}|{checkpoints}".encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        appts = list(
            s.scalars(
                select(m.Appointment).where(m.Appointment.status != "cancelled").order_by(m.Appointment.id)
            )
        )
        sf = m.SourceFile(
            file_name=f"a1sweep_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0, status="loaded"
        )
        s.add(sf)
        s.flush()
        added = 0
        for a in appts:
            for offset in sorted(checkpoints, reverse=True):
                due = a.appt_date - timedelta(days=offset)
                if due < start or due > end or due < a.booked_on:
                    continue  # outside the window, or the visit was not booked yet that day
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
