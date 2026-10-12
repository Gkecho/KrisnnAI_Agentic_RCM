"""A14 control tower agent. Shadow mode only: once a day it looks at the tower and, if a signal fires, proposes one
escalation review for the operations leader. It changes no resource, assigns no work and writes nothing back.

The engine only runs on events, so `krisnai a14 sweep` appends one `tower.daily` event per day (like A7's sweeper).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a14_tower.tower import compute_tower
from krisnai.agents.a15_lite.expected import money
from krisnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult
from krisnai.engine.card import build_card
from krisnai.engine.models import ModelResult
from krisnai.model import tenant_session

AGENT_ID = "a14_tower"
EVENT_TYPE = "tower.daily"
ESCALATION_REVIEW = "a14_escalation_review"
ACTION_TYPES = (ESCALATION_REVIEW,)
OWNER = "operations_leader"  # spec field 8: the operations leader approves resource changes

NEXT_STEPS = [
    "Read the signals and the top of the decision inbox",
    "Decide whether to reassign work, escalate with a payer or change priorities (a person decides)",
]


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool


def sweep(engine, tenant_id: int, start: date, end: date) -> SweepResult:
    """Append one `tower.daily` event per day in [start, end]. A day that already has one is left alone."""
    digest = sha256(f"tower|{tenant_id}|{start}|{end}".encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        have = {k.date() for k in s.scalars(select(m.Event.known_at).where(m.Event.event_type == EVENT_TYPE))}
        sf = m.SourceFile(file_name=f"tower_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0,
                          status="loaded")  # fmt: skip
        s.add(sf)
        s.flush()
        added, day = 0, start
        while day <= end:
            if day not in have:
                added += 1
                s.add(m.Event(source_file_id=sf.id, event_type=EVENT_TYPE, isa13=day.strftime("%Y%m%d"), gs06="tower",
                              st02="1", seq_in_file=added, known_at=datetime.combine(day, time.min),
                              payload=json.dumps({"day": day.isoformat()})))  # fmt: skip
            day += timedelta(days=1)
        s.commit()
    return SweepResult(added, False)


class A14TowerAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = (EVENT_TYPE,)

    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        tower = compute_tower(session.get_bind(), session.info["tenant_id"], as_of.date(), backtest_weeks=0,
                              include_kpis=False)  # fmt: skip
        return Context(data=tower, lineage={"event_ids": [event.id], "source_file_ids": [event.source_file_id]})

    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        d = ctx.data
        checks = [RuleResult("data_sufficient", d["data_sufficient"], "enough paid claims to judge payer timing")]
        checks += [RuleResult(s["signal"], not s["fired"], s["detail"]) for s in d["signals"]]
        return checks

    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        fired = [s for s in d["signals"] if s["fired"]]
        if not fired:
            return Proposal(NO_ACTION, {"as_of": d["as_of"], "signals": [], "backlog_items": d["backlog"]["items"]})
        as_of = date.fromisoformat(d["as_of"])
        dollars = Decimal(str(d["backlog"]["dollars"]))
        names = ", ".join(s["signal"] for s in fired)
        why = [s["detail"] for s in fired]
        if not d["data_sufficient"]:
            why.append("Little payment history yet: payer timing signals are weak")
        card = build_card(
            f"{len(fired)} signal(s) need attention: {names}", why, money(dollars), money(dollars),
            as_of + timedelta(days=1), OWNER, NEXT_STEPS,
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "as_of": d["as_of"], "signals": fired, "backlog_items": d["backlog"]["items"],
            "backlog_dollars": str(money(dollars)), "overdue": d["backlog"]["overdue"],
            "due_soon": d["backlog"]["due_soon"], "forecast_next_28_days": d["forecast"]["next_28_days"],
            "top_cards": d["top_cards"][:5], "card": card,
        }  # fmt: skip
        return Proposal(ESCALATION_REVIEW, payload, money(dollars), Decimal("0.80"),
                        f"the operations leader has reviewed the signals by {as_of + timedelta(days=1)}")  # fmt: skip
