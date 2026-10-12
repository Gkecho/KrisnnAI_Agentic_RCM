"""When a payer usually pays and how likely a claim is to pay on its own, from earlier claims only (rule 9).

Everything is computed as of a date: a claim counts only if its event was known by then, and a payment only if its
remit was known by then. Defaults here are placeholders for sign-off.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import krisnai.model as m

DEFAULT_DAYS = 30  # expected days to pay when a payer has too little history; TBD at spec review
MIN_HISTORY = 5  # paid claims needed before a payer's own history is used; TBD at spec review
MATURE_DAYS = 90  # a claim this old has had time to resolve, so it counts toward "pays on its own"; TBD


def _end_of(as_of: date | datetime) -> datetime:
    return as_of if isinstance(as_of, datetime) else datetime.combine(as_of, time.max)


def first_payments(session: Session, payer_id: int, as_of: date | datetime) -> dict[int, date]:
    """claim id -> date of the first paying remit known by `as_of` (reversals and zero payments do not count)."""
    stmt = (
        select(m.Remit.claim_id, func.min(m.Payment.payment_date))
        .join(m.Payment, m.Payment.id == m.Remit.payment_id)
        .join(m.Event, m.Event.id == m.Remit.event_id)
        .join(m.Claim, m.Claim.id == m.Remit.claim_id)
        .where(
            m.Claim.payer_id == payer_id,
            m.Remit.total_paid > 0,
            m.Remit.claim_status_code != "22",
            m.Event.known_at <= _end_of(as_of),
        )
        .group_by(m.Remit.claim_id)
    )
    return {cid: paid_on for cid, paid_on in session.execute(stmt).all()}


def _known_claims(session: Session, payer_id: int, as_of: date | datetime):
    stmt = (
        select(m.Claim.id, m.Claim.submitted_on)
        .join(m.Event, m.Event.id == m.Claim.event_id)
        .where(
            m.Claim.payer_id == payer_id,
            m.Claim.frequency_code != "8",
            m.Claim.submitted_on.is_not(None),
            m.Event.known_at <= _end_of(as_of),
        )
    )
    return session.execute(stmt).all()


def expected_days(session: Session, payer_id: int, as_of: date | datetime) -> tuple[int, str]:
    """(days from submission to first payment, basis). The payer's median once it has MIN_HISTORY paid claims."""
    paid = first_payments(session, payer_id, as_of)
    days = [(paid[cid] - sub).days for cid, sub in _known_claims(session, payer_id, as_of) if cid in paid]
    days = [d for d in days if d >= 0]
    if len(days) >= MIN_HISTORY:
        return int(median(days)), f"history n={len(days)}"
    return DEFAULT_DAYS, f"default (history n={len(days)})"


def paid_on_their_own(session: Session, payer_id: int, as_of: date | datetime) -> tuple[int, int]:
    """(paid, n) over this payer's claims old enough to have resolved: how many got paid by `as_of`."""
    cutoff = _end_of(as_of).date().toordinal() - MATURE_DAYS
    paid = first_payments(session, payer_id, as_of)
    mature = [cid for cid, sub in _known_claims(session, payer_id, as_of) if sub.toordinal() <= cutoff]
    return sum(1 for cid in mature if cid in paid), len(mature)


def p_paid(paid: int, n: int) -> Decimal:
    """Beta(1, 1) smoothing: (paid + 1) / (n + 2), so a payer with no history starts at one half."""
    return (Decimal(paid) + 1) / (Decimal(n) + 2)
