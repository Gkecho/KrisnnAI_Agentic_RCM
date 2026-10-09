"""The 8-step pipeline every agent runs through (BUILD_PLAN M6).

    1 trigger -> 2 context pack -> 3 deterministic checks -> 4 model reasoning -> 5 confidence and materiality
      -> 6 human checkpoint -> 7 action adapter -> 8 verify and learn

The agent supplies steps 1-5 and 8. The engine owns 6 and 7, so policy cannot be skipped: a denied action never
reaches an adapter, shadow mode never calls one, and every run writes exactly one decision record (rule 5). A repeat
run on the same event finds the existing record and does nothing (rule 7).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from krisnai.engine import policy as pol
from krisnai.engine.adapters.base import Adapter, AdapterDisabled
from krisnai.engine.decision_record import canonical_json, write_record
from krisnai.engine.models import ModelProvider, ModelResult, StubProvider, call_model
from krisnai.model import ApprovalRequest, DecisionRecord, Event, tenant_session


@dataclass
class Context:
    """Step 2 output. `data` is what the agent reasoned over; `lineage` says where it came from."""

    data: dict
    lineage: dict = field(default_factory=dict)  # e.g. {"event_ids": [...], "source_file_ids": [...]}


@dataclass
class RuleResult:
    rule_id: str
    result: bool
    detail: str = ""
    blocking: bool = False  # a failed blocking rule stops execution (the record still explains why)


@dataclass
class Proposal:
    """Step 5 output."""

    action_type: str  # use policy.NO_ACTION when the agent proposes nothing
    payload: dict = field(default_factory=dict)
    materiality: Decimal = Decimal(0)
    confidence: Decimal | None = None
    verification_condition: str | None = None


@dataclass
class Verification:
    condition: str | None
    result: str


class Agent(ABC):
    agent_id: str
    version: str
    trigger_types: tuple[str, ...]

    def wants(self, event: Event) -> bool:  # step 1
        return event.event_type in self.trigger_types

    @abstractmethod
    def context_pack(self, session: Session, event: Event, as_of: datetime) -> Context:  # step 2
        """Build the context using only data known at `as_of` (rule 9). Use `known_event_ids`."""

    @abstractmethod
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:  # step 3
        ...

    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:  # step 4 (optional)
        return None

    @abstractmethod
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:  # step 5
        ...

    def verify(self, proposal: Proposal, execution_result: str) -> Verification:  # step 8
        return Verification(proposal.verification_condition, "not_run")


@dataclass
class RunResult:
    record_id: int
    outcome: str
    created: bool  # False when the record already existed (idempotent repeat)
    approval_id: int | None = None


def known_event_ids(session: Session, as_of: datetime) -> list[int]:
    """Ids of this tenant's events known at or before `as_of`: the only way an agent should select history."""
    return list(session.scalars(select(Event.id).where(Event.known_at <= as_of).order_by(Event.known_at, Event.id)))


def run(
    engine: Engine,
    tenant_id: int,
    agent: Agent,
    event_id: int,
    adapters: dict[str, Adapter] | None = None,
    provider: ModelProvider | None = None,
    baa_approved: bool = False,
    force_shadow: bool = False,
    l4_confidence: Decimal = pol.L4_CONFIDENCE,
) -> RunResult | None:
    """Run one agent over one event. Returns None when the agent does not trigger on it."""
    adapters = adapters or {}
    with tenant_session(engine, tenant_id) as s:
        event = s.get(Event, event_id)
        if event is None:
            raise LookupError(f"event {event_id} does not exist for tenant {tenant_id}")
        if not agent.wants(event):
            return None
        ctx = agent.context_pack(s, event, event.known_at)
        checks = agent.deterministic_checks(ctx)
        prompt = agent.model_prompt(ctx, checks)
        model = call_model(provider or StubProvider(), prompt, baa_approved) if prompt is not None else None
        proposal = agent.assess(ctx, checks, model)

        existing = s.scalars(
            select(DecisionRecord).where(
                DecisionRecord.event_id == event_id,
                DecisionRecord.agent_id == agent.agent_id,
                DecisionRecord.action_type == proposal.action_type,
            )
        ).first()
        if existing is not None:
            return RunResult(existing.id, existing.outcome, False)

        policy = pol.load_policy(s, proposal.action_type)
        outcome = pol.decide(
            policy,
            action_type=proposal.action_type,
            materiality=proposal.materiality,
            confidence=proposal.confidence,
            blocking_failure=any(c.blocking and not c.result for c in checks),
            force_shadow=force_shadow,
            l4_confidence=l4_confidence,
        )

        execution_result: str | None = None
        final = outcome
        if outcome == pol.EXECUTE:  # step 7: the only place an adapter is called from a run
            final, execution_result = execute(adapters, proposal.action_type, proposal.payload)
        elif outcome == pol.PENDING:
            execution_result = "waiting for approval"
        elif outcome == pol.SHADOW:
            execution_result = "shadow: not executed"
        elif outcome == pol.DENIED:
            execution_result = "denied by policy: not executed"
        elif outcome == pol.BLOCKED:
            execution_result = "blocked by a failed check: not executed"

        verification = agent.verify(proposal, execution_result or "")  # step 8
        record = write_record(
            s,
            agent_id=agent.agent_id,
            agent_version=agent.version,
            event_id=event_id,
            trigger_type=event.event_type,
            input_snapshot=canonical_json({"as_of": event.known_at, "lineage": ctx.lineage, "data": ctx.data}),
            rules_fired=canonical_json([{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks]),
            model_id=model.model_id if model else None,
            model_version=model.model_version if model else None,
            prompt_hash=model.prompt_hash if model else None,
            confidence=proposal.confidence,
            materiality_amount=proposal.materiality,
            action_type=proposal.action_type,
            action_payload=canonical_json(proposal.payload),
            autonomy_level=policy.autonomy_level,
            mode="shadow" if (force_shadow or policy.mode == "shadow") else "live",
            outcome=final,
            execution_result=execution_result,
            verification_condition=verification.condition,
            verification_result=verification.result,
        )
        approval_id = None
        if final == pol.PENDING:
            req = ApprovalRequest(decision_record_id=record.id, status="pending", approver_role=policy.approver_role)
            s.add(req)
            s.flush()
            approval_id = req.id
        s.commit()
        return RunResult(record.id, final, True, approval_id)


def execute(adapters: dict[str, Adapter], action_type: str, payload: dict) -> tuple[str, str]:
    """Call the adapter registered for this action type. Returns (outcome, execution_result)."""
    adapter = adapters.get(action_type)
    if adapter is None:
        return "no_adapter", f"no adapter registered for {action_type}"
    try:
        res = adapter.execute(action_type, payload)
    except AdapterDisabled as e:
        return "adapter_disabled", str(e)
    except Exception as e:  # an adapter failure must be recorded, not lose the decision
        return "failed", f"{type(e).__name__}: {e}"
    return ("executed" if res.ok else "failed"), res.detail
