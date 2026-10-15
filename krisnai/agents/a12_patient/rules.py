"""Patient balance checks as pure functions: one claim's patient share, its statements and payments, as of a date.

Everything is judged "as of" the check date: a payment or status dated after it does not exist yet. Order matters and is
the order a person would read the account: a dispute stops everything, a credit is a credit, a small balance is a staff
decision, and only then does a missing statement or an aging balance count.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from krisnai.agents.a12_patient import config

DISPUTE_HOLD = "dispute_hold"
CREDIT = "credit_balance"
SMALL = "small_balance"
NO_STATEMENT = "no_statement"
AGING = "balance_aging"
PRIORITY = (DISPUTE_HOLD, CREDIT, SMALL, NO_STATEMENT, AGING)
HOLD_STATUSES = ("disputed", "hardship")


@dataclass(frozen=True)
class Statement:
    sent_on: date
    status: str  # sent | disputed | plan | hardship | returned


@dataclass(frozen=True)
class Payment:
    paid_on: date
    amount: Decimal


@dataclass(frozen=True)
class Gap:
    kind: str
    amount: Decimal
    stage: int | None
    detail: str


def stage_for(age: int) -> int:
    return next((s for s in config.STAGES if age >= s), config.AGING_FROM_DAYS)


def check(
    owed: Decimal, confirmed_on: date, statements: list[Statement], payments: list[Payment], as_of: date
) -> list[Gap]:
    """The one gap (or none) a person would raise for this claim's patient share as of a date."""
    if owed <= 0 or confirmed_on > as_of:
        return []
    paid = sum((p.amount for p in payments if p.paid_on <= as_of), Decimal(0))
    open_ = owed - paid
    known = [s for s in statements if s.sent_on <= as_of]
    age = (as_of - confirmed_on).days

    if open_ > 0 and any(s.status in HOLD_STATUSES for s in known):
        return [Gap(DISPUTE_HOLD, open_, None, "the account is disputed or in hardship: outreach is on hold")]
    if open_ < 0:
        return [Gap(CREDIT, -open_, None, f"paid {-open_} more than the patient share")]
    if open_ == 0:
        return []
    if any(s.status == "plan" for s in known):
        return []  # a payment plan is in place: the balance is being worked down
    if open_ < config.SMALL_BALANCE:
        return [Gap(SMALL, open_, None, f"{open_} open, under the small-balance line")]
    sent = [s for s in known if s.status == "sent"]
    if not sent:
        if age >= config.STATEMENT_DUE_DAYS:
            return [Gap(NO_STATEMENT, open_, None, f"patient share confirmed {age} days ago, no statement sent")]
        return []
    if age >= config.AGING_FROM_DAYS:
        stage = stage_for(age)
        return [Gap(AGING, open_, stage, f"{open_} open, {age} days since the share was confirmed (stage {stage})")]
    return []
