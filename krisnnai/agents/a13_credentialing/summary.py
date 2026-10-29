"""A13 results: open gaps, dollars at risk, and enrollment cycle time from the enrollment feed."""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a13_credentialing.agent import AGENT_ID
from krisnnai.engine import NO_ACTION
from krisnnai.model import tenant_session


def latest(engine: Engine, tenant_id: int) -> dict[str, tuple[str, dict]]:
    """key (npi or npi|payer) -> (action, payload) of its latest decision."""
    out: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            at = known[rec.event_id]
            if p["key"] not in out or at >= out[p["key"]][0]:
                out[p["key"]] = (at, rec.action_type, p)
    return {k: (a, p) for k, (_, a, p) in out.items()}


def cycle_time(engine: Engine, tenant_id: int) -> dict:
    """Days from application to effective date over enrollments that became active."""
    with tenant_session(engine, tenant_id) as s:
        days = [(e.effective_on - e.submitted_on).days for e in s.scalars(select(m.Enrollment))
                if e.submitted_on is not None and e.effective_on is not None]  # fmt: skip
    return {"n": len(days), "mean_days": round(mean(days), 1) if days else None,
            "median_days": median(days) if days else None}  # fmt: skip


def summarize(engine: Engine, tenant_id: int) -> dict:
    final = latest(engine, tenant_id)
    by_gap: dict[str, dict] = defaultdict(lambda: {"count": 0, "amount": Decimal(0)})
    by_action: dict[str, int] = defaultdict(int)
    for action, p in final.values():
        by_action[action] += 1
        if action == NO_ACTION:
            continue
        for g in p["gaps"]:
            by_gap[g["kind"]]["count"] += 1
            by_gap[g["kind"]]["amount"] += Decimal(g["amount"])
    at_risk = sum((v["amount"] for v in by_gap.values()), Decimal(0))
    return {"tenant_id": tenant_id, "by_action": dict(by_action), "by_gap": dict(by_gap), "at_risk": at_risk,
            "cycle_time": cycle_time(engine, tenant_id)}  # fmt: skip


def format_summary(s: dict) -> str:
    c = s["cycle_time"]
    out = [
        f"A13 replay - tenant {s['tenant_id']}: claim payment at risk {s['at_risk']}; enrollment cycle time "
        f"{c['n']} enrollments, mean {c['mean_days']} days, median {c['median_days']}"
    ]
    out += [f"  action {a:36s}{n:6d}" for a, n in sorted(s["by_action"].items())]
    out += [f"  gap    {g:36s}{v['count']:6d} {v['amount']:>12}" for g, v in sorted(s["by_gap"].items())]
    return "\n".join(out)
