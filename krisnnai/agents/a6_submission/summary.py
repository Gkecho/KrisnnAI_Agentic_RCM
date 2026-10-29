"""Summary of A6 decision records after a replay: what was proposed, for whom, and that nothing was executed."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a6_submission.agent import AGENT_ID
from krisnnai.model import tenant_session


def summarize(engine: Engine, tenant_id: int) -> dict:
    rows = defaultdict(lambda: {"count": 0, "claims": 0, "amount": Decimal(0)})
    totals = {"records": 0, "claims": 0, "executed": 0, "unrouted": 0, "overdue": 0, "amount": Decimal(0)}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            amount = Decimal(p["amount"])
            row = rows[(p["source"], p["status_category"], p["category"], p["kind"], p["owner"], rec.action_type)]
            row["count"] += 1
            row["claims"] += p["claims_total"]
            row["amount"] += amount
            totals["records"] += 1
            totals["claims"] += p["claims_total"]
            totals["amount"] += amount
            totals["unrouted"] += 1 if p["unrouted"] else 0
            totals["executed"] += 1 if rec.outcome == "executed" else 0
            if p["filing_deadline"] and date.fromisoformat(p["filing_deadline"]) < known[rec.event_id].date():
                totals["overdue"] += 1
    groups = [
        {"source": k[0], "status": k[1], "category": k[2], "kind": k[3], "owner": k[4], "action": k[5], **v}
        for k, v in sorted(rows.items())
    ]
    return {"tenant_id": tenant_id, "totals": totals, "groups": groups}


def format_summary(summary: dict) -> str:
    t = summary["totals"]
    out = [
        f"A6 replay - tenant {summary['tenant_id']}: {t['records']} rejections on {t['claims']} claims, "
        f"{t['executed']} executed, {t['overdue']} past the filing limit, {t['unrouted']} unrouted",
        f"amount affected {t['amount']}",
        f"{'source':7s}{'status':7s}{'category':32s}{'kind':11s}{'owner':9s}{'action':22s}{'count':>6s}{'amount':>11s}",
    ]
    for g in summary["groups"]:
        out.append(
            f"{g['source']:7s}{g['status']:7s}{g['category']:32s}{g['kind']:11s}{g['owner']:9s}{g['action']:22s}"
            f"{g['count']:6d}{g['amount']:11.2f}"
        )
    return "\n".join(out)
