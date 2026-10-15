"""Level-of-service support as pure functions: is the billed E/M level supported by the documented elements?

Nothing here selects or changes a code. It reports a difference between the billed level and the highest level the
named elements support, and leaves the decision to a coder.
"""

from __future__ import annotations

from dataclasses import dataclass

from krisnai.agents.a4_coding import config

UNSUPPORTED = "level_unsupported"  # billed above what is documented: overcoding risk (compliance)
COULD_BE_HIGHER = "level_could_be_higher"  # documented above what is billed: an opportunity the coder may decline
SKIPPED_NO_NOTE = "no_signed_note"
SKIPPED_BASELINE = "baseline_missing"


@dataclass(frozen=True)
class Finding:
    kind: str  # UNSUPPORTED | COULD_BE_HIGHER
    billed: str
    documented: str
    missing: tuple[str, ...]  # level-specific elements the billed level needs and the note lacks


def supported_level(family: str, elements: set[str]) -> str:
    """The highest code in the family whose level-specific elements are all documented."""
    best = config.FAMILIES[family][0]
    for code in config.FAMILIES[family]:
        if set(config.LEVEL_ELEMENTS[code]) <= elements:
            best = code
    return best


def check(cpt: str, elements: set[str] | None, signed: bool) -> tuple[Finding | None, str]:
    """(finding or None, reason). The reason says why nothing was judged when there is no finding and no match."""
    if cpt not in config.FAMILY_OF:
        return None, "not_levelled"
    if elements is None or not signed:
        return None, SKIPPED_NO_NOTE
    if not set(config.BASELINE) <= elements:
        return None, SKIPPED_BASELINE
    family = config.FAMILY_OF[cpt]
    documented = supported_level(family, elements)
    codes = config.FAMILIES[family]
    if codes.index(cpt) > codes.index(documented):
        missing = tuple(e for e in config.LEVEL_ELEMENTS[cpt] if e not in elements)
        return Finding(UNSUPPORTED, cpt, documented, missing), "judged"
    if codes.index(cpt) < codes.index(documented):
        return Finding(COULD_BE_HIGHER, cpt, documented, ()), "judged"
    return None, "judged"
