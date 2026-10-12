"""Cash forecast with prediction intervals, and a backtest that measures how good it was.

A transparent method, not a fitted model. For a claim still open at `as_of` with age `a` days, let q be the payer's
smoothed share of mature, unrejected claims that ever get paid and F the payer's days-to-pay curve (among paid
mature claims).
Then the chance it is paid in the week ending a + 7k, given it is unpaid today, is
q * (F(a + 7k) - F(a + 7k - 7)) / (1 - q * F(a)). A claim already older than anything the payer has paid is forecast
near zero, which is how stuck claims stop inflating the forecast. A payer with too little history gets a flat ramp over
60 days, flagged as default. The amount is the A15 expected payer payment. The interval adds the variance of independent
pay / do-not-pay outcomes, 80% two-sided. Everything uses only data known by `as_of` (rule 9).
"""

from __future__ import annotations

from bisect import bisect_right
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a7_ar import timing
from krisnai.agents.a15_lite.expected import money
from krisnai.agents.a15_lite.pricing import ClaimPricer
from krisnai.agents.rejections import rejection_sets
from krisnai.model import tenant_session

HORIZON_DAYS = 28
WEEKS = HORIZON_DAYS // 7
Z80 = Decimal("1.2816")  # two-sided 80% normal interval; TBD at spec review
ZERO = Decimal(0)
DEFAULT_RAMP_DAYS = 60  # payers with too little history: paid evenly over this many days; TBD at spec review


def _end(as_of: date) -> datetime:
    return datetime.combine(as_of, time.max)


def open_claim_rows(session: Session, as_of: date) -> list[tuple[m.Claim, str]]:
    """(claim, payer code) for claims known by `as_of` with no remit yet and not rejected by the 999 / 277CA."""
    end = _end(as_of)
    answered = set(
        session.scalars(
            select(m.Remit.claim_submitter_id)
            .join(m.Event, m.Event.id == m.Remit.event_id)
            .where(m.Event.known_at <= end)
        )
    )
    returned, rejected_files = rejection_sets(session, end)
    stmt = (
        select(m.Claim, m.Payer.payer_id_code, m.Event.gs06, m.Event.st02)
        .join(m.Event, m.Event.id == m.Claim.event_id)
        .join(m.Payer, m.Payer.id == m.Claim.payer_id)
        .where(m.Claim.frequency_code != "8", m.Claim.submitted_on.is_not(None), m.Event.known_at <= end)
        .order_by(m.Claim.id)
    )
    return [
        (claim, payer)
        for claim, payer, gs06, st02 in session.execute(stmt)
        if claim.claim_submitter_id not in answered
        and claim.claim_submitter_id not in returned
        and (gs06, st02) not in rejected_files
    ]


def _cdf(days: list[int], x: int) -> Decimal:
    """Share of the payer's paid claims that were paid within x days of submission (flat ramp when history is thin)."""
    if len(days) < timing.MIN_HISTORY:
        return Decimal(max(0, min(x, DEFAULT_RAMP_DAYS))) / DEFAULT_RAMP_DAYS
    return Decimal(bisect_right(days, x)) / len(days)


def weekly_chances(days: list[int], q: Decimal, age: int) -> list[Decimal]:
    """Chance a claim of this age, unpaid today, is paid in each of the next WEEKS weeks, then later."""
    unpaid = 1 - q * _cdf(days, age)
    chances = [q * (_cdf(days, age + 7 * k) - _cdf(days, age + 7 * (k - 1))) / unpaid for k in range(1, WEEKS + 1)]
    chances.append(q * (1 - _cdf(days, age + 7 * WEEKS)) / unpaid)
    return chances


def eventually_paid(session: Session, payer_id: int, end: datetime, returned: set[str], files: set) -> tuple[int, int]:
    """(paid, n) over this payer's mature claims that were not rejected: the same population the forecast covers."""
    cutoff = end.date() - timedelta(days=timing.MATURE_DAYS)
    paid = timing.first_payments(session, payer_id, end)
    stmt = (
        select(m.Claim.id, m.Claim.claim_submitter_id, m.Event.gs06, m.Event.st02)
        .join(m.Event, m.Event.id == m.Claim.event_id)
        .where(
            m.Claim.payer_id == payer_id, m.Claim.frequency_code != "8", m.Claim.submitted_on.is_not(None),
            m.Claim.submitted_on <= cutoff, m.Event.known_at <= end,
        )
    )  # fmt: skip
    mature = [
        cid for cid, sid, gs06, st02 in session.execute(stmt) if sid not in returned and (gs06, st02) not in files
    ]
    return sum(1 for cid in mature if cid in paid), len(mature)


