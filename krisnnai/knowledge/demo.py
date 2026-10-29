# ruff: noqa: E501
"""The v1 demo ruleset: a client-confirmed demo ruleset for the fictional payer SYNAETNA (plus one with gaps on purpose).

Every rule is labelled `kind="demo"`. None of it is an official payer policy and none of it is real payer data. The rules
change at 2026-01-01 so a December 2025 service and a January 2026 service must pick different versions.
"""

from __future__ import annotations

from datetime import date, timedelta

from krisnnai.knowledge.book import Book, Rule, Source

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


# ---------------------------------------------------------------------------------------------------- the payer network (S6)
# Rule specs for six fictional payers. Same labelling as above: demo rules, not any real payer's policy. SYNAETNA keeps every
# rule above; the specs below only ADD rules for other services. A span `(start, end)` means "in force from start until end";
# `end=None` is open ended. Several rules change on 2026-01-01 so a December 2025 and a January 2026 service pick different versions.
Y25 = date(2025, 1, 1)
ALWAYS = (Y25, None)
FROM26 = (Y26, None)
ONLY25 = (Y25, date(2025, 12, 31))

# diagnosis prefixes (ICD-10 without the dot) that support a service, per medical-necessity rule
SUPPORT = {
    "72148": ("M54", "M51", "M47", "S32", "G83"),
    "70450": ("R51", "S06", "G43", "R55", "R42", "H53", "I63"),
    "71046": ("J", "R05", "R06", "R07", "R09", "A15", "I50"),
    "93000": ("I", "R00", "R07", "R42", "R55", "R06", "Z01"),
    "83036": ("E11", "E10", "E66", "R73", "Z13", "Z00"),
    "80061": ("E78", "I10", "I25", "E11", "Z00", "E66"),
    "84443": ("E03", "E02", "R53", "E66", "D64", "Z00"),
    "73560": ("M17", "M25", "S8", "M22", "M23", "M79"),
    "94010": ("J4", "R06", "J2", "R05", "J84"),
    "97110": ("M", "S", "G", "R26"),
    "97140": ("M", "S", "G"),
    "20610": ("M17", "M25", "M19", "M13", "M75"),
}

NETWORK_RULES: dict[str, dict] = {
    "SYNAETNA": dict(
        prior_auth={"72148": ALWAYS, "70450": FROM26},
        not_covered={},
        bundles=[("80053", "36415"), ("94010", "94640"), ("20610", "96372"), ("97530", "97140")],
        necessity=("71046", "93000", "83036"),
        filing=[(Y25, 365), (Y26, 180)], appeal=None, corrected=None),
    "SYNCIGNA": dict(
        prior_auth={"72148": ALWAYS, "70450": ALWAYS, "97112": ALWAYS, "97140": ALWAYS, "97530": ALWAYS, "97110": FROM26, "99205": FROM26, "20610": FROM26},
        not_covered={"99406": ONLY25},
        bundles=[("12001", "99213"), ("10060", "99213"), ("11102", "99213"), ("20610", "96372")],
        necessity=("72148", "73560", "93000", "80061", "83036"),
        filing=[(Y25, 180), (Y26, 90)], appeal=[(Y25, 180), (Y26, 120)], corrected=365),
    "SYNUNITED": dict(
        prior_auth={"72148": ALWAYS, "70450": ALWAYS, "97110": FROM26, "97112": FROM26, "97140": FROM26, "97530": FROM26, "99204": FROM26},
        not_covered={"17110": ALWAYS},
        bundles=[("80053", "36415"), ("85025", "36415"), ("94010", "94640"), ("97530", "97140"), ("93000", "99213")],
        necessity=("71046", "72148", "70450", "93000", "94010", "83036", "84443", "80061", "97110", "97140"),
        filing=[(Y25, 180), (Y26, 90)], appeal=[(Y25, 180), (Y26, 90)], corrected=180),
    "SYNBLUE": dict(
        prior_auth={"72148": ALWAYS, "70450": FROM26},
        not_covered={"17110": ONLY25},
        bundles=[("20610", "96372"), ("12001", "99213"), ("94010", "94640")],
        necessity=("72148", "70450", "83036"),
        filing=[(Y25, 365)], appeal=[(Y25, 180)], corrected=365),
    "SYNMCARE": dict(
        prior_auth={},
        not_covered={"99385": ALWAYS, "99395": ALWAYS, "99396": ALWAYS, "99393": ALWAYS, "17110": ALWAYS},
        bundles=[("80053", "36415"), ("85025", "36415"), ("20610", "96372"), ("12001", "99213"), ("10060", "99213"), ("11102", "99213"), ("93000", "99213")],
        necessity=("83036", "80061", "84443", "93000", "71046", "73560", "94010", "97110", "97140"),
        filing=[(Y25, 365)], appeal=[(Y25, 120)], corrected=365),
    "SYNMCAID": dict(
        prior_auth={"72148": ALWAYS, "70450": ALWAYS, "73560": ALWAYS, "97110": ALWAYS, "97112": ALWAYS, "97140": ALWAYS, "97530": ALWAYS, "20610": FROM26},
        not_covered={"17110": ALWAYS, "90837": FROM26},
        bundles=[("80053", "36415"), ("85025", "36415"), ("94010", "94640"), ("20610", "96372")],
        necessity=("71046", "93000", "83036"),
        filing=[(Y25, 180), (Y26, 90)], appeal=[(Y25, 60)], corrected=90),
}


