"""Which claims the payer or clearinghouse has bounced, known by a given moment.

Shared by A5, A14 and anything else that must not treat a claim that never reached adjudication as a live claim.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m


def rejection_sets(session: Session, end: datetime) -> tuple[set[str], set[tuple[str, str]]]:
    """(claim ids returned by the 277CA, (GS06, ST02) of files the 999 rejected), known by `end`."""
    returned = set(
        session.scalars(
            select(m.Ack277Ca.claim_submitter_id)
            .join(m.Event, m.Event.id == m.Ack277Ca.event_id)
            .where(m.Ack277Ca.status_category.in_(["A3", "A4"]), m.Event.known_at <= end)
        )
    )
    files = {
        (g, s)
        for g, s in session.execute(
            select(m.Ack999.acked_gs06, m.Ack999.acked_st02)
            .join(m.Event, m.Event.id == m.Ack999.event_id)
            .where(m.Ack999.transaction_status == "R", m.Event.known_at <= end)
        )
    }
    return returned, files
