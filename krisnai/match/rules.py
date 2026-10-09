"""Matching rules as pure functions over small value objects (no database access).

Rule names are stored in `match_method` (String(30)), so each must stay short.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

CLP01 = "clp01"
CLP07 = "clp07"
PATIENT_DOS_AMOUNT = "patient_dos_amount"
LINE_EXACT = "line_exact"
LINE_CPT_MOD = "line_cpt_mod"

NO_CANDIDATE = "no_candidate"
AMBIGUOUS = "ambiguous"
PAYER_MISMATCH = "payer_mismatch"
AMOUNT_MISMATCH = "amount_mismatch"
NO_CLAIM = "claim_not_matched"


@dataclass(frozen=True)
class ClaimKey:
    id: int
    payer_id: int
    submitter_id: str
    patient_ref_id: int
    service_date: date | None
    total_charge: Decimal
    submitted_on: date | None
    pcn: str | None  # REF*F8 on the claim itself; may be filled from a matched 277CA


@dataclass(frozen=True)
class LineKey:
    id: int
    cpt: str
    modifiers: tuple[str, ...]
    service_date: date | None
    units: Decimal | None


def modifiers(*mods: str | None) -> tuple[str, ...]:
    return tuple(m for m in mods if m)


def latest_version(claims: list[ClaimKey]) -> ClaimKey:
    """Among versions of the same claim (replacement, re-send) the most recently submitted wins."""
    return max(claims, key=lambda c: (c.submitted_on or date.min, c.id))


def pick(candidates: list[ClaimKey]) -> tuple[ClaimKey | None, str | None]:
    """Collapse candidates to one claim. Several versions of one CLM01 are fine; different claims are ambiguous."""
    if not candidates:
        return None, NO_CANDIDATE
    if len({c.submitter_id for c in candidates}) > 1:
        return None, AMBIGUOUS
    return latest_version(candidates), None


def line_exact(remit_line: LineKey, claim_lines: list[LineKey]) -> list[LineKey]:
    """Procedure + modifiers + service date + units. A missing date or units on the remit side is not compared."""
    return [
        c
        for c in claim_lines
        if c.cpt == remit_line.cpt
        and c.modifiers == remit_line.modifiers
        and (remit_line.service_date is None or c.service_date is None or c.service_date == remit_line.service_date)
        and (remit_line.units is None or c.units == remit_line.units)
    ]


def line_cpt_mod(remit_line: LineKey, claim_lines: list[LineKey]) -> list[LineKey]:
    return [c for c in claim_lines if c.cpt == remit_line.cpt and c.modifiers == remit_line.modifiers]
