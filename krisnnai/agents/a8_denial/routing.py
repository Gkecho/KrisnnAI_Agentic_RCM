"""CARC routing and payer appeal windows live in tables, not code. Seed defaults, all awaiting sign-off."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from krisnnai.model import CarcRoute, PayerAppealWindow

DEFAULT_APPEAL_DAYS = 180

# (carc, category, owner, disposition, description)
DEFAULT_ROUTES: list[tuple[str, str, str, str, str]] = [
    ("27", "coverage", "front_desk", "correctable", "Expenses incurred after coverage terminated"),
    ("31", "coverage", "front_desk", "correctable", "Patient cannot be identified as the payer's insured"),
    ("22", "coordination_of_benefits", "front_desk", "correctable", "May be covered by another payer"),
    ("197", "authorization", "front_desk", "appealable", "Precertification / authorization absent"),
    ("198", "authorization", "front_desk", "appealable", "Precertification / notification exceeded"),
    ("4", "coding", "coding", "correctable", "Procedure code inconsistent with the modifier"),
    ("11", "coding", "coding", "correctable", "Diagnosis inconsistent with the procedure"),
    ("97", "bundling", "coding", "appealable", "Payment included in the allowance for another service"),
    ("50", "medical_necessity", "coding", "appealable", "Not deemed medically necessary"),
    ("16", "missing_information", "billing", "correctable", "Claim lacks information needed to adjudicate"),
    ("18", "duplicate", "billing", "write_off_review", "Exact duplicate claim / service"),
    ("29", "timely_filing", "billing", "write_off_review", "Time limit for filing has expired"),
]


@dataclass(frozen=True)
class Route:
    carc: str
    category: str
    owner: str
    disposition: str
    description: str


def seed_defaults(session: Session) -> int:
    """Insert any default route this tenant does not have yet. Existing rows (and edits to them) are left alone."""
    have = set(session.scalars(select(CarcRoute.carc_code)))
    added = 0
    for carc, category, owner, disposition, description in DEFAULT_ROUTES:
        if carc not in have:
            session.add(
                CarcRoute(
                    carc_code=carc, category=category, owner=owner, disposition=disposition, description=description
                )
            )
            added += 1
    session.flush()
    return added


def load_routes(session: Session) -> dict[str, Route]:
    return {
        r.carc_code: Route(r.carc_code, r.category, r.owner, r.disposition, r.description)
        for r in session.scalars(select(CarcRoute))
    }


def appeal_window(session: Session, payer_id: int) -> tuple[int, bool]:
    """(days, from_table). The default applies when the payer has no row."""
    row = session.scalars(select(PayerAppealWindow).where(PayerAppealWindow.payer_id == payer_id)).first()
    return (row.appeal_days, True) if row is not None else (DEFAULT_APPEAL_DAYS, False)
