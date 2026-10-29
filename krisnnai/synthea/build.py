"""Synthea CSV folder -> X12 files, fee schedule, visits and ground truth that `krisnnai ingest` already reads."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from krisnnai.synthea.authorization import AUTH_CPTS, plan_authorizations
from krisnnai.synthea.bundles import LOOKBACK_DAYS, build_bundles
from krisnnai.synthea.cash import plan_cash
from krisnnai.synthea.documentation import plan_documentation
from krisnnai.synthea.enrollment import denial_dates, plan_defects, plan_enrollment
from krisnnai.synthea.eligibility import plan_eligibility
from krisnnai.synthea.patient import plan_patient
from krisnnai.synthea.reader import read_dir
from krisnnai.synthea.simulate import parse_denial_pattern, parse_rate_cut, simulate, write_dir


def build(
    synthea_dir: Path,
    out_dir: Path,
    as_of: date,
    seed: int = 7,
    lookback_days: int = LOOKBACK_DAYS,
    rate_cuts: list[str] | None = None,
    documentation: bool = False,
    eligibility: bool = False,
    denial_patterns: list[str] | None = None,
    authorization: bool = False,
    cash: bool = False,
    enrollment: bool = False,
    patient: bool = False,
    coding: bool = False,
) -> dict:
    """Return a report: what Synthea gave us, what was billable, what the simulator planted, what was written."""
    if authorization and not eligibility:
        raise ValueError("--authorization needs --eligibility: the authorization checks run on the appointments")
    if coding and not documentation:
        raise ValueError("--coding needs --documentation: the audit reads the note elements")
    if enrollment and not documentation:
        raise ValueError("--enrollment needs --documentation: the visits are the service evidence")
    data = read_dir(synthea_dir)
    bundles, report = build_bundles(data, as_of, lookback_days)
    defects = (
        plan_defects({(b.provider_npi, b.payer.payer_id) for b in bundles}, as_of, seed) if enrollment else {}
    )
    claims, visits = simulate(
        bundles, as_of, seed, [parse_rate_cut(t) for t in rate_cuts or []],
        [parse_denial_pattern(t) for t in denial_patterns or []],
        AUTH_CPTS if authorization else None,
        denial_dates(defects) if defects else None,
    )
    doc = plan_documentation(claims, visits, as_of, seed, coding) if documentation else None
    elig = plan_eligibility(claims, as_of, seed, AUTH_CPTS if authorization else frozenset()) if eligibility else None
    auth = plan_authorizations(claims, seed) if authorization else None
    cash_plan = plan_cash(claims, as_of, seed) if cash else None
    enroll_plan = plan_enrollment(claims, visits, as_of, seed, defects) if enrollment else None
    patient_plan = plan_patient(claims, as_of, seed) if patient else None
    written = write_dir(claims, visits, out_dir, as_of, doc, elig, auth, cash_plan, enroll_plan, patient_plan)
    planted: dict[str, int] = {}
    for c in claims:
        planted[c.scenario] = planted.get(c.scenario, 0) + 1
    return {
        "as_of": as_of.isoformat(), "seed": seed, "synthea": report, "claims_billed": len(claims),
        "unbilled_visits": len(visits), "claims_by_scenario": planted, "files": written,
    }  # fmt: skip
