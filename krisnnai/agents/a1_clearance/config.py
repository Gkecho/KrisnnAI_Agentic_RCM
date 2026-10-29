"""A1 settings. Every value is a placeholder for front-desk lead / practice manager sign-off (docs/specs/A1.md)."""

from __future__ import annotations

CHECKPOINT_DAYS = (3, 1)  # re-check this many days before the visit (72 h and 24 h); booking is the first check
STALE_DAYS = 14  # an eligibility answer older than this is not trusted for the visit
