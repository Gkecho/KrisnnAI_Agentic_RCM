"""Summary of A7 decision records after a replay: what was proposed, for how much, and that nothing was executed."""

from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.agents.a7_ar.agent import AGENT_ID
from krisnai.engine import NO_ACTION
from krisnai.model import tenant_session


def summarize(engine: Engine, tenant_id: int) -> dict:
    by_action: Counter = Counter()
    by_issue: Counter = Counter()
    claims: set[str] = set()
    executed, amount = 0, Decimal(0)
    with tenant_session(engine, tenant_id) as s:
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            by_action[rec.action_type] += 1
            executed += 1 if rec.outcome == "executed" else 0
            if rec.action_type != NO_ACTION:
                p = json.loads(rec.action_payload)
                by_issue[p["issue"]] += 1
                claims.add(p["claim"])
                amount += Decimal(p["amount"])
    return {
        "tenant_id": tenant_id,
        "records": sum(by_action.values()),
        "executed": executed,
        "claims": len(claims),
        "amount": amount,
        "by_action": dict(by_action),
        "by_issue": dict(by_issue),
    }


def format_summary(summary: dict) -> str:
    out = [
        f"A7 replay - tenant {summary['tenant_id']}: {summary['records']} decisions on {summary['claims']} claims, "
        f"{summary['executed']} executed",
        f"unpaid amount across decisions {summary['amount']} (a claim counts once per follow-up round)",
    ]
    out += [f"  {action:24s}{n:6d}" for action, n in sorted(summary["by_action"].items())]
    out += [f"  issue {issue:24s}{n:6d}" for issue, n in sorted(summary["by_issue"].items())]
    return "\n".join(out)
