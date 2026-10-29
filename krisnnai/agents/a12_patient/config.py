"""A12 settings. Every value is a placeholder for the patient-billing lead's sign-off (docs/specs/A12.md).

This agent is staff-facing. Nothing here, or anywhere in the agent, sends anything to a patient.
"""

from __future__ import annotations

from decimal import Decimal

STATEMENT_DUE_DAYS = 7  # a first statement should go out this many days after the patient share is confirmed
AGING_FROM_DAYS = 30  # an open balance this old is followed up; stages at 30 / 60 / 90 days
STAGES = (90, 60, 30)
SMALL_BALANCE = Decimal("10.00")  # an open balance under this is a staff decision (never a write-off by the agent)
REPEAT_DAYS = 14  # how often an open item comes back
STAGE_WEIGHT = {30: Decimal("1.0"), 60: Decimal("1.5"), 90: Decimal("2.0")}  # priority = open balance x weight
