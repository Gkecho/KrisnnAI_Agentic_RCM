"""A15-lite settings. Every default here is a business assumption awaiting sign-off (see docs/specs/a15_lite.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

# Finding types. They match the issue_type values in the synthetic ground truth.
DENIAL = "denial"
TIMELY_FILING = "timely_filing"
UNDERPAYMENT = "underpayment"
REJECTION = "rejection"
UNBILLED_VISIT = "unbilled_visit"
UNEXPLAINED_ADJUSTMENT = "unexplained_adjustment"

# CARC -> denial category. Anything not listed is "other".
CARC_CATEGORY = {
    "16": "missing_information",
    "18": "duplicate",
    "50": "medical_necessity",
    "97": "bundling",
    "27": "coverage",
    "31": "coverage",
    "197": "authorization",
    "4": "coding",
    "29": "timely_filing",
}

# Which later agent would work each finding. Denials depend on the category (see AGENT_BY_CATEGORY).
AGENT_BY_TYPE = {
    TIMELY_FILING: "A5",  # claim prevention: filing-deadline checks
    UNDERPAYMENT: "A10",  # contract / underpayment
    REJECTION: "A6",  # submission and response
    UNBILLED_VISIT: "A3",  # charge capture (needs PM schedule and notes)
    UNEXPLAINED_ADJUSTMENT: "A7",  # AR next-best-action
}
AGENT_BY_CATEGORY = {
    "coverage": "A1",  # eligibility / registration
    "duplicate": "A5",
    "missing_information": "A8",
    "coding": "A8",
    "authorization": "A8",
    "medical_necessity": "A8",
    "bundling": "A8",
    "timely_filing": "A5",
    "other": "A8",
}


@dataclass
class A15Config:
    appeal_window_days: int = 180
    filing_window_days: int = 365
    # per payer code overrides, e.g. {"SYNPAY01": 120}
    appeal_window_overrides: dict[str, int] = field(default_factory=dict)
    filing_window_overrides: dict[str, int] = field(default_factory=dict)
    g0_tolerance: Decimal = Decimal("0.01")  # largest accepted difference per checked total
    g0_min_match_rate: Decimal = Decimal("0.99")  # remits must be linked to claims (run `krisnai match` first)
    share_places: int = 3  # patient share learned per payer, rounded to 0.1%
    fallback_min_shortfall: Decimal = Decimal("0.20")  # fallback-priced lines flag only when 20% below the median

    def appeal_window(self, payer_code: str) -> int:
        return self.appeal_window_overrides.get(payer_code, self.appeal_window_days)

    def filing_window(self, payer_code: str) -> int:
        return self.filing_window_overrides.get(payer_code, self.filing_window_days)
