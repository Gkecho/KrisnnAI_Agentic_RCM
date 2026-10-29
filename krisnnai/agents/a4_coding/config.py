"""A4 settings. The level table is a PLACEHOLDER for the lead coder's and compliance owner's sign-off.

It is not the AMA CPT or CMS E/M guidelines. Level support here means "these named note elements are present", nothing
more. A certified coder always decides; this agent suggests.
"""

from __future__ import annotations

BASELINE = ("assessment", "plan")  # needed before any level is judged; missing baseline is A3's finding, not A4's
EXTRA = ("history_detailed", "exam_expanded")  # what a level-4 E/M needs on top of the baseline

# family -> (lower level code, higher level code); level-specific elements by code
FAMILIES = {"established": ("99213", "99214"), "new": ("99203", "99204")}
LEVEL_ELEMENTS: dict[str, tuple[str, ...]] = {"99213": (), "99214": EXTRA, "99203": (), "99204": EXTRA}
FAMILY_OF = {code: family for family, codes in FAMILIES.items() for code in codes}

SUGGESTION_ONLY = "Suggestion only: a certified coder decides; this agent changes no code, modifier or diagnosis."
