"""A2 results: gaps by type, the authorization-covered share, and turnaround from the authorization feed."""

from __future__ import annotations

import json
from collections import defaultdict
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a2_authorization.agent import AGENT_ID
from krisnnai.engine import NO_ACTION
from krisnnai.model import tenant_session


def latest_by_appointment(engine: Engine, tenant_id: int) -> dict[str, dict]:
    """appointment ref -> {action, gaps (kinds), appt_date} of its latest checkpoint decision."""
    latest: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            at = known[rec.event_id]
            if p["appt"] not in latest or at >= latest[p["appt"]][0]:
                latest[p["appt"]] = (at, rec.action_type, p)
    return {
        ref: {"action": action, "gaps": [g["kind"] for g in p.get("gaps", [])], "appt_date": p.get("appt_date")}
        for ref, (_, action, p) in latest.items()
    }  # fmt: skip


def turnaround(engine: Engine, tenant_id: int) -> dict:
    """Days from request to decision over decided authorizations."""
    with tenant_session(engine, tenant_id) as s:
        days = [(a.decided_on - a.requested_on).days
                for a in s.scalars(select(m.Authorization)) if a.decided_on is not None]  # fmt: skip
        pending = sum(1 for a in s.scalars(select(m.Authorization)) if a.decided_on is None)
    return {"decided": len(days), "pending": pending, "mean_days": round(mean(days), 2) if days else None,
            "median_days": median(days) if days else None}  # fmt: skip


def summarize(engine: Engine, tenant_id: int) -> dict:
    final = latest_by_appointment(engine, tenant_id)
    by_gap: dict[str, int] = defaultdict(int)
    by_action: dict[str, int] = defaultdict(int)
    for v in final.values():
        by_action[v["action"]] += 1
        for g in v["gaps"]:
            by_gap[g] += 1
    covered = by_action.get(NO_ACTION, 0)
    return {
        "tenant_id": tenant_id, "required_appointments": len(final), "covered": covered,
        "covered_rate": (covered / len(final)) if final else None, "by_action": dict(by_action),
        "by_gap": dict(by_gap), "turnaround": turnaround(engine, tenant_id),
    }  # fmt: skip


def format_summary(summary: dict) -> str:
    rate = summary["covered_rate"]
    t = summary["turnaround"]
    out = [
        f"A2 replay - tenant {summary['tenant_id']}: {summary['required_appointments']} appointments needing "
        f"authorization, {summary['covered']} covered ({'n/a' if rate is None else f'{rate:.1%}'})",
        f"turnaround: {t['decided']} decided, mean {t['mean_days']} days, median {t['median_days']}, "
        f"{t['pending']} still pending",
    ]
    out += [f"  action {a:30s}{n:6d}" for a, n in sorted(summary["by_action"].items())]
    out += [f"  gap    {g:30s}{n:6d}" for g, n in sorted(summary["by_gap"].items())]
    return "\n".join(out)
