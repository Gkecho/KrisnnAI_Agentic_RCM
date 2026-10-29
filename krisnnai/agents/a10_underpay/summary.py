"""Summary of A10 decision records after a replay: dollars short by action, cause and payer."""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a10_underpay.agent import AGENT_ID
from krisnnai.engine import NO_ACTION
from krisnnai.model import tenant_session


def summarize(engine: Engine, tenant_id: int) -> dict:
    by_action: dict[str, dict] = defaultdict(lambda: {"count": 0, "short": Decimal(0)})
    by_cause: dict[str, dict] = defaultdict(lambda: {"lines": 0, "short": Decimal(0)})
    by_payer: dict[str, dict] = defaultdict(lambda: {"claims": 0, "short": Decimal(0)})
    totals = {"records": 0, "flagged": 0, "executed": 0, "short": Decimal(0)}
    with tenant_session(engine, tenant_id) as s:
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            totals["records"] += 1
            totals["executed"] += 1 if rec.outcome == "executed" else 0
            if rec.action_type == NO_ACTION:
                continue
            p = json.loads(rec.action_payload)
            short = Decimal(p["total_gap"])
            totals["flagged"] += 1
            totals["short"] += short
            by_action[rec.action_type]["count"] += 1
            by_action[rec.action_type]["short"] += short
            by_payer[p["payer"]]["claims"] += 1
            by_payer[p["payer"]]["short"] += short
            for ln in p["lines"]:
                by_cause[ln["cause"]]["lines"] += 1
                by_cause[ln["cause"]]["short"] += Decimal(ln["gap"])
    return {"tenant_id": tenant_id, "totals": totals, "by_action": dict(by_action), "by_cause": dict(by_cause),
            "by_payer": dict(by_payer)}  # fmt: skip


def format_summary(summary: dict) -> str:
    t = summary["totals"]
    out = [
        f"A10 replay - tenant {summary['tenant_id']}: {t['records']} payments checked, {t['flagged']} short-paid, "
        f"{t['executed']} executed",
        f"short-paid amount {t['short']}",
    ]
    out += [f"  action {a:26s}{v['count']:6d} claims {v['short']:>12}" for a, v in sorted(summary["by_action"].items())]
    out += [f"  cause  {c:26s}{v['lines']:6d} lines  {v['short']:>12}" for c, v in sorted(summary["by_cause"].items())]
    out += [f"  payer  {p:26s}{v['claims']:6d} claims {v['short']:>12}" for p, v in sorted(summary["by_payer"].items())]
    return "\n".join(out)
