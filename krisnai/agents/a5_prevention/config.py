"""Rule data for A5 lives in tables, not code. The seeded rows are placeholders awaiting sign-off and real CMS data."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from krisnai.model import MueLimit, NcciPair, PayerFilingWindow

DEFAULT_FILING_DAYS = 365  # TBD at spec review; used only when the payer has no payer_filing_window row
FILING_WARN_DAYS = 30  # flag a claim this close to its filing deadline; TBD at spec review

# Synthetic stand-ins, NOT the CMS tables: (cpt_a, cpt_b, modifier_indicator)
DEFAULT_NCCI: list[tuple[str, str, str]] = [("97140", "97530", "1"), ("99213", "99214", "0")]
DEFAULT_MUE: list[tuple[str, int]] = [("99213", 1), ("97110", 4)]


@dataclass(frozen=True)
class RuleData:
    ncci: dict[frozenset[str], str]  # {cpt_a, cpt_b} -> modifier_indicator
    mue: dict[str, int]
    filing_days: dict[int, int]  # payer.id -> days


def seed_defaults(session: Session) -> int:
    """Insert any default NCCI/MUE row this tenant lacks. Existing rows (and edits to them) are left alone."""
    have_ncci = {(r.cpt_a, r.cpt_b) for r in session.scalars(select(NcciPair))}
    have_mue = set(session.scalars(select(MueLimit.cpt)))
    added = 0
    for a, b, ind in DEFAULT_NCCI:
        if (a, b) not in have_ncci:
            session.add(NcciPair(cpt_a=a, cpt_b=b, modifier_indicator=ind))
            added += 1
    for cpt, limit in DEFAULT_MUE:
        if cpt not in have_mue:
            session.add(MueLimit(cpt=cpt, max_units=limit))
            added += 1
    session.flush()
    return added


def load(session: Session) -> RuleData:
    return RuleData(
        ncci={frozenset((r.cpt_a, r.cpt_b)): r.modifier_indicator for r in session.scalars(select(NcciPair))},
        mue={r.cpt: r.max_units for r in session.scalars(select(MueLimit))},
        filing_days={r.payer_id: r.filing_days for r in session.scalars(select(PayerFilingWindow))},
    )
