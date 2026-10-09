"""Point-in-time replay: run an agent over history using only what was known at each event's time (rule 9).

Always in shadow mode and with no adapters, so a replay can never act. Records are keyed on (event, agent, action),
so a second replay finds the first one's records and returns identical fingerprints (rule 7).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine

from krisnai.engine.decision_record import fingerprint
from krisnai.engine.models import ModelProvider
from krisnai.engine.pipeline import Agent, run
from krisnai.model import DecisionRecord, Event, tenant_session


@dataclass(frozen=True)
class ReplayItem:
    event_id: int
    known_at: datetime
    outcome: str
    fingerprint: str


def replay(
    engine: Engine,
    tenant_id: int,
    agent: Agent,
    until: datetime | None = None,
    provider: ModelProvider | None = None,
) -> list[ReplayItem]:
    with tenant_session(engine, tenant_id) as s:
        stmt = select(Event.id, Event.known_at).where(Event.event_type.in_(agent.trigger_types))
        if until is not None:
            stmt = stmt.where(Event.known_at <= until)
        events = [(eid, known) for eid, known in s.execute(stmt.order_by(Event.known_at, Event.id)).all()]
    items: list[ReplayItem] = []
    for event_id, known_at in events:
        res = run(engine, tenant_id, agent, event_id, adapters={}, provider=provider, force_shadow=True)
        if res is None:
            continue
        with tenant_session(engine, tenant_id) as s:
            items.append(ReplayItem(event_id, known_at, res.outcome, fingerprint(s.get(DecisionRecord, res.record_id))))
    return items
