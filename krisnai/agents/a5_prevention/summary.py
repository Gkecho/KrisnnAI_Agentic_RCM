"""Summary of A5 decision records: how many claims were checked, which rules failed, and what was proposed."""

from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.agents.a5_prevention.agent import AGENT_ID
from krisnai.engine import NO_ACTION
from krisnai.model import tenant_session


def summarize(engine: Engine, tenant_id: int) -> dict:
    by_action: Counter = Counter()
    by_rule: Counter = Counter()
    at_risk = Decimal(0)
    executed = 0
    with tenant_session(engine, tenant_id) as s:
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            by_action[rec.action_type] += 1
            executed += 1 if rec.outcome == "executed" else 0
            if rec.action_type != NO_ACTION:
                p = json.loads(rec.action_payload)
                at_risk += Decimal(p["amount_at_risk"])
                for f in p["failed_rules"]:
                    by_rule[f["rule"]] += 1
    return {
        "tenant_id": tenant_id,
        "claims": sum(by_action.values()),
        "executed": executed,
        "flagged": sum(n for a, n in by_action.items() if a != NO_ACTION),
        "at_risk": at_risk,
        "by_action": dict(by_action),
        "by_rule": dict(by_rule),
    }


def format_summary(summary: dict) -> str:
    out = [
        f"A5 replay - tenant {summary['tenant_id']}: {summary['claims']} claims checked, {summary['flagged']} flagged, "
        f"{summary['executed']} executed",
        f"charges on flagged claims {summary['at_risk']}",
    ]
    out += [f"  {action:16s}{n:6d}" for action, n in sorted(summary["by_action"].items())]
    out += [f"  rule {rule:20s}{n:6d}" for rule, n in sorted(summary["by_rule"].items())]
    return "\n".join(out)
