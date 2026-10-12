"""Decision engine tables: per-tenant policy, one decision record per agent run, and the approval queue."""

from __future__ import annotations

from sqlalchemy import CHAR, Boolean, DateTime, Integer, Numeric, String, Text

from krisnai.model.base import Base, Decimal, Mapped, Money, Scoped, col, datetime, fk, scoped


class Policy(Scoped, Base):
    """What an action type may do for one tenant. No row means the default: allowed, L0, shadow (never executes)."""

    __tablename__ = "policy"
    __table_args__ = scoped(
        unique=[("action_type",)],
        checks=[("level", "autonomy_level BETWEEN 0 AND 4"), ("mode", "mode IN ('shadow', 'live')")],
        from_file=False,
    )

    action_type: Mapped[str] = col(String(50), "engine config: the action this policy governs")
    allowed: Mapped[bool] = col(Boolean, "engine config: false = the action is denied and never executes")
    autonomy_level: Mapped[int] = col(
        Integer, "engine config: 0 observe, 1 assist, 2 prepare, 3 approve-and-run, 4 bounded"
    )
    mode: Mapped[str] = col(String(10), "engine config: shadow (record only) or live")
    max_amount: Mapped[Decimal | None] = col(Money, "engine config: L4 may run alone only up to this materiality")
    approver_role: Mapped[str | None] = col(String(50), "engine config: role that must approve at L2 / L3")


class DecisionRecord(Scoped, Base):
    """One agent run on one event (CLAUDE.md decision record). `loaded_at` is its created_at."""

    __tablename__ = "decision_record"
    __table_args__ = scoped(
        [("event_id", "event")],
        unique=[("event_id", "agent_id", "action_type")],
        checks=[("level", "autonomy_level BETWEEN 0 AND 4"), ("mode", "mode IN ('shadow', 'live')")],
        from_file=False,
    )

    agent_id: Mapped[str] = col(String(50), "agent run: which agent decided")
    agent_version: Mapped[str] = col(String(20), "agent run: version of that agent")
    event_id: Mapped[int] = fk("event that triggered the run")
    trigger_type: Mapped[str] = col(String(40), "event.event_type of the trigger")
    input_snapshot: Mapped[str] = col(Text, "context pack as JSON with source lineage (files, events, as-of)")
    rules_fired: Mapped[str] = col(Text, "deterministic checks as JSON: rule id + result")
    model_id: Mapped[str | None] = col(String(100), "model provider id when a model was used")
    model_version: Mapped[str | None] = col(String(50), "model version when a model was used")
    prompt_hash: Mapped[str | None] = col(CHAR(64), "SHA-256 of the prompt sent to the model")
    confidence: Mapped[Decimal | None] = col(Numeric(5, 4), "agent confidence 0-1")
    materiality_amount: Mapped[Decimal] = col(Money, "financial materiality of the proposed action, in dollars")
    action_type: Mapped[str] = col(String(50), "proposed action, or no_action")
    action_payload: Mapped[str] = col(Text, "proposed action parameters as JSON")
    autonomy_level: Mapped[int] = col(Integer, "autonomy level applied from policy (0-4)")
    mode: Mapped[str] = col(String(10), "shadow or live, from policy")
    outcome: Mapped[str] = col(
        String(30), "policy outcome: denied | shadow | observed | pending_approval | executed | ..."
    )
    approver: Mapped[str | None] = col(String(100), "named approver for L2 / L3 actions")
    approved_at: Mapped[datetime | None] = col(DateTime, "when the approval or rejection was recorded")
    execution_result: Mapped[str | None] = col(String(500), "what the adapter reported, or why nothing ran")
    verification_condition: Mapped[str | None] = col(
        String(500), "what must be true afterwards for the action to count as done"
    )
    verification_result: Mapped[str | None] = col(String(500), "whether that condition held")


class ApprovalRequest(Scoped, Base):
    """A decision waiting for a named human (L2 prepared drafts, L3 actions, L4 actions over the cap)."""

    __tablename__ = "approval_request"
    __table_args__ = scoped(
        [("decision_record_id", "decision_record")],
        unique=[("decision_record_id",)],
        checks=[("status", "status IN ('pending', 'approved', 'rejected')")],
        from_file=False,
    )

    decision_record_id: Mapped[int] = fk("decision this request is about")
    status: Mapped[str] = col(String(10), "pending, approved or rejected")
    approver_role: Mapped[str | None] = col(String(50), "role asked to decide, from policy")
    decided_by: Mapped[str | None] = col(String(100), "who approved or rejected")
    decided_at: Mapped[datetime | None] = col(DateTime, "when they decided")
    reason: Mapped[str | None] = col(String(500), "rejection reason (required when rejecting)")


class CarcRoute(Scoped, Base):
    """Denial routing table (A8): who owns a claim adjustment reason code and what kind of fix it needs."""

    __tablename__ = "carc_route"
    __table_args__ = scoped(
        unique=[("carc_code",)],
        checks=[
            ("owner", "owner IN ('front_desk', 'coding', 'billing')"),
            ("disposition", "disposition IN ('correctable', 'appealable', 'write_off_review')"),
        ],
        from_file=False,
    )

    carc_code: Mapped[str] = col(String(5), "CAS reason code (CARC) this row routes")
    category: Mapped[str] = col(String(40), "routing config: denial category, e.g. coverage or missing_information")
    owner: Mapped[str] = col(String(20), "routing config: front_desk, coding or billing")
    disposition: Mapped[str] = col(String(30), "routing config: correctable, appealable or write_off_review")
    description: Mapped[str] = col(String(200), "routing config: what the code means, for the person reading the task")


class PayerAppealWindow(Scoped, Base):
    """Days a payer allows for an appeal, counted from the payment date. No row means the agent default."""

    __tablename__ = "payer_appeal_window"
    __table_args__ = scoped([("payer_id", "payer")], unique=[("payer_id",)], from_file=False)

    payer_id: Mapped[int] = fk("payer this window applies to")
    appeal_days: Mapped[int] = col(Integer, "routing config: appeal window in days from the payment date")


class NcciPair(Scoped, Base):
    """Procedure pair that should not be billed together on one date of service (A5). Placeholder rows until CMS data."""

    __tablename__ = "ncci_pair"
    __table_args__ = scoped(
        unique=[("cpt_a", "cpt_b")],
        checks=[("indicator", "modifier_indicator IN ('0', '1')")],
        from_file=False,
    )

    cpt_a: Mapped[str] = col(String(5), "prevention config: column 1 procedure code of the pair")
    cpt_b: Mapped[str] = col(String(5), "prevention config: column 2 procedure code of the pair")
    modifier_indicator: Mapped[str] = col(
        String(1), "prevention config: 1 = a modifier may bypass the edit, 0 = never billable together"
    )


class MueLimit(Scoped, Base):
    """Most units of one procedure per date of service (A5). Placeholder rows until CMS data."""

    __tablename__ = "mue_limit"
    __table_args__ = scoped(unique=[("cpt",)], from_file=False)

    cpt: Mapped[str] = col(String(5), "prevention config: procedure code the limit applies to")
    max_units: Mapped[int] = col(Integer, "prevention config: most units allowed per date of service")


class PayerFilingWindow(Scoped, Base):
    """Days a payer allows to file a claim, counted from the date of service. No row means the agent default."""

    __tablename__ = "payer_filing_window"
    __table_args__ = scoped([("payer_id", "payer")], unique=[("payer_id",)], from_file=False)

    payer_id: Mapped[int] = fk("payer this window applies to")
    filing_days: Mapped[int] = col(Integer, "prevention config: timely filing limit in days from the date of service")
