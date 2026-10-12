"""Rejection routing lives in a table, not code. The seeded rows are placeholders awaiting sign-off.

Only a 999 rejection (the file's structure or format is wrong) is seeded as technical. Every 277CA status is business by
default, and a code with no row is business and flagged unrouted, so the gap is visible. More technical rows are
added by sign-off, never by code. Verify the codes against the current X12 code lists before relying on them.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from krisnai.model import RejectionRoute

ANY = "*"
FIX_DAYS = 3  # target days from rejection to a fixed claim; TBD at spec review
FILING_RISK_DAYS = 60  # within this many days of the filing limit, urgency goes up; TBD at spec review

# (source, status_category, status_code, category, kind, owner, description)
DEFAULT_ROUTES: list[tuple[str, str, str, str, str, str, str]] = [
    ("999", "R", ANY, "edi_structure", "technical", "billing", "File rejected for structure or format: fix and resend"),
    ("999", "E", ANY, "accepted_with_errors", "business", "billing", "File accepted with errors: review each error"),
    ("277CA", "A3", "21", "missing_or_invalid_information", "business", "billing", "Returned: missing or invalid data"),
    ("277CA", "A3", ANY, "returned_unprocessable", "business", "billing", "Returned as unprocessable: read the reason"),
    ("277CA", "A4", ANY, "claim_not_found", "business", "billing", "Payer cannot find the claim: confirm receipt"),
]


@dataclass(frozen=True)
class Route:
    source: str
    status_category: str
    status_code: str
    category: str
    kind: str
    owner: str
    description: str


def seed_defaults(session: Session) -> int:
    """Insert any default route this tenant lacks. Existing rows (and edits to them) are left alone."""
    have = {(r.source, r.status_category, r.status_code) for r in session.scalars(select(RejectionRoute))}
    added = 0
    for source, category, code, name, kind, owner, description in DEFAULT_ROUTES:
        if (source, category, code) not in have:
            session.add(
                RejectionRoute(
                    source=source, status_category=category, status_code=code,
                    category=name, kind=kind, owner=owner, description=description,
                )  # fmt: skip
            )
            added += 1
    session.flush()
    return added


def load_routes(session: Session) -> dict[tuple[str, str, str], Route]:
    return {
        (r.source, r.status_category, r.status_code): Route(
            r.source, r.status_category, r.status_code, r.category, r.kind, r.owner, r.description
        )
        for r in session.scalars(select(RejectionRoute))
    }


def find_route(routes: dict[tuple[str, str, str], Route], source: str, category: str, code: str | None):
    """The exact code's row, else the category's `*` row, else None (unrouted)."""
    return routes.get((source, category, code or ANY)) or routes.get((source, category, ANY))
