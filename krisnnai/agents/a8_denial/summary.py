"""Summary of A8 decision records: what the replay assigned, by owner, category and disposition."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a8_denial.agent import AGENT_ID
from krisnnai.model import tenant_session


def summarize(engine: Engine, tenant_id: int) -> dict:
    rows = defaultdict(lambda: {"count": 0, "at_risk": Decimal(0), "expected_recovery": Decimal(0)})
    totals = {
        "records": 0,
        "overdue": 0,
        "unrouted": 0,
        "executed": 0,
        "at_risk": Decimal(0),
        "expected_recovery": Decimal(0),
    }
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            key = (p["owner"], p["category"], p["disposition"], p["trigger"])
            at_risk, recovery = Decimal(p["amount_at_risk"]), Decimal(p["expected_recovery"])
            rows[key]["count"] += 1
            rows[key]["at_risk"] += at_risk
            rows[key]["expected_recovery"] += recovery
            totals["records"] += 1
            totals["at_risk"] += at_risk
            totals["expected_recovery"] += recovery
            totals["unrouted"] += 1 if p["unrouted"] else 0
            totals["executed"] += 1 if rec.outcome == "executed" else 0
            if date.fromisoformat(p["deadline"]) < known[rec.event_id].date():
                totals["overdue"] += 1
    groups = [
        {"owner": o, "category": c, "disposition": d, "trigger": t, **v} for (o, c, d, t), v in sorted(rows.items())
    ]
    return {"tenant_id": tenant_id, "totals": totals, "groups": groups}


def format_summary(summary: dict) -> str:
    t = summary["totals"]
    out = [
        f"A8 replay - tenant {summary['tenant_id']}: {t['records']} decisions, {t['executed']} executed, "
        f"{t['overdue']} already past their deadline, {t['unrouted']} unrouted",
        f"amount at risk {t['at_risk']}, expected recovery {t['expected_recovery']}",
        f"{'owner':11s}{'category':26s}{'disposition':18s}{'trigger':13s}"
        f"{'count':>6s}{'at risk':>12s}{'expected':>12s}",
    ]
    for g in summary["groups"]:
        out.append(
            f"{g['owner']:11s}{g['category']:26s}{g['disposition']:18s}{g['trigger']:13s}{g['count']:6d}"
            f"{g['at_risk']:12}{g['expected_recovery']:12}"
        )
    return "\n".join(out)
