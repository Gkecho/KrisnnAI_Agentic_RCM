"""The documentation checks as one pure function, shared by the sweeper (which visit?) and the agent (what is wrong?).

Everything is judged "as of" a date: a note, signature or charge dated after `as_of` does not exist yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from krisnai.agents.a3_documentation import config

NO_NOTE = "no_note"
UNSIGNED = "unsigned_note"
MISSING_ELEMENTS = "missing_elements"
MISSING_MINUTES = "missing_minutes"
NO_CHARGE = "no_charge"
CHARGE_LAG = "charge_lag"
# Actionable gaps in the order A3 raises them: money first, then a missing note, then signature, then content.
PRIORITY = (NO_CHARGE, NO_NOTE, UNSIGNED, MISSING_ELEMENTS, MISSING_MINUTES)


@dataclass(frozen=True)
class Note:
    note_date: date
    signed_date: date | None
    minutes: int | None
    elements: tuple[str, ...]


@dataclass(frozen=True)
class Gap:
    kind: str
    detail: str = ""

    @property
    def actionable(self) -> bool:
        return self.kind != CHARGE_LAG  # charge lag feeds the KPI; it is not work for a person on its own


def check(
    service_date: date, cpt: str, note: Note | None, charge_dates: list[date], billed: bool, as_of: date
) -> list[Gap]:
    """Gaps for one billable service as of a date, actionable ones first in PRIORITY order."""
    if note is not None and note.note_date > as_of:
        note = None  # not written yet
    known_charges = [d for d in charge_dates if d <= as_of]
    gaps: list[Gap] = []
    age = (as_of - service_date).days

    if note is None:
        if age >= config.DOC_DUE_DAYS:
            gaps.append(Gap(NO_NOTE, f"no note {age} days after the service"))
    else:
        signed = note.signed_date is not None and note.signed_date <= as_of
        if not signed and (as_of - note.note_date).days >= config.SIGN_DUE_DAYS:
            gaps.append(Gap(UNSIGNED, f"started {note.note_date.isoformat()}, not signed"))
        missing = [e for e in config.required_elements(cpt) if e not in note.elements]
        if missing:
            gaps.append(Gap(MISSING_ELEMENTS, ", ".join(missing)))
        if cpt in config.TIMED_CPTS and note.minutes is None:
            gaps.append(Gap(MISSING_MINUTES, "timed service without documented minutes"))
        if not known_charges and not billed and age > config.CHARGE_LAG_DAYS:
            gaps.append(Gap(NO_CHARGE, f"documented, no charge {age} days after the service"))

    if known_charges:
        lag = (min(known_charges) - service_date).days
        if lag > config.CHARGE_LAG_DAYS:
            gaps.append(Gap(CHARGE_LAG, f"charge entered {lag} days after the service"))
    gaps.sort(key=lambda g: PRIORITY.index(g.kind) if g.kind in PRIORITY else len(PRIORITY))
    return gaps
