"""A dummy agent that exercises all 8 engine steps. Fabricated; it proposes a note and nothing else."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.engine import Agent, Context, Proposal, RuleResult, Verification, known_event_ids
from krisnnai.engine.adapters import AdapterResult
from krisnnai.engine.models import ModelResult

TRIGGER = "test.trigger"


class DummyAgent(Agent):
    agent_id = "dummy"
    version = "1.0"
    trigger_types = (TRIGGER,)

    def __init__(self, action: str = "add_note", confidence: str = "0.95", failing_blocking_rule: bool = False):
        self.action = action
        self.confidence = Decimal(confidence)
        self.failing_blocking_rule = failing_blocking_rule

    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        ids = known_event_ids(session, as_of)  # only what was known at the event's time
        return Context(
            data={"seen": len(ids), "amount": json.loads(event.payload)["amount"]},
            lineage={"event_ids": ids, "source_file_ids": [event.source_file_id]},
        )

    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        checks = [RuleResult("amount_is_positive", Decimal(ctx.data["amount"]) > 0)]
        if self.failing_blocking_rule:
            checks.append(RuleResult("must_have_authorization", False, "no authorization on file", blocking=True))
        return checks

    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        return f"write a note for {ctx.data['seen']} events"

    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        return Proposal(
            action_type=self.action,
            payload={"note": f"saw {ctx.data['seen']} events", "model": model.text if model else None},
            materiality=Decimal(ctx.data["amount"]),
            confidence=self.confidence,
            verification_condition="the note exists in the outbox",
        )

    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        done = execution_result.startswith("queued") or execution_result.startswith("spy")
        return Verification(proposal.verification_condition, "confirmed" if done else "not_run")


class SpyAdapter:
    """Counts calls so tests can prove an adapter was (or was never) reached."""

    name = "spy"

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute(self, action_type: str, payload: dict) -> AdapterResult:
        self.calls.append((action_type, dict(payload)))
        return AdapterResult(True, "spy: ran")
