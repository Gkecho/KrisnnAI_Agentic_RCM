"""Synthea CSV folder -> X12 files, fee schedule, visits and ground truth that `krisnai ingest` already reads."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from krisnai.synthea.authorization import AUTH_CPTS, plan_authorizations
from krisnai.synthea.bundles import LOOKBACK_DAYS, build_bundles
from krisnai.synthea.cash import plan_cash
from krisnai.synthea.documentation import plan_documentation
from krisnai.synthea.eligibility import plan_eligibility
from krisnai.synthea.reader import read_dir
from krisnai.synthea.simulate import parse_denial_pattern, parse_rate_cut, simulate, write_dir


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
) -> dict:
    """Return a report: what Synthea gave us, what was billable, what the simulator planted, what was written."""
    if authorization and not eligibility:
        raise ValueError("--authorization needs --eligibility: the authorization checks run on the appointments")
    data = read_dir(synthea_dir)
    bundles, report = build_bundles(data, as_of, lookback_days)
    claims, visits = simulate(
        bundles, as_of, seed, [parse_rate_cut(t) for t in rate_cuts or []],
        [parse_denial_pattern(t) for t in denial_patterns or []],
        AUTH_CPTS if authorization else None,
    )
    doc = plan_documentation(claims, visits, as_of, seed) if documentation else None
    elig = plan_eligibility(claims, as_of, seed, AUTH_CPTS if authorization else frozenset()) if eligibility else None
    auth = plan_authorizations(claims, seed) if authorization else None
    cash_plan = plan_cash(claims, as_of, seed) if cash else None
    written = write_dir(claims, visits, out_dir, as_of, doc, elig, auth, cash_plan)
    planted: dict[str, int] = {}
    for c in claims:
        planted[c.scenario] = planted.get(c.scenario, 0) + 1
    return {
        "as_of": as_of.isoformat(), "seed": seed, "synthea": report, "claims_billed": len(claims),
        "unbilled_visits": len(visits), "claims_by_scenario": planted, "files": written,
    }  # fmt: skip
