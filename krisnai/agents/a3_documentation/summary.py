"""A3 results: gaps found by type, missed-charge dollars, and the charge-lag KPI from the charge log."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.agents.a3_documentation import config
from krisnai.agents.a3_documentation.agent import AGENT_ID, CHARGE_REVIEW
from krisnai.engine import NO_ACTION
from krisnai.model import tenant_session


def charge_lag(engine: Engine, tenant_id: int, as_of: date) -> dict:
    """Days from service to the first charge entered, over visits whose charge was known by `as_of`."""
    lags: dict[str, int] = {}
    with tenant_session(engine, tenant_id) as s:
        service = {v.visit_ref: v.service_date for v in s.scalars(select(m.Visit))}
        first: dict[str, date] = {}
        for ref, entered in s.execute(select(m.Charge.visit_ref, m.Charge.entered_date)):
            if entered <= as_of and ref in service and (ref not in first or entered < first[ref]):
                first[ref] = entered
    for ref, entered in first.items():
        lags[ref] = (entered - service[ref]).days
    values = list(lags.values())
    late = sorted(r for r, d in lags.items() if d > config.CHARGE_LAG_DAYS)
    return {
        "visits": len(values), "mean_days": round(mean(values), 2) if values else None,
        "median_days": median(values) if values else None,
        "over_threshold": len(late), "late_visits": late,
    }  # fmt: skip


def summarize(engine: Engine, tenant_id: int, as_of: date | None = None) -> dict:
    by_action: dict[str, dict] = defaultdict(lambda: {"visits": 0, "amount": Decimal(0)})
    by_gap: dict[str, int] = defaultdict(int)
    totals = {"records": 0, "open_visits": 0, "executed": 0, "missed_charge": Decimal(0)}
    latest: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            totals["records"] += 1
            totals["executed"] += 1 if rec.outcome == "executed" else 0
            p = json.loads(rec.action_payload)
            cur = latest.get(p["visit"])
            if cur is None or known[rec.event_id] >= cur[0]:
                latest[p["visit"]] = (known[rec.event_id], rec.action_type, p)
    for _, action, p in latest.values():
        if action == NO_ACTION:
            continue
        totals["open_visits"] += 1
        by_action[action]["visits"] += 1
        by_action[action]["amount"] += Decimal(p["amount"])
        for g in p["gaps"]:
            by_gap[g["kind"]] += 1
        if action == CHARGE_REVIEW:
            totals["missed_charge"] += Decimal(p["amount"])
    out = {"tenant_id": tenant_id, "totals": totals, "by_action": dict(by_action), "by_gap": dict(by_gap)}
    if as_of is not None:
        out["charge_lag"] = charge_lag(engine, tenant_id, as_of)
    return out


def open_visits(engine: Engine, tenant_id: int) -> dict[str, list[str]]:
    """visit ref -> gap kinds of its latest decision (only visits that are still open)."""
    latest: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            cur = latest.get(p["visit"])
            if cur is None or known[rec.event_id] >= cur[0]:
                latest[p["visit"]] = (known[rec.event_id], rec.action_type, p)
    return {
        v: [g["kind"] for g in p["gaps"]] for v, (_, action, p) in latest.items() if action != NO_ACTION
    }  # fmt: skip


def format_summary(summary: dict) -> str:
    t = summary["totals"]
    out = [
        f"A3 replay - tenant {summary['tenant_id']}: {t['records']} checks, {t['open_visits']} visits still open, "
        f"{t['executed']} executed",
        f"missed charges (documented, not billed): {t['missed_charge']}",
    ]
    for a, v in sorted(summary["by_action"].items()):
        out.append(f"  action {a:24s}{v['visits']:6d} visits {v['amount']:>12}")
    out += [f"  gap    {g:24s}{n:6d}" for g, n in sorted(summary["by_gap"].items())]
    lag = summary.get("charge_lag")
    if lag:
        out.append(
            f"charge lag: {lag['visits']} charged visits, mean {lag['mean_days']} days, median {lag['median_days']}, "
            f"{lag['over_threshold']} over {config.CHARGE_LAG_DAYS} days"
        )
    return "\n".join(out)