def forecast(session: Session, as_of: date, pricer: ClaimPricer | None = None) -> dict:
    pricer = pricer or ClaimPricer()
    end = _end(as_of)
    rows = open_claim_rows(session, as_of)
    lines: dict[int, list[m.ClaimLine]] = {}
    ids = [c.id for c, _ in rows]
    if ids:
        for ln in session.scalars(select(m.ClaimLine).where(m.ClaimLine.claim_id.in_(ids))):
            lines.setdefault(ln.claim_id, []).append(ln)
    returned, files = rejection_sets(session, end)
    payer_stats: dict[int, tuple[list[int], Decimal]] = {}
    buckets = {k: {"expected": ZERO, "var": ZERO, "claims": 0} for k in range(1, WEEKS + 2)}  # WEEKS + 1 = later
    total28 = {"expected": ZERO, "var": ZERO, "claims": 0}
    sids = []
    for claim, payer_code in rows:
        if claim.payer_id not in payer_stats:
            paid, n = eventually_paid(session, claim.payer_id, end, returned, files)
            curve = timing.payment_days(session, claim.payer_id, end, True)
            payer_stats[claim.payer_id] = (curve, timing.p_paid(paid, n))
        days, q = payer_stats[claim.payer_id]
        amount, _ = pricer.price(
            session, as_of, payer_code, lines.get(claim.id, []), claim.service_date, claim.total_charge
        )
        chances = weekly_chances(days, q, (as_of - claim.submitted_on).days)
        for k, p in enumerate(chances, start=1):
            buckets[k]["expected"] += amount * p
            buckets[k]["var"] += amount * amount * p * (1 - p)
            buckets[k]["claims"] += 1 if p >= Decimal("0.05") else 0
        p28 = sum(chances[:WEEKS], ZERO)
        total28["expected"] += amount * p28
        total28["var"] += amount * amount * p28 * (1 - p28)
        total28["claims"] += 1 if p28 >= Decimal("0.05") else 0
        sids.append(claim.claim_submitter_id)

    def interval(expected: Decimal, var: Decimal) -> dict:
        sd = var.sqrt() if var > 0 else ZERO
        return {"expected": money(expected), "low": money(max(ZERO, expected - Z80 * sd)),
                "high": money(expected + Z80 * sd)}  # fmt: skip

    weeks = []
    for k in range(1, WEEKS + 1):
        b = buckets[k]
        start = as_of + timedelta(days=7 * (k - 1) + 1)
        weeks.append({"week": k, "from": start.isoformat(), "to": (start + timedelta(days=6)).isoformat(),
                      "claims": b["claims"], **interval(b["expected"], b["var"])})  # fmt: skip
    later = buckets[WEEKS + 1]
    return {
        "as_of": as_of.isoformat(), "claims_open": len(rows), "weeks": weeks,
        "next_28_days": {"claims": total28["claims"], **interval(total28["expected"], total28["var"])},
        "later": {"claims": later["claims"], "expected": money(later["expected"])},
        "method": "payer days-to-pay curve x A15 expected payment x smoothed chance of payment; 80% interval",
        "sids": sids,
    }  # fmt: skip


def actual_cash(session: Session, sids: list[str], start: date, end: date) -> Decimal:
    """Payments received in (start, end] on these claims, counting only remits known by `end`."""
    if not sids:
        return ZERO
    total = ZERO
    stmt = (
        select(m.Remit.total_paid)
        .join(m.Payment, m.Payment.id == m.Remit.payment_id)
        .join(m.Event, m.Event.id == m.Remit.event_id)
        .where(
            m.Remit.claim_submitter_id.in_(sids),
            m.Remit.claim_status_code != "22",
            m.Payment.payment_date > start,
            m.Payment.payment_date <= end,
            m.Event.known_at <= _end(end),
        )
    )
    for paid in session.scalars(stmt):
        total += paid
    return total


def backtest(engine: Engine, tenant_id: int, dates: list[date]) -> dict:
    """Forecast on each past date, then compare the next 28 days with what was actually paid on those claims."""
    pricer = ClaimPricer()
    rows = []
    with tenant_session(engine, tenant_id) as s:
        for d in dates:
            f = forecast(s, d, pricer)
            if not f["claims_open"]:
                continue
            end = d + timedelta(days=HORIZON_DAYS)
            actual = actual_cash(s, f["sids"], d, end)
            n = f["next_28_days"]
            inside = n["low"] <= actual <= n["high"]
            rows.append({"as_of": d.isoformat(), "claims": n["claims"], "forecast": n["expected"], "low": n["low"],
                         "high": n["high"], "actual": money(actual), "inside": inside})  # fmt: skip
    total_actual = sum((r["actual"] for r in rows), ZERO)
    error = sum((abs(r["forecast"] - r["actual"]) for r in rows), ZERO)
    return {
        "dates": len(rows), "rows": rows,
        "wape": (error / total_actual).quantize(Decimal("0.0001")) if total_actual else None,
        "coverage": (Decimal(sum(r["inside"] for r in rows)) / len(rows)).quantize(Decimal("0.01")) if rows else None,
    }  # fmt: skip
