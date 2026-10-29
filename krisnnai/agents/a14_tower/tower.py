"""The control tower: one read-only snapshot of how the revenue cycle looks on a given day.

KPIs (M4), a cash forecast with a measured accuracy, the open work across every agent, and the signals that say
something needs a person today. Nothing here writes anything. The same dict feeds the terminal, `--json` and,
later, a screen.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import distinct, func, select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a7_ar import timing
from krisnnai.agents.a14_tower import forecast as fc
from krisnnai.agents.a14_tower import signals as sg
from krisnnai.agents.a14_tower.cards import open_cards
from krisnnai.engine import list_requests
from krisnnai.metrics import compute_all
from krisnnai.model import tenant_session

TOP_CARDS = 10
GAPS = [
    "productivity and staffing forecast: need task / action logs and staff capacity data",
    "load-balancing recommendations: need staff data",
    "forecast is a transparent method, not a fitted model",
]


def _first(rows: list[dict], field: str, **where):
    for r in rows:
        if all(r.get(k) == v for k, v in where.items()):
            return r.get(field)
    return None


def headline(kpis: dict[str, list[dict]]) -> dict:
    return {
        "clean_claim_rate": _first(kpis["clean_claim_rate"], "clean_claim_rate"),
        "rejection_rate": _first(kpis["rejection_rate"], "rejection_rate"),
        "first_pass_paid_rate": _first(kpis["first_pass_paid_rate"], "first_pass_paid_rate"),
        "denial_rate": _first(kpis["denial_rate"], "denial_rate_count", dimension="overall"),
        "days_in_ar": _first(kpis["days_in_ar"], "days_in_ar"),
        "ar_over_90_share": _first(kpis["ar_over_90"], "ar_over_90_share"),
        "net_collection_rate": _first(kpis["net_collection_rate"], "net_collection_rate"),
        "underpayment_amount": _first(kpis["underpayment"], "underpayment_amount"),
    }


def compute_tower(
    engine: Engine, tenant_id: int, as_of: date, backtest_weeks: int = 8, include_kpis: bool = True
) -> dict:
    cards = open_cards(engine, tenant_id, as_of)
    week_ago = open_cards(engine, tenant_id, as_of - timedelta(days=7))
    kpis = compute_all(engine, tenant_id, as_of)
    end = datetime.combine(as_of, time.max)
    with tenant_session(engine, tenant_id) as s:
        forecast = fc.forecast(s, as_of)
        paid_claims = s.scalar(
            select(func.count(distinct(m.Remit.claim_submitter_id)))
            .join(m.Event, m.Event.id == m.Remit.event_id)
            .where(m.Remit.total_paid > 0, m.Event.known_at <= end)
        )
        slow = sg.payer_slowdowns(s, as_of)
        spike = sg.rejection_spike(s, as_of)
    forecast.pop("sids")
    signals = [sg.backlog_growth(len(cards), len(week_ago)), slow, spike, sg.deadline_critical(cards)]
    dates = [as_of - timedelta(days=fc.HORIZON_DAYS + 7 * k) for k in reversed(range(backtest_weeks))]
    out = {
        "tenant_id": tenant_id,
        "as_of": as_of.isoformat(),
        "data_sufficient": paid_claims >= timing.MIN_HISTORY,
        "headline": headline(kpis),
        "forecast": forecast,
        "backtest": fc.backtest(engine, tenant_id, dates) if backtest_weeks else None,
        "backlog": sg.backlog(cards),
        "signals": signals,
        "top_cards": [{k: v for k, v in c.items() if k != "card"} for c in cards[:TOP_CARDS]],
        "pending_approvals": len(list_requests(engine, tenant_id)),
        "gaps": GAPS,
    }
    if include_kpis:
        out["kpis"] = kpis
    return out


def _pct(value) -> str:
    return "n/a" if value is None else f"{Decimal(value):.1%}"


def format_tower(t: dict) -> str:
    h, f, b = t["headline"], t["forecast"], t["backlog"]
    out = [f"RCM control tower - tenant {t['tenant_id']} as of {t['as_of']}", ""]
    out.append(
        f"clean claims {_pct(h['clean_claim_rate'])}   first-pass paid {_pct(h['first_pass_paid_rate'])}   "
        f"denied {_pct(h['denial_rate'])}   rejected {_pct(h['rejection_rate'])}   "
        f"net collection {_pct(h['net_collection_rate'])}"
    )
    days = h["days_in_ar"] if h["days_in_ar"] is not None else "n/a"
    out.append(f"days in A/R {days}   A/R over 90 days {_pct(h['ar_over_90_share'])}")
    n = f["next_28_days"]
    out += [
        "",
        f"Cash forecast, next 28 days: {n['expected']} (80% range {n['low']} to {n['high']}) "
        f"from {n['claims']} open claims",
    ]
    out += [
        f"  week {w['week']} {w['from']}..{w['to']}: {w['expected']:>10} ({w['low']} - {w['high']})" for w in f["weeks"]
    ]
    bt = t["backtest"]
    if bt and bt["dates"]:
        out.append(
            f"  accuracy over {bt['dates']} past forecasts: WAPE {_pct(bt['wape'])}, "
            f"actual inside the range {_pct(bt['coverage'])}"
        )
    out += [
        "",
        f"Open work: {b['items']} items, {b['dollars']} expected value, {b['overdue']} overdue, "
        f"{b['due_soon']} due within 7 days",
    ]
    out += [
        f"  {owner:18s}{g['items']:5d} items {g['dollars']:>10} overdue {g['overdue']}"
        for owner, g in b["by_owner"].items()
    ]
    fired = [s for s in t["signals"] if s["fired"]]
    out += ["", "Signals: " + ("none firing" if not fired else f"{len(fired)} firing")]
    out += [f"  {'FIRING' if s['fired'] else 'ok':7s}{s['signal']:18s}{s['detail']}" for s in t["signals"]]
    out += ["", f"Top of the decision inbox ({t['pending_approvals']} approvals pending):"]
    out += [
        f"  {i:2d}. {c['priority']:>9} {c['agent']:14s}{c['owner']:16s}due {c['deadline']}  {c['title']}"
        for i, c in enumerate(t["top_cards"], start=1)
    ]
    return "\n".join(out)
