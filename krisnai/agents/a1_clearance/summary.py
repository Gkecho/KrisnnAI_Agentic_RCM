"""A1 results: gaps by type, the latest decision per appointment and the pre-service clearance rate."""

from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.agents.a1_clearance.agent import AGENT_ID
from krisnai.engine import NO_ACTION
from krisnai.model import tenant_session


def latest_by_appointment(engine: Engine, tenant_id: int) -> dict[str, dict]:
    """appointment ref -> {action, gaps (kinds), patient_estimate, appt_date} of its latest checkpoint decision."""
    latest: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            at = known[rec.event_id]
            if p["appt"] not in latest or at >= latest[p["appt"]][0]:
                latest[p["appt"]] = (at, rec.action_type, p)
    return {
        ref: {
            "action": action, "gaps": [g["kind"] for g in p.get("gaps", [])],
            "patient_estimate": p.get("patient_estimate"), "appt_date": p.get("appt_date"),
        }
        for ref, (_, action, p) in latest.items()
    }  # fmt: skip


def summarize(engine: Engine, tenant_id: int) -> dict:
    final = latest_by_appointment(engine, tenant_id)
    by_gap: dict[str, int] = defaultdict(int)
    by_action: dict[str, int] = defaultdict(int)
    for v in final.values():
        by_action[v["action"]] += 1
        for g in v["gaps"]:
            by_gap[g] += 1
    total = len(final)
    cleared = by_action.get(NO_ACTION, 0)
    return {
        "tenant_id": tenant_id, "appointments": total, "cleared": cleared,
        "clearance_rate": (cleared / total) if total else None,
        "estimates": sum(1 for v in final.values() if v["patient_estimate"] is not None),
        "by_action": dict(by_action), "by_gap": dict(by_gap),
    }  # fmt: skip


def format_summary(summary: dict) -> str:
    rate = summary["clearance_rate"]
    out = [
        f"A1 replay - tenant {summary['tenant_id']}: {summary['appointments']} appointments, "
        f"{summary['cleared']} cleared ({'n/a' if rate is None else f'{rate:.1%}'}), "
        f"{summary['estimates']} with a patient estimate",
    ]
    out += [f"  action {a:30s}{n:6d}" for a, n in sorted(summary["by_action"].items())]
    out += [f"  gap    {g:30s}{n:6d}" for g, n in sorted(summary["by_gap"].items())]
    return "\n".join(out)
