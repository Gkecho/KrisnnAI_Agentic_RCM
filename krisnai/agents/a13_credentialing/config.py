"""A13 settings. Every value is a placeholder for the compliance owner's sign-off (docs/specs/A13.md)."""

from __future__ import annotations

EXPIRY_WARN_DAYS = 90  # an enrollment that expires within this many days is raised
PENDING_DAYS = 90  # an application pending this long is chased
SERVICE_WINDOW_DAYS = 90  # services in this many days count as claim risk
SCREENING_STALE_DAYS = 35  # a screening older than this is out of date (monthly list checks)
REPEAT_DAYS = 14  # how often an open gap comes back
