"""Bank deposit and PM posting feed for the simulated book, with planted defects and an answer key.

Synthea has no bank or posting data, so they are simulated from the 835 payments the book already contains. One payment
is one payer on one remit date (the trace the 835 writer assigns). Each payment gets a deposit a few days later and each
paid claim a posting a day or two after, with planted defects:

    missing_deposit   no deposit at all
    deposit_variance  deposited short by a bank fee (the line still carries the trace)
    duplicate_deposit the same deposit twice
    late_deposit      deposited 8 to 12 days after the payment date
    unidentified_deposit  an extra deposit with no payment behind it
    not_posted        a paid claim never posted
    partial_posting   posted for less than was paid
    late_posting      posted 8 to 12 days after the payment date

Defects go only on payments old enough for a check at `as_of` to know about them. The simulator keeps its own constants,
apart from the agent's configuration.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from krisnnai.synthea.types import SimClaim, money

PAYMENT_BANDS = (  # cumulative bands of one draw per payment
    ("missing_deposit", 0.03), ("deposit_variance", 0.06), ("duplicate_deposit", 0.08), ("late_deposit", 0.13),
)  # fmt: skip
POSTING_BANDS = (("not_posted", 0.04), ("partial_posting", 0.07), ("late_posting", 0.13))
UNIDENTIFIED_SHARE = 0.02
UNTRACED_SHARE = 0.20  # normal deposits that arrive without a trace number (matched on payer + amount)
MIN_AGE_DAYS = 14  # a defect is planted only on a payment at least this old at as_of
DEPOSIT_COLUMNS = ["deposit_id", "deposit_date", "amount", "payer_id", "trace", "method"]
POSTING_COLUMNS = ["posting_id", "payment_trace", "claim_id", "posted_on", "posted_amount", "posted_by_role"]
TRUTH_COLUMNS = ["key", "defect", "payment_trace", "claim_id", "amount"]


@dataclass
class CashPlan:
    deposits: list[dict] = field(default_factory=list)
    postings: list[dict] = field(default_factory=list)
    truth: list[dict] = field(default_factory=list)


def _band(draw: float, bands) -> str:
    for name, upper in bands:
        if draw < upper:
            return name
    return ""


def trace_of(claim: SimClaim) -> str:
    """The TRN02 the 835 writer gives this claim's payment: payer suffix + remit date."""
    return f"TRC{claim.payer.payer_id[-4:]}{claim.remit_date:%Y%m%d}"


def plan_cash(claims: list[SimClaim], as_of: date, seed: int) -> CashPlan:
    rng = random.Random(seed + 67)
    plan = CashPlan()
    groups: dict[tuple[str, date], list[SimClaim]] = {}
    for c in claims:
        if c.has_remit and c.remit_date is not None and c.remit_date <= as_of:
            groups.setdefault((c.payer.payer_id, c.remit_date), []).append(c)
    n_dep = 0

    def deposit(payer_id, when, amount, trace, method="ACH"):
        nonlocal n_dep
        n_dep += 1
        plan.deposits.append({"deposit_id": f"SYNBK{n_dep:06d}", "deposit_date": when.isoformat(),
                              "amount": f"{amount:.2f}", "payer_id": payer_id, "trace": trace or "",
                              "method": method})  # fmt: skip
        return f"SYNBK{n_dep:06d}"

    for (payer_id, paid_on), items in sorted(groups.items()):
        amount = sum((c.paid for c in items), Decimal(0))
        if amount <= 0:
            continue  # a zero-dollar remittance has no cash
        trace = trace_of(items[0])
        old_enough = (as_of - paid_on).days >= MIN_AGE_DAYS
        kind = _band(rng.random(), PAYMENT_BANDS) if old_enough else ""
        lag = rng.randint(1, 3)
        if kind == "late_deposit":
            lag = rng.randint(8, 12)
        when = paid_on + timedelta(days=lag)
        traced = rng.random() >= UNTRACED_SHARE or kind in ("deposit_variance", "duplicate_deposit")
        if kind == "missing_deposit":
            plan.truth.append({"key": trace, "defect": kind, "payment_trace": trace, "claim_id": "",
                               "amount": f"{amount:.2f}"})  # fmt: skip
        else:
            dep_amount = amount
            if kind == "deposit_variance":
                fee = money(Decimal(rng.randint(200, 1500)) / 100)
                dep_amount = amount - min(fee, amount - Decimal("0.01"))
                plan.truth.append({"key": trace, "defect": kind, "payment_trace": trace, "claim_id": "",
                                   "amount": f"{amount - dep_amount:.2f}"})  # fmt: skip
            deposit(payer_id, when, dep_amount, trace if traced else "")
            if kind == "duplicate_deposit":
                deposit(payer_id, when, dep_amount, trace)
                plan.truth.append({"key": trace, "defect": kind, "payment_trace": trace, "claim_id": "",
                                   "amount": f"{dep_amount:.2f}"})  # fmt: skip
            if kind == "late_deposit":
                plan.truth.append({"key": trace, "defect": kind, "payment_trace": trace, "claim_id": "",
                                   "amount": f"{lag}"})  # fmt: skip

        for c in items:
            if c.paid <= 0:
                continue
            pk = _band(rng.random(), POSTING_BANDS) if old_enough else ""
            ref = f"SYNPO{c.claim_id[-6:]}"
            posted, post_lag = c.paid, rng.randint(0, 2)
            if pk == "not_posted":
                plan.truth.append({"key": f"{trace}|{c.claim_id}", "defect": pk, "payment_trace": trace,
                                   "claim_id": c.claim_id, "amount": f"{c.paid:.2f}"})  # fmt: skip
                continue
            if pk == "partial_posting":
                posted = c.paid - min(max(money(c.paid * Decimal("0.2")), Decimal("1.00")), c.paid - Decimal("0.01"))
                plan.truth.append({"key": f"{trace}|{c.claim_id}", "defect": pk, "payment_trace": trace,
                                   "claim_id": c.claim_id, "amount": f"{c.paid - posted:.2f}"})  # fmt: skip
            if pk == "late_posting":
                post_lag = rng.randint(8, 12)
                plan.truth.append({"key": f"{trace}|{c.claim_id}", "defect": pk, "payment_trace": trace,
                                   "claim_id": c.claim_id, "amount": f"{post_lag}"})  # fmt: skip
            plan.postings.append({"posting_id": ref, "payment_trace": trace, "claim_id": c.claim_id,
                                  "posted_on": (paid_on + timedelta(days=post_lag)).isoformat(),
                                  "posted_amount": f"{posted:.2f}", "posted_by_role": "payment_poster"})  # fmt: skip

    # deposits no payment explains: a few random amounts on random days inside the book
    days = sorted({d for _, d in groups})
    payers = sorted({p for p, _ in groups})
    for _ in range(max(1, int(len(groups) * UNIDENTIFIED_SHARE)) if groups else 0):
        when = rng.choice(days)
        if (as_of - when).days < MIN_AGE_DAYS:
            continue
        amount = money(Decimal(rng.randint(5000, 60000)) / 100) + Decimal("0.07")  # never equals a payment by chance
        ref = deposit(rng.choice(payers), when + timedelta(days=rng.randint(1, 3)), amount, "")
        plan.truth.append({"key": ref, "defect": "unidentified_deposit", "payment_trace": "", "claim_id": "",
                           "amount": f"{amount:.2f}"})  # fmt: skip
    return plan
