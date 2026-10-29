"""A11 settings. Every value is a placeholder for the payment poster's and finance lead's sign-off (A11 spec)."""

from __future__ import annotations

from decimal import Decimal

DEPOSIT_DUE_DAYS = 5  # the money should be in the bank this many days after the payment date
DEPOSIT_LATE_DAYS = 7  # a deposit later than this is late (KPI only)
POST_DUE_DAYS = 3  # a payment should be posted this many days after the payment date
POST_LATE_DAYS = 7  # a posting later than this is late (KPI only)
MATCH_WINDOW_DAYS = 30  # a deposit with no trace is matched on payer + amount within this many days
UNIDENTIFIED_AFTER_DAYS = 7  # a deposit with no payment is raised this many days after it arrived
REPEAT_DAYS = 7  # how often an open reconciliation gap comes back
TOLERANCE = Decimal("0.00")  # differences up to this amount are not reported
