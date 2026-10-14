"""A3 settings. Every value is a placeholder for provider-lead / practice-manager sign-off (docs/specs/A3.md)."""

from __future__ import annotations

DOC_DUE_DAYS = 3  # a note should exist this many days after the service
SIGN_DUE_DAYS = 3  # a note should be signed this many days after it was started
CHARGE_LAG_DAYS = 3  # a charge keyed later than this is a lagging charge; a missing charge past it is a missed charge
REPEAT_DAYS = 7  # how often an open gap comes back to the inbox

# Elements a note must contain, by service group (placeholder list, not a coding reference)
EM_CPTS = frozenset({"99213", "99214", "99203", "99204", "99283", "99395", "99396"})
SCREEN_CPTS = frozenset({"96127"})
TIMED_CPTS = frozenset({"97110", "97140", "90837"})  # need minutes in the note
REQUIRED = {"em": ("assessment", "plan"), "procedure": ("procedure_note",), "screen": ("result",)}


def group_of(cpt: str) -> str:
    return "em" if cpt in EM_CPTS else "screen" if cpt in SCREEN_CPTS else "procedure"


def required_elements(cpt: str) -> tuple[str, ...]:
    return REQUIRED[group_of(cpt)]
