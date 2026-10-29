"""Historical win rate for a payer + CARC, point in time: only outcomes known when the decision is made."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m


def outcomes(session: Session, payer_id: int, carc: str, as_of: datetime) -> tuple[int, int]:
    """(wins, n) over earlier denials of this payer with this CARC.

    A denial counts if its event was known strictly before `as_of`. It is a win if the same claim has a paid remit
    known on or before `as_of`. Anything that happened after `as_of` is invisible here (rule 9).
    """
    known = {e.id: e.known_at for e in session.scalars(select(m.Event).where(m.Event.known_at <= as_of))}
    payer_of = {p.id: p.payer_id for p in session.scalars(select(m.Payment))}
    paid_claims: set[int] = set()
    denied: list[m.Remit] = []
    for r in session.scalars(select(m.Remit)):
        if r.event_id not in known:
            continue
        if r.claim_id is not None and r.total_paid > 0 and r.claim_status_code != "22":
            paid_claims.add(r.claim_id)
        if r.claim_status_code == "4" and payer_of.get(r.payment_id) == payer_id and known[r.event_id] < as_of:
            denied.append(r)
    reasons: dict[int, set[str]] = {}
    ids = {r.id for r in denied}
    for a in session.scalars(select(m.Adjustment)):
        if a.remit_id in ids:
            reasons.setdefault(a.remit_id, set()).add(a.reason_code)
    matching = [r for r in denied if carc in reasons.get(r.id, set())]
    wins = sum(1 for r in matching if r.claim_id in paid_claims)
    return wins, len(matching)


def win_probability(wins: int, n: int) -> Decimal:
    """Beta(1, 1) smoothing: (wins + 1) / (n + 2), so a payer + CARC with no history starts at one half."""
    return (Decimal(wins) + 1) / (Decimal(n) + 2)
