"""Approval queue: list, approve, reject. A named human decides; nothing runs without one at L2 / L3.

approve at L2 only marks the draft approved (L2 prepares, it does not run). approve at L3 or L4-over-the-cap runs
the action once through the adapter. reject needs a reason and never runs anything.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

from krisnnai.engine import policy as pol
from krisnnai.engine.adapters.base import Adapter
from krisnnai.engine.pipeline import Agent, Proposal, execute
from krisnnai.model import ApprovalRequest, DecisionRecord, tenant_session


class ApprovalError(Exception):
    pass


def _row(req: ApprovalRequest, rec: DecisionRecord) -> dict:
    return {
        "approval_id": req.id, "status": req.status, "decision_record_id": rec.id, "agent_id": rec.agent_id,
        "action_type": rec.action_type, "materiality_amount": rec.materiality_amount,
        "approver_role": req.approver_role,
        "outcome": rec.outcome, "decided_by": req.decided_by, "reason": req.reason,
        "execution_result": rec.execution_result,
    }  # fmt: skip


def list_requests(engine: Engine, tenant_id: int, status: str | None = "pending") -> list[dict]:
    with tenant_session(engine, tenant_id) as s:
        stmt = select(ApprovalRequest, DecisionRecord).join(
            DecisionRecord, DecisionRecord.id == ApprovalRequest.decision_record_id
        )
        if status:
            stmt = stmt.where(ApprovalRequest.status == status)
        return [_row(req, rec) for req, rec in s.execute(stmt.order_by(ApprovalRequest.id)).all()]


def _load(s, request_id: int, approver: str, approver_role: str | None):
    if not approver or not approver.strip():
        raise ApprovalError("a named approver is required")
    req = s.get(ApprovalRequest, request_id)
    if req is None:
        raise ApprovalError(f"approval request {request_id} does not exist")
    if req.status != "pending":
        raise ApprovalError(f"approval request {request_id} is already {req.status}")
    if req.approver_role and approver_role != req.approver_role:
        raise ApprovalError(f"this request needs the {req.approver_role!r} role")
    return req, s.get(DecisionRecord, req.decision_record_id)


def approve(
    engine: Engine,
    tenant_id: int,
    request_id: int,
    approver: str,
    approver_role: str | None = None,
    adapters: dict[str, Adapter] | None = None,
    agents: dict[str, Agent] | None = None,
) -> dict:
    with tenant_session(engine, tenant_id) as s:
        req, rec = _load(s, request_id, approver, approver_role)
        policy = pol.load_policy(s, rec.action_type)
        if not policy.allowed or policy.mode != "live":
            raise ApprovalError(f"policy for {rec.action_type!r} no longer allows live execution")
        now = datetime.now(UTC).replace(tzinfo=None)
        req.status, req.decided_by, req.decided_at = "approved", approver, now
        rec.approver, rec.approved_at = approver, now
        if rec.autonomy_level >= 3:  # the level applied when the decision was made, not today's policy
            rec.outcome, rec.execution_result = execute(adapters or {}, rec.action_type, json.loads(rec.action_payload))
            agent = (agents or {}).get(rec.agent_id)
            if agent is not None:  # step 8 for an action that ran after approval
                proposal = Proposal(rec.action_type, json.loads(rec.action_payload), Decimal(rec.materiality_amount),
                                    rec.confidence, rec.verification_condition)  # fmt: skip
                v = agent.verify(proposal, rec.execution_result)
                rec.verification_condition, rec.verification_result = v.condition, v.result
        else:
            rec.outcome, rec.execution_result = "approved_draft", "L2 draft approved: prepared only, nothing executed"
        s.commit()
        return _row(req, rec)


def reject(
    engine: Engine,
    tenant_id: int,
    request_id: int,
    approver: str,
    reason: str,
    approver_role: str | None = None,
) -> dict:
    if not reason or not reason.strip():
        raise ApprovalError("a reason is required to reject")
    with tenant_session(engine, tenant_id) as s:
        req, rec = _load(s, request_id, approver, approver_role)
        now = datetime.now(UTC).replace(tzinfo=None)
        req.status, req.decided_by, req.decided_at, req.reason = "rejected", approver, now, reason.strip()[:500]
        rec.approver, rec.approved_at = approver, now
        rec.outcome, rec.execution_result = "rejected", f"rejected: {reason.strip()}"[:500]
        s.commit()
        return _row(req, rec)
