"""Policy: what may an action type do for a tenant. Default for every new action type is allowed + L0 + shadow.

Autonomy levels: L0 observe, L1 assist (rank / explain), L2 prepare (draft for review), L3 approve-and-run
(named approval), L4 bounded autonomous (client caps). Promotion is a data change in the `policy` table backed by
evidence, never a code default.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from krisnai.model import Policy

# Outcomes stored on the decision record
NO_ACTION = "no_action"
DENIED = "denied"
BLOCKED = "blocked_by_check"
SHADOW = "shadow"
OBSERVED = "observed"
ASSISTED = "assisted"
PENDING = "pending_approval"
EXECUTE = "execute"  # decided to run now; the record then ends as executed / adapter_disabled / failed

L4_CONFIDENCE = Decimal("0.90")


@dataclass(frozen=True)
class EffectivePolicy:
    allowed: bool = True
    autonomy_level: int = 0
    mode: str = "shadow"
    max_amount: Decimal | None = None
    approver_role: str | None = None


def load_policy(session: Session, action_type: str) -> EffectivePolicy:
    row = session.scalars(select(Policy).where(Policy.action_type == action_type)).first()
    if row is None:
        return EffectivePolicy()
    return EffectivePolicy(row.allowed, row.autonomy_level, row.mode, row.max_amount, row.approver_role)


def set_policy(
    session: Session,
    action_type: str,
    *,
    allowed: bool = True,
    autonomy_level: int = 0,
    mode: str = "shadow",
    max_amount: Decimal | None = None,
    approver_role: str | None = None,
) -> None:
    """Create or replace the policy row for this tenant + action type (the tenant comes from the session)."""
    row = session.scalars(select(Policy).where(Policy.action_type == action_type)).first()
    if row is None:
        row = Policy(action_type=action_type)
        session.add(row)
    row.allowed, row.autonomy_level, row.mode = allowed, autonomy_level, mode
    row.max_amount, row.approver_role = max_amount, approver_role


def decide(
    policy: EffectivePolicy,
    *,
    action_type: str,
    materiality: Decimal,
    confidence: Decimal | None,
    blocking_failure: bool,
    force_shadow: bool = False,
    l4_confidence: Decimal = L4_CONFIDENCE,
) -> str:
    """Pure function: what the engine does with a proposal. Nothing here touches an adapter."""
    if action_type == NO_ACTION:
        return NO_ACTION
    if not policy.allowed:
        return DENIED
    if blocking_failure:
        return BLOCKED
    if force_shadow or policy.mode == "shadow":
        return SHADOW
    level = policy.autonomy_level
    if level == 0:
        return OBSERVED
    if level == 1:
        return ASSISTED
    if level in (2, 3):
        return PENDING
    within_cap = policy.max_amount is not None and materiality <= policy.max_amount
    confident = confidence is not None and confidence >= l4_confidence
    return EXECUTE if within_cap and confident else PENDING
