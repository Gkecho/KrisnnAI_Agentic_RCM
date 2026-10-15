"""The sweeper: raises one `denial.pattern_found` event for each new qualifying denial cluster, on each sweep date.

A cluster already proposed (an earlier event) or already decided (a learned_rule row) is not raised again. Events are
append-only and carry `known_at`; running the same sweep twice adds nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256

from sqlalchemy import select

import krisnai.model as m
from krisnai.agents.a9_learning import config
from krisnai.agents.a9_learning.clusters import clusters
from krisnai.model import tenant_session

EVENT_TYPE = "denial.pattern_found"


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool  # True when this exact sweep was already recorded


def sweep(engine, tenant_id: int, start: date, end: date, every_days: int = config.SWEEP_EVERY_DAYS):
    digest = sha256(f"a9sweep|{tenant_id}|{start}|{end}|{every_days}".encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        decided = set(s.scalars(select(m.LearnedRule.rule_key)))
        raised = {json.loads(p)["rule_key"] for p in s.scalars(
            select(m.Event.payload).where(m.Event.event_type == EVENT_TYPE))}  # fmt: skip
        sf = m.SourceFile(
            file_name=f"a9sweep_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0, status="loaded"
        )
        s.add(sf)
        s.flush()
        added = 0
        day = start
        while day <= end:
            for c in clusters(s, day):
                if c.key in decided or c.key in raised:
                    continue
                raised.add(c.key)
                added += 1
                payload = {"rule_key": c.key, "payer": c.payer, "cpt": c.cpt, "carc": c.carc, "due_on": day.isoformat()}
                s.add(
                    m.Event(
                        source_file_id=sf.id, event_type=EVENT_TYPE, isa13=day.strftime("%Y%m%d"), gs06="1",
                        st02="1", seq_in_file=added, known_at=datetime.combine(day, time.min),
                        payload=json.dumps(payload, sort_keys=True),
                    )
                )  # fmt: skip
            day += timedelta(days=every_days)
        s.commit()
    return SweepResult(added, False)
