"""The human decision on a proposed rule: approve or reject, by name. The only way a learned rule takes effect."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a9_learning.agent import AGENT_ID, RULE_REVIEW
from krisnnai.model import tenant_session

APPROVED, REJECTED = "approved", "rejected"


class DecisionError(Exception):
    pass


def decide(engine: Engine, tenant_id: int, rule_key: str, status: str, by: str, today: date | None = None) -> dict:
    """Record a person's decision. The proposal must exist (A9 raised it); the approver's name is required."""
    if status not in (APPROVED, REJECTED):
        raise DecisionError(f"status must be {APPROVED} or {REJECTED}")
    if not by or not by.strip():
        raise DecisionError("a named approver is required (--by NAME)")
    today = today or date.today()
    with tenant_session(engine, tenant_id) as s:
        proposal = None
        for rec in s.scalars(
            select(m.DecisionRecord)
            .where(m.DecisionRecord.agent_id == AGENT_ID, m.DecisionRecord.action_type == RULE_REVIEW)
            .order_by(m.DecisionRecord.id.desc())
        ):
            p = json.loads(rec.action_payload)
            if p["rule_key"] == rule_key:
                proposal = p
                break
        if proposal is None:
            raise DecisionError(f"no A9 proposal for rule {rule_key}; run a9 replay first")
        payer = s.scalars(select(m.Payer).where(m.Payer.payer_id_code == proposal["payer"])).first()
        if payer is None:
            raise DecisionError(f"payer {proposal['payer']} is not loaded")
        row = s.scalars(select(m.LearnedRule).where(m.LearnedRule.rule_key == rule_key)).first()
        if row is None:
            row = m.LearnedRule(
                rule_key=rule_key, payer_id=payer.id, cpt=proposal["cpt"],
                carc=proposal["carc"], proposed_on=date.fromisoformat(proposal["proposed_on"]), status=status,
                n_denials=proposal["n_denials"], n_adjudicated=proposal["n_adjudicated"],
                denial_rate=Decimal(proposal["rate"]),
            )  # fmt: skip
            s.add(row)
        row.status, row.approved_by, row.decided_on = status, by.strip(), today
        s.commit()
        return {"rule_key": rule_key, "status": status, "by": by.strip(), "on": today.isoformat()}
