"""A9 settings. Every value is a placeholder for the practice manager's sign-off (docs/specs/A9.md)."""

from __future__ import annotations

from decimal import Decimal

MIN_DENIALS = 5  # a cluster needs at least this many denied claims
MIN_RATE = Decimal("0.30")  # ...and the payer must deny at least this share of its claims carrying the CPT
ALREADY_FLAGGED = Decimal("0.80")  # A5 already flagged this share of the cluster's claims: no new rule is needed
EXPLAINED_OVERLAP = Decimal("0.80")  # a weaker cluster sharing this much with a stronger one is the same defect
WINDOW_DAYS = 120  # denial rates are measured over claims the payer answered in this many days
SWEEP_EVERY_DAYS = 30
SAMPLE_CLAIMS = 5
CONTRACTUAL = "45"  # CARC 45 and patient responsibility are not denials
