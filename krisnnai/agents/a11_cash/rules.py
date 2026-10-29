"""Cash reconciliation as pure functions: one payer payment against the bank and the PM, as of a date.

Everything is judged "as of" the check date: a deposit or posting dated after it does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from krisnnai.agents.a11_cash import config

DEPOSIT_MISSING = "deposit_missing"
DEPOSIT_VARIANCE = "deposit_variance"
DUPLICATE_DEPOSIT = "duplicate_deposit"
NOT_POSTED = "not_posted"
PARTIAL_POSTING = "partial_posting"
DEPOSIT_LATE = "deposit_late"  # informational: feeds the days-to-deposit KPI
POSTING_LATE = "posting_late"  # informational: feeds the days-to-post KPI
PRIORITY = (DEPOSIT_MISSING, DUPLICATE_DEPOSIT, DEPOSIT_VARIANCE, NOT_POSTED, PARTIAL_POSTING)
INFORMATIONAL = (DEPOSIT_LATE, POSTING_LATE)


@dataclass(frozen=True)
class Payment:
    trace: str
    payer: str
    amount: Decimal
    paid_on: date


@dataclass(frozen=True)
class Deposit:
    ref: str
    deposited_on: date
    amount: Decimal
    payer: str | None
    trace: str | None


@dataclass(frozen=True)
class Posting:
    claim: str
    posted_on: date
    amount: Decimal


@dataclass(frozen=True)
class Gap:
    kind: str
    amount: Decimal
    detail: str

    @property
    def actionable(self) -> bool:
        return self.kind not in INFORMATIONAL


def match_deposits(
    payment: Payment, deposits: list[Deposit], as_of: date, rivals: tuple[Payment, ...] = ()
) -> list[Deposit]:
    """Deposits known by `as_of` that belong to this payment.

    By trace when the bank sent it. Otherwise by payer + amount inside the window, one deposit to one payment: payments
    with the same payer and amount (`rivals`, which the bank file cannot tell apart) take the untraced deposits in date
    order, so two equal payments are not both credited with the same two deposits.
    """
    known = [d for d in deposits if d.deposited_on <= as_of]
    by_trace = [d for d in known if d.trace == payment.trace and (d.payer in (None, payment.payer))]
    if by_trace:
        return by_trace
    pool = sorted(
        (d for d in known if d.trace is None and d.payer in (None, payment.payer) and d.amount == payment.amount),
        key=lambda d: (d.deposited_on, d.ref),
    )
    order = sorted([payment, *(p for p in rivals if p.paid_on <= as_of)], key=lambda p: (p.paid_on, p.trace))
    used: set[str] = set()
    for p in order:
        window = config.MATCH_WINDOW_DAYS
        pick = next((d for d in pool if d.ref not in used and 0 <= (d.deposited_on - p.paid_on).days <= window), None)
        if pick is not None:
            used.add(pick.ref)
        if p.trace == payment.trace:
            return [pick] if pick is not None else []
    return []


def reconcile(
    payment: Payment,
    claims_paid: dict[str, Decimal],
    deposits: list[Deposit],
    postings: list[Posting],
    as_of: date,
    rivals: tuple[Payment, ...] = (),
) -> list[Gap]:
    """Gaps for one payment: actionable ones first in PRIORITY order, then the informational ones."""
    if payment.amount <= 0:
        return []  # a zero-dollar remittance has no cash to reconcile
    gaps: list[Gap] = []
    age = (as_of - payment.paid_on).days
    matched = match_deposits(payment, deposits, as_of, rivals)

    if not matched:
        if age >= config.DEPOSIT_DUE_DAYS:
            gaps.append(Gap(DEPOSIT_MISSING, payment.amount, f"no deposit {age} days after the payment date"))
    else:
        first = min(matched, key=lambda d: d.deposited_on)
        if len(matched) > 1:
            extra = sum((d.amount for d in matched), Decimal(0)) - payment.amount
            gaps.append(Gap(DUPLICATE_DEPOSIT, extra, f"{len(matched)} deposits for one payment"))
        else:
            diff = payment.amount - first.amount
            if abs(diff) > config.TOLERANCE:
                gaps.append(Gap(DEPOSIT_VARIANCE, diff, f"deposited {first.amount}, payment {payment.amount}"))
        lag = (first.deposited_on - payment.paid_on).days
        if lag > config.DEPOSIT_LATE_DAYS:
            gaps.append(Gap(DEPOSIT_LATE, Decimal(lag), f"deposited {lag} days after the payment date"))

    posted: dict[str, list[Posting]] = {}
    for p in postings:
        if p.posted_on <= as_of:
            posted.setdefault(p.claim, []).append(p)
    if age >= config.POST_DUE_DAYS:
        for claim, paid in sorted(claims_paid.items()):
            if paid <= 0:
                continue
            rows = posted.get(claim, [])
            if not rows:
                gaps.append(Gap(NOT_POSTED, paid, f"claim {claim}: {paid} not posted {age} days after payment"))
                continue
            total = sum((p.amount for p in rows), Decimal(0))
            if total < paid:
                gaps.append(Gap(PARTIAL_POSTING, paid - total, f"claim {claim}: posted {total} of {paid}"))
            lag = (min(p.posted_on for p in rows) - payment.paid_on).days
            if lag > config.POST_LATE_DAYS:
                gaps.append(Gap(POSTING_LATE, Decimal(lag), f"claim {claim}: posted {lag} days after payment"))
    order = {k: i for i, k in enumerate(PRIORITY + INFORMATIONAL)}
    gaps.sort(key=lambda g: (order.get(g.kind, 99), g.detail))
    return gaps
