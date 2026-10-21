# ruff: noqa: E501
"""The v1 demo ruleset: a client-confirmed demo ruleset for the fictional payer SYNAETNA (plus one with gaps on purpose).

Every rule is labelled `kind="demo"`. None of it is an official payer policy and none of it is real payer data. The rules
change at 2026-01-01 so a December 2025 service and a January 2026 service must pick different versions.
"""

from __future__ import annotations

from datetime import date

from krisnai.knowledge.book import Book, Rule, Source

DEMO = Source("demo", "Client-confirmed demo ruleset (not official payer policy)")
PAYER = "SYNAETNA"
KNOWN_SINCE = date(2025, 1, 1)  # the book knew the 2025 and 2026 rules from the start of 2025
Y26 = date(2026, 1, 1)


def demo_book() -> Book:
    b = Book()

    def add(**kw) -> None:  # noqa: ANN003
        kw.setdefault("source", DEMO)
        kw.setdefault("payer", PAYER)
        kw.setdefault("active_from", KNOWN_SINCE)
        b.add(Rule(**kw))

    # coverage: outpatient therapy visit limit drops from 20 to 12 in 2026 (judged on the service date)
    add(rule_id="cov-97110", version=1, family="coverage", service="97110", date_basis="service_date",
        effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31), content={"covered": True, "visit_limit": 20})
    add(rule_id="cov-97110", version=2, family="coverage", service="97110", date_basis="service_date",
        effective_from=Y26, content={"covered": True, "visit_limit": 12})
    add(rule_id="cov-99213", version=1, family="coverage", service="99213", date_basis="service_date",
        effective_from=date(2025, 1, 1), content={"covered": True})
    # prior authorization: therapy needs one only from 2026
    add(rule_id="pa-97110", version=1, family="prior_auth", service="97110", date_basis="service_date",
        effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31), content={"required": False})
    add(rule_id="pa-97110", version=2, family="prior_auth", service="97110", date_basis="service_date",
        effective_from=Y26, content={"required": True, "valid_days": 90})
    # medical necessity evidence for therapy
    add(rule_id="mn-97110", version=1, family="medical_necessity", service="97110", date_basis="service_date",
        effective_from=date(2025, 1, 1), content={"evidence": ["signed plan of care", "functional goals", "progress note"]})
    # denial and appeal: the window is judged on the date the denial was notified, and shrinks for denials notified in 2026
    add(rule_id="appeal-all", version=1, family="denial_appeal", date_basis="denial_notification_date",
        effective_from=date(2025, 1, 1), effective_to=date(2025, 12, 31),
        content={"window_days": 180, "day_count": "calendar", "inclusive": False})
    add(rule_id="appeal-all", version=2, family="denial_appeal", date_basis="denial_notification_date", effective_from=Y26,
        content={"window_days": 120, "day_count": "calendar", "inclusive": False})
    # corrected claims are a different route with a different clock (from the service date)
    add(rule_id="corrected-all", version=1, family="billing", date_basis="service_date", effective_from=date(2025, 1, 1),
        content={"corrected_claim_window_days": 365, "day_count": "calendar", "inclusive": False})

    # a second payer whose appeal rule is incomplete on purpose: the book must refuse to compute a deadline from it
    add(rule_id="appeal-humana-demo", version=1, payer="SYNHUMANA", family="denial_appeal",
        date_basis="denial_notification_date", effective_from=date(2025, 1, 1),
        content={"window_days": None, "day_count": "calendar", "inclusive": False}, unknown=("window_days",),
        note="the window has not been confirmed with the client")
    return b