def network_book() -> Book:
    """The demo book plus coverage, prior authorization, medical necessity, billing and appeal rules for all six payers."""
    b = demo_book()

    def add(payer: str, **kw) -> None:  # noqa: ANN003
        kw.setdefault("source", DEMO)
        kw.setdefault("active_from", KNOWN_SINCE)
        b.add(Rule(payer=payer, **kw))

    def versions(payer: str, rid: str, family: str, service: str, span: tuple[date, date | None], on: dict, off: dict) -> None:
        """`on` while the span is in force, `off` before it and after it (so a change shows as a new version)."""
        start, end = span
        v = 1
        if start > Y25:
            add(payer, rule_id=rid, version=v, family=family, service=service, date_basis="service_date", effective_from=Y25,
                effective_to=start - timedelta(days=1), content=off)
            v += 1
        add(payer, rule_id=rid, version=v, family=family, service=service, date_basis="service_date", effective_from=start, effective_to=end, content=on)
        if end is not None:
            add(payer, rule_id=rid, version=v + 1, family=family, service=service, date_basis="service_date", effective_from=end + timedelta(days=1), content=off)

    for payer, spec in NETWORK_RULES.items():
        for cpt, span in spec["prior_auth"].items():
            versions(payer, f"pa-{payer}-{cpt}", "prior_auth", cpt, span, {"required": True, "valid_days": 90}, {"required": False})
        for cpt, span in spec["not_covered"].items():
            versions(payer, f"cov-{payer}-{cpt}", "coverage", cpt, span, {"covered": False}, {"covered": True})
        by_component: dict[str, list[str]] = {}
        for primary, component in spec["bundles"]:
            by_component.setdefault(component, []).append(primary)
        for component, primaries in sorted(by_component.items()):
            add(payer, rule_id=f"bundle-{payer}-{component}", version=1, family="coverage", service=component, date_basis="service_date",
                effective_from=Y25, content={"covered": True, "bundled_into": sorted(primaries)})
        for cpt in spec["necessity"]:
            add(payer, rule_id=f"mn-{payer}-{cpt}", version=1, family="medical_necessity", service=cpt, date_basis="service_date",
                effective_from=Y25, content={"dx_prefixes": list(SUPPORT[cpt]), "evidence": ["documented indication"]})
        # the timely-filing limit hangs on a pseudo-service so it never collides with the corrected-claim rule of the same family
        fil = spec["filing"]
        for n, (start, days) in enumerate(fil, start=1):
            end = fil[n][0] - timedelta(days=1) if n < len(fil) else None
            add(payer, rule_id=f"filing-{payer}", version=n, family="billing", service="FILING", date_basis="service_date",
                effective_from=start, effective_to=end, content={"filing_days": days, "day_count": "calendar"})
        if spec["corrected"]:
            add(payer, rule_id=f"corrected-{payer}", version=1, family="billing", date_basis="service_date", effective_from=Y25,
                content={"corrected_claim_window_days": spec["corrected"], "day_count": "calendar", "inclusive": False})
        if spec["appeal"]:
            ap = spec["appeal"]
            for n, (start, days) in enumerate(ap, start=1):
                end = ap[n][0] - timedelta(days=1) if n < len(ap) else None
                add(payer, rule_id=f"appeal-{payer}", version=n, family="denial_appeal", date_basis="denial_notification_date",
                    effective_from=start, effective_to=end, content={"window_days": days, "day_count": "calendar", "inclusive": False})
    return b
