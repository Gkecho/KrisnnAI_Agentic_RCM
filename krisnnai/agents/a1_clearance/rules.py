"""Pre-visit clearance checks as pure functions: the gaps for one appointment, and the patient estimate.

Everything is judged "as of" the checkpoint date: an eligibility answer dated after it does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from krisnnai.agents.a1_clearance import config

INACTIVE = "coverage_inactive"
COB = "cob_other_payer"
NO_CHECK = "no_eligibility_check"
STALE = "stale_check"
PRIORITY = (INACTIVE, COB, NO_CHECK, STALE)  # worst first: a lapse costs the whole visit, a stale check might not


@dataclass(frozen=True)
class Response:
    checked_on: date
    active: bool
    plan_begin: date | None
    plan_end: date | None
    other_payer: str | None
    copay: Decimal | None
    coinsurance: Decimal | None
    deductible_remaining: Decimal | None


@dataclass(frozen=True)
class Gap:
    kind: str
    detail: str


def latest(responses: list[Response], as_of: date) -> Response | None:
    known = [r for r in responses if r.checked_on <= as_of]
    return max(known, key=lambda r: r.checked_on) if known else None


def check(appt_date: date, response: Response | None, as_of: date) -> list[Gap]:
    """Gaps for one appointment as of a checkpoint date, worst first. `response` must already be the latest known."""
    if response is None or response.checked_on > as_of:
        return [Gap(NO_CHECK, "no eligibility answer on file")]
    gaps: list[Gap] = []
    if not response.active:
        gaps.append(Gap(INACTIVE, "the payer reports coverage inactive"))
    elif response.plan_end is not None and response.plan_end < appt_date:
        gaps.append(Gap(INACTIVE, f"coverage ended {response.plan_end.isoformat()}, before the visit"))
    elif response.plan_begin is not None and response.plan_begin > appt_date:
        gaps.append(Gap(INACTIVE, f"coverage starts {response.plan_begin.isoformat()}, after the visit"))
    if response.other_payer:
        gaps.append(Gap(COB, f"another payer is primary: {response.other_payer}"))
    age = (as_of - response.checked_on).days
    if age > config.STALE_DAYS:
        gaps.append(Gap(STALE, f"last checked {age} days ago"))
    gaps.sort(key=lambda g: PRIORITY.index(g.kind))
    return gaps


def estimate(
    copay: Decimal | None, coinsurance: Decimal | None, deductible_remaining: Decimal | None, allowed: Decimal
) -> Decimal:
    """What the patient owes for one service: remaining deductible first, then coinsurance on the rest, plus a copay.

    Never more than the allowed amount. Arithmetic only: the benefit lines come from the 271, the allowed amount from
    the fee schedule.
    """
    deductible = min(max(deductible_remaining or Decimal(0), Decimal(0)), allowed)
    coins = (allowed - deductible) * (coinsurance or Decimal(0))
    total = deductible + coins + (copay or Decimal(0))
    return min(total, allowed).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
