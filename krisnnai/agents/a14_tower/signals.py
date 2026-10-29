"""Backlog and the four anomaly signals. Every threshold here is a placeholder for sign-off (spec field 17).

A signal is a dict: {"signal", "fired", "detail", "items"}. `fired` is the only thing the agent acts on, and the
detail is a sentence a person can read. All of it is computed from data known by `as_of` (rule 9).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a7_ar import timing
from krisnnai.agents.a14_tower.cards import AGE_BUCKETS
from krisnnai.agents.rejections import rejection_sets

BACKLOG_GROWTH = Decimal("0.25")  # open items grew by at least this share in a week...
BACKLOG_MIN_ITEMS = 5  # ...and by at least this many
SLOWDOWN_DAYS = 7  # a payer pays this many days slower than its own baseline...
SLOWDOWN_MIN_CLAIMS = 5  # ...with at least this many paid claims in each window
RECENT_PAID_DAYS, BASELINE_PAID_DAYS = 30, 90
REJECTION_POINTS = Decimal("0.05")  # rejection share up by this many points...
REJECTION_MIN_CLAIMS = 10  # ...among at least this many recent claims
RECENT_SUBMIT_DAYS, BASELINE_SUBMIT_DAYS = 14, 60

ZERO = Decimal(0)


def backlog(cards: list[dict]) -> dict:
    """Open items by owner, by age and by agent, with dollars (expected value) and how many are overdue."""

    def group(key) -> dict:
        out: dict[str, dict] = defaultdict(lambda: {"items": 0, "dollars": ZERO, "overdue": 0, "due_soon": 0})
        for c in cards:
            g = out[key(c)]
            g["items"] += 1
            g["dollars"] += c["expected_value"]
            g["overdue"] += c["overdue"]
            g["due_soon"] += c["due_soon"]
        return dict(sorted(out.items()))

    order = [label for _, label in AGE_BUCKETS] + ["30+"]
    by_age = group(lambda c: c["age_bucket"])
    return {
        "items": len(cards), "dollars": sum((c["expected_value"] for c in cards), ZERO),
        "overdue": sum(c["overdue"] for c in cards), "due_soon": sum(c["due_soon"] for c in cards),
        "by_owner": group(lambda c: c["owner"]), "by_agent": group(lambda c: c["agent"]),
        "by_age": {k: by_age[k] for k in order if k in by_age},
    }  # fmt: skip


def backlog_growth(now_items: int, week_ago_items: int) -> dict:
    grew = now_items - week_ago_items
    fired = grew >= BACKLOG_MIN_ITEMS and week_ago_items > 0 and Decimal(grew) / week_ago_items >= BACKLOG_GROWTH
    fired = fired or (week_ago_items == 0 and grew >= BACKLOG_MIN_ITEMS)
    return {"signal": "backlog_growth", "fired": fired, "items": [],
            "detail": f"{now_items} open items now, {week_ago_items} a week ago"}  # fmt: skip


def deadline_critical(cards: list[dict]) -> dict:
    hot = [c for c in cards if c["overdue"] or c["due_soon"]]
    items = [{"agent": c["agent"], "claim": c["claim"], "deadline": c["deadline"], "overdue": c["overdue"]}
             for c in sorted(hot, key=lambda c: (c["deadline"], c["agent"]))[:10]]  # fmt: skip
    overdue = sum(c["overdue"] for c in hot)
    return {"signal": "deadline_critical", "fired": bool(hot), "items": items,
            "detail": f"{len(hot)} open items due within 7 days or overdue ({overdue} overdue)"}  # fmt: skip


def payer_slowdowns(session: Session, as_of: date) -> dict:
    end = datetime.combine(as_of, time.max)
    recent_from = as_of - timedelta(days=RECENT_PAID_DAYS)
    base_from = as_of - timedelta(days=BASELINE_PAID_DAYS + RECENT_PAID_DAYS)
    items = []
    for payer in session.scalars(select(m.Payer).order_by(m.Payer.id)):
        paid_on = timing.first_payments(session, payer.id, end)
        submitted = dict(
            session.execute(select(m.Claim.id, m.Claim.submitted_on).where(m.Claim.payer_id == payer.id)).all()
        )
        recent, base = [], []
        for cid, paid_date in paid_on.items():
            if submitted.get(cid) is None or paid_date < submitted[cid]:
                continue
            days = (paid_date - submitted[cid]).days
            if recent_from < paid_date <= as_of:
                recent.append(days)
            elif base_from < paid_date <= recent_from:
                base.append(days)
        if len(recent) >= SLOWDOWN_MIN_CLAIMS and len(base) >= SLOWDOWN_MIN_CLAIMS:
            delta = median(recent) - median(base)
            if delta >= SLOWDOWN_DAYS:
                items.append({"payer": payer.payer_id_code, "recent_median": median(recent),
                              "baseline_median": median(base), "slower_by_days": delta,
                              "recent_claims": len(recent), "baseline_claims": len(base)})  # fmt: skip
    names = ", ".join(i["payer"] for i in items)
    detail = f"slower than their own baseline: {names}" if items else "no payer is paying slower than usual"
    return {"signal": "payer_slowdown", "fired": bool(items), "items": items, "detail": detail}


def rejection_spike(session: Session, as_of: date) -> dict:
    end = datetime.combine(as_of, time.max)
    returned, files = rejection_sets(session, end)
    stmt = (
        select(m.Claim.claim_submitter_id, m.Claim.submitted_on, m.Event.gs06, m.Event.st02)
        .join(m.Event, m.Event.id == m.Claim.event_id)
        .where(m.Claim.frequency_code != "8", m.Claim.submitted_on.is_not(None), m.Event.known_at <= end)
    )
    recent_from = as_of - timedelta(days=RECENT_SUBMIT_DAYS)
    base_from = as_of - timedelta(days=RECENT_SUBMIT_DAYS + BASELINE_SUBMIT_DAYS)
    counts = {"recent": [0, 0], "baseline": [0, 0]}  # [claims, rejected]
    for sid, submitted, gs06, st02 in session.execute(stmt):
        window = None
        if recent_from < submitted <= as_of:
            window = "recent"
        elif base_from < submitted <= recent_from:
            window = "baseline"
        if window:
            counts[window][0] += 1
            counts[window][1] += 1 if (sid in returned or (gs06, st02) in files) else 0

    def rate(w: str) -> Decimal | None:
        n, r = counts[w]
        return Decimal(r) / n if n else None

    now, before = rate("recent"), rate("baseline")
    fired = (
        now is not None and before is not None and counts["recent"][0] >= REJECTION_MIN_CLAIMS
        and now - before >= REJECTION_POINTS
    )  # fmt: skip
    text = "not enough claims"
    if now is not None and before is not None:
        text = f"{now:.1%} of recent claims vs {before:.1%} before"
    return {"signal": "rejection_spike", "fired": fired, "items": [], "detail": text}
