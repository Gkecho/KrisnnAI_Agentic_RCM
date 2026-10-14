"""A10 settings. Every value here is a placeholder for finance sign-off (docs/specs/A10.md)."""

from __future__ import annotations

from decimal import Decimal

FEE_FLOOR = Decimal("1.00")  # a line paid at least this far under the contract (fee-schedule basis) is flagged
FALLBACK_FLOOR = Decimal("0.20")  # on payer-history pricing only a gap of 20% of the expected amount is flagged
MIN_PATTERN_LINES = 5  # fewer similar short-paid lines than this are not called a pattern
BUCKET_WIDTH = Decimal("0.01")  # gaps within one point of the commonest gap % belong to the same pattern
DOMINANT_SHARE = Decimal("0.50")  # ...and that group must be at least half of the short lines for the code

# The nine underpayment root causes in the source RCM document (docs/RCM_REVIEW.md), keyed from the CARC found on
# the short-paid line. A line with no odd adjustment (only CARC 45) is a contract pricing difference.
CONTRACT_PRICING = "contract_pricing"
DATA_CODING = "data_coding"
CAUSE_BY_CARC = {
    "4": "modifiers",
    "59": "bundling_ncci",
    "97": "bundling_ncci",
    "151": "units_charges",
    "50": "medical_necessity",
    "197": "authorization",
    "29": "timely_filing",
    "16": "data_coding",
    "B15": "payer_policy",
    "N130": "payer_policy",
}
CAUSES = (
    CONTRACT_PRICING, "modifiers", "bundling_ncci", "units_charges", "medical_necessity", "authorization",
    "timely_filing", "payer_policy", DATA_CODING,
)  # fmt: skip
