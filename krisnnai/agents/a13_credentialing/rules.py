"""Credentialing checks as pure functions: one provider + payer enrollment, and one provider's screening, as of a date.

Everything is judged "as of" the check date: a status or screening dated after it does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from krisnnai.agents.a13_credentialing import config

BILLING_WITHOUT = "billing_without_enrollment"
EXPIRED = "enrollment_expired"
EXPIRING = "expiring_soon"
PENDING_LONG = "pending_too_long"
EXCLUDED = "excluded_provider"
STALE_SCREEN = "screening_stale"
PRIORITY = (EXCLUDED, BILLING_WITHOUT, EXPIRED, EXPIRING, PENDING_LONG, STALE_SCREEN)


@dataclass(frozen=True)
class Enroll:
    status: str
    submitted_on: date | None
    effective_on: date | None
    expires_on: date | None
    status_on: date


@dataclass(frozen=True)
class Service:
    when: date
    amount: Decimal  # expected payer payment of the service; zero when not priced


@dataclass(frozen=True)
class Gap:
    kind: str
    amount: Decimal
    detail: str


def latest_known(rows: list[Enroll], as_of: date) -> Enroll | None:
    known = [r for r in rows if r.status_on <= as_of]
    return max(known, key=lambda r: r.status_on) if known else None


def check_enrollment(enroll: Enroll | None, services: list[Service], as_of: date) -> list[Gap]:
    """Gaps for one provider + payer, worst first. `enroll` must be the latest status known by `as_of`."""
    recent = [s for s in services if as_of - timedelta(days=config.SERVICE_WINDOW_DAYS) < s.when <= as_of]
    gaps: list[Gap] = []
    if enroll is None or enroll.status in ("denied", "terminated"):
        since = [s for s in recent if enroll is None or s.when > enroll.status_on]  # only work after the refusal
        if since:
            why = "no enrollment on file" if enroll is None else f"enrollment {enroll.status} {enroll.status_on}"
            days = config.SERVICE_WINDOW_DAYS
            gaps.append(Gap(BILLING_WITHOUT, sum((s.amount for s in since), Decimal(0)),
                            f"{len(since)} service(s) in the last {days} days, {why}"))  # fmt: skip
        return gaps
    expiry = enroll.expires_on or (enroll.status_on if enroll.status == "expired" else None)
    if expiry is not None and expiry < as_of and enroll.status in ("active", "expired"):
        after = [s for s in recent if s.when > expiry]
        if after:
            gaps.append(Gap(EXPIRED, sum((s.amount for s in after), Decimal(0)),
                            f"expired {expiry.isoformat()}, {len(after)} service(s) since"))  # fmt: skip
        return gaps
    if enroll.status == "active" and expiry is not None:
        days = (expiry - as_of).days
        if 0 <= days <= config.EXPIRY_WARN_DAYS:
            gaps.append(Gap(EXPIRING, Decimal(0), f"expires in {days} days ({expiry.isoformat()})"))
    if enroll.status == "pending" and enroll.submitted_on is not None:
        waiting = (as_of - enroll.submitted_on).days
        if waiting >= config.PENDING_DAYS:
            gaps.append(Gap(PENDING_LONG, Decimal(0), f"application pending {waiting} days"))
    return gaps


def check_screening(result: str | None, screened_on: date | None, as_of: date) -> list[Gap]:
    if result == "excluded":
        return [Gap(EXCLUDED, Decimal(0), f"screening on {screened_on} returned excluded")]
    if screened_on is None:
        return [Gap(STALE_SCREEN, Decimal(0), "no screening on file")]
    age = (as_of - screened_on).days
    if age > config.SCREENING_STALE_DAYS:
        return [Gap(STALE_SCREEN, Decimal(0), f"last screened {age} days ago")]
    return []
