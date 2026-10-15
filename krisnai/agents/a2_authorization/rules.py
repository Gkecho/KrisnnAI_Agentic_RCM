"""Authorization checks as pure functions: the gaps for one appointment on one checkpoint day.

Everything is judged "as of" the checkpoint: a request, decision or unit count dated after it does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from krisnai.agents.a2_authorization import config

NO_AUTH = "no_authorization"
DENIED = "authorization_denied"
EXPIRED = "expired_authorization"
UNITS = "units_exhausted"
PENDING_LATE = "pending_late"
PRIORITY = (DENIED, EXPIRED, UNITS, NO_AUTH, PENDING_LATE)  # a refusal or a lapse first; a missing request next


@dataclass(frozen=True)
class Auth:
    status: str  # requested | approved | denied | expired
    requested_on: date
    decided_on: date | None
    start_date: date | None
    end_date: date | None
    units_approved: int | None
    units_used: int | None
    units_as_of: date | None


@dataclass(frozen=True)
class Gap:
    kind: str
    detail: str


def pick(auths: list[Auth], appt_date: date, as_of: date) -> Auth | None:
    """The request that applies to the visit: one whose window holds the date, else the latest request known."""
    known = [a for a in auths if a.requested_on <= as_of]
    covering = [
        a for a in known
        if a.start_date is not None and a.start_date <= appt_date and (a.end_date is None or a.end_date >= appt_date)
    ]  # fmt: skip
    pool = covering or known
    return max(pool, key=lambda a: a.requested_on) if pool else None


def check(appt_date: date, required: bool, auth: Auth | None, as_of: date) -> list[Gap]:
    if not required:
        return []
    if auth is None or auth.requested_on > as_of:
        return [Gap(NO_AUTH, "this service needs prior authorization and none has been requested")]
    decided = auth.decided_on is not None and auth.decided_on <= as_of
    if not decided:  # still pending as of the checkpoint
        waiting = (as_of - auth.requested_on).days
        if waiting >= config.PENDING_DAYS and (appt_date - as_of).days <= config.PENDING_WINDOW_DAYS:
            return [Gap(PENDING_LATE, f"requested {waiting} days ago and not decided, visit in "
                                      f"{(appt_date - as_of).days} days")]  # fmt: skip
        return []
    if auth.status == "denied":
        return [Gap(DENIED, "the payer denied the authorization")]
    gaps: list[Gap] = []
    if auth.end_date is not None and auth.end_date < appt_date:
        gaps.append(Gap(EXPIRED, f"approved window ended {auth.end_date.isoformat()}, before the visit"))
    elif auth.start_date is not None and auth.start_date > appt_date:
        gaps.append(Gap(EXPIRED, f"approved window starts {auth.start_date.isoformat()}, after the visit"))
    if (
        auth.units_approved is not None and auth.units_used is not None
        and auth.units_as_of is not None and auth.units_as_of <= as_of and auth.units_used >= auth.units_approved
    ):
        gaps.append(Gap(UNITS, f"{auth.units_used} of {auth.units_approved} units already used"))
    gaps.sort(key=lambda g: PRIORITY.index(g.kind))
    return gaps
