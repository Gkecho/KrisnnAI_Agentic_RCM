"""Patient payment and statement feed for the simulated book, with planted outcomes and an answer key.

Synthea has no patient billing data, so it is simulated from the patient share (835 CLP05) of each paid claim. A claim
the practice has known for 45 or more days gets one planted outcome; younger claims are paid in full inside 25 days so
nothing is open that a check could not yet call late. A statement goes out 3 to 10 days after the remit (3 to 6 for
the younger claims).

    paid_full       paid in full 10 to 40 days after the remit
    partial         30 to 60% paid, the rest open
    aging_unpaid    nothing paid
    no_statement    no statement ever sent
    disputed        a disputed status row 15 to 30 days after the remit, nothing paid
    credit_balance  paid 5 to 25 more than owed

The answer key mirrors what a person reading the account would call it: an open balance under 10.00 is a small balance
whatever else is true, a dispute stops everything else, and a credit is a credit. The simulator keeps its own
constants, apart from the agent's configuration.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from krisnai.synthea.types import SimClaim, money

BANDS = (("paid_full", 0.60), ("partial", 0.70), ("aging_unpaid", 0.85), ("no_statement", 0.90),
         ("disputed", 0.94), ("credit_balance", 1.0))  # fmt: skip
MIN_AGE_DAYS = 45
SMALL = Decimal("10.00")
PAYMENT_COLUMNS = ["payment_id", "claim_id", "paid_on", "amount", "method"]
STATEMENT_COLUMNS = ["statement_id", "claim_id", "sent_on", "channel", "status"]
TRUTH_COLUMNS = ["key", "defect", "amount", "detail"]


@dataclass
class PatientPlan:
    payments: list[dict] = field(default_factory=list)
    statements: list[dict] = field(default_factory=list)
    truth: list[dict] = field(default_factory=list)


def stage_of(age: int) -> int:
    return 90 if age >= 90 else 60 if age >= 60 else 30


def plan_patient(claims: list[SimClaim], as_of: date, seed: int) -> PatientPlan:
    rng = random.Random(seed + 79)
    plan = PatientPlan()
    n_pay = n_st = 0

    def statement(claim, on, status="sent", channel="mail"):
        nonlocal n_st
        n_st += 1
        plan.statements.append({"statement_id": f"SYNST{n_st:06d}", "claim_id": claim.claim_id,
                                "sent_on": on.isoformat(), "channel": channel, "status": status})  # fmt: skip

    def payment(claim, on, amount):
        nonlocal n_pay
        n_pay += 1
        plan.payments.append({
            "payment_id": f"SYNPP{n_pay:06d}", "claim_id": claim.claim_id, "paid_on": on.isoformat(),
            "amount": f"{amount:.2f}", "method": rng.choice(["CARD", "CHECK", "ONLINE"]),
        })  # fmt: skip

    def note(claim, defect, amount, detail=""):
        plan.truth.append({"key": claim.claim_id, "defect": defect, "amount": f"{amount:.2f}", "detail": detail})

    for c in claims:
        owed = c.pr
        if not (c.has_remit and c.remit_date is not None and c.remit_date <= as_of and c.paid > 0 and owed > 0):
            continue
        age = (as_of - c.remit_date).days
        planted = age >= MIN_AGE_DAYS
        draw = rng.random()
        kind = next(n for n, upper in BANDS if draw < upper) if planted else "paid_full"
        sent = c.remit_date + timedelta(days=rng.randint(3, 10) if planted else rng.randint(3, 6))
        if kind != "no_statement":
            statement(c, sent)
        paid = Decimal(0)
        if kind == "paid_full":
            paid = owed
            pay_on = c.remit_date + timedelta(days=rng.randint(10, 40) if planted else rng.randint(10, 25))
            payment(c, pay_on, paid)
            if pay_on > as_of:  # a younger claim whose payment has not arrived yet: still open today
                paid = Decimal(0)
        elif kind == "partial":
            paid = money(owed * Decimal(rng.randint(30, 60)) / 100)
            payment(c, c.remit_date + timedelta(days=rng.randint(10, 30)), paid)
        elif kind == "credit_balance":
            paid = owed + Decimal(rng.randint(500, 2500)) / 100
            payment(c, c.remit_date + timedelta(days=rng.randint(10, 30)), paid)
        elif kind == "disputed":
            statement(c, c.remit_date + timedelta(days=rng.randint(15, 30)), status="disputed", channel="none")
        if not planted:
            if 0 < owed - paid < SMALL:  # too young for anything else, but a small open balance is a small balance
                note(c, "small_balance", owed - paid)
            continue
        # what a person reading the account would call it, in the agent's priority order
        open_ = owed - paid  # every planted payment date is before as_of, so it is known
        if kind == "disputed" and open_ > 0:
            note(c, "dispute_hold", open_)
        elif open_ < 0:
            note(c, "credit_balance", -open_)
        elif 0 < open_ < SMALL:
            note(c, "small_balance", open_)
        elif open_ > 0 and kind == "no_statement":
            note(c, "no_statement", open_)
        elif open_ > 0 and age >= 30:
            note(c, "balance_aging", open_, str(stage_of(age)))
    return plan
