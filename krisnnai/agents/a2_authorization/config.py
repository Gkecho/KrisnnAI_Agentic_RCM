"""A2 settings. Every value is a placeholder for the authorization specialist's sign-off (docs/specs/A2.md)."""

from __future__ import annotations

CHECKPOINT_DAYS = (7, 2)  # look this many days before the visit
PENDING_DAYS = 7  # a request still undecided after this many days is chased
PENDING_WINDOW_DAYS = 7  # ...once the visit is within this many days
VALIDITY_DAYS = 90  # how long a new approval normally lasts

# Placeholder payer + CPT pairs that need prior authorization (not payer policy). `a2 seed` loads them for every
# payer the tenant has.
DEFAULT_CPTS = ("71046", "45378", "77067")
