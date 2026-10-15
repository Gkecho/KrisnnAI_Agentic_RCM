"""A15 investigator settings. Every value is a placeholder for the revenue assurance lead (docs/specs/A15.md)."""

from __future__ import annotations

from decimal import Decimal

RECENT_DAYS = 56  # realisation is measured over remit lines paid in this many days...
BASELINE_DAYS = 180  # ...against the baseline of this many days before them
MIN_LINES = 8  # a slice needs this many priced lines in each window
MIN_EXPECTED = Decimal("500.00")  # ...and this much contract value in the recent window
DROP_POINTS = Decimal("0.05")  # realisation must have fallen this far (5 points)
CHANGE_POINTS = Decimal("0.02")  # a flagged slice raises a new event when its drop moves this far
SWEEP_EVERY_DAYS = 28
