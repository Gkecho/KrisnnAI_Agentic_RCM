"""Provider enrollment and screening feed for the simulated book, with planted defects and an answer key.

Synthea has no credentialing data, so it is simulated. Each (rendering NPI, payer) pair that bills gets an enrollment
row, or one planted defect. Three defects also change what the payer does: from a date claims for that pair are denied
with CARC 185 (rendering provider not eligible), decided in `simulate()` from `denial_dates`.

    lapsed             enrollment expired inside the book; later claims denied
    no_record          no enrollment row at all; claims denied from the start of the window
    denied_enrollment  the payer denied the application; later claims denied
    pending_long       application pending 100 to 200 days
    expiring_soon      active, expires 20 to 80 days after `as_of`
    stale_screening    a provider last screened 60 to 120 days ago
    excluded_provider  a provider whose screening result is "excluded"

The answer key lists a defect only when something is there to find: the lapse ones need services for the pair in the
last 90 days after the lapse (the dollars are the expected payment of those services). The simulator keeps its own
constants, apart from the agent's configuration.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from krisnai.synthea.types import SimClaim, SimVisit, money

BANDS = (  # cumulative bands of one draw per pair
    ("lapsed", 0.08), ("no_record", 0.13), ("denied_enrollment", 0.16), ("pending_long", 0.21), ("expiring_soon", 0.31),
)  # fmt: skip
WINDOW_DAYS = 90  # services in the last 90 days count as claim risk
LOOKBACK_DAYS = 548
ENROLLMENT_COLUMNS = ["enrollment_id", "provider_npi", "payer_id", "status", "status_on", "submitted_on",
                      "effective_on", "expires_on"]  # fmt: skip
SCREENING_COLUMNS = ["screening_id", "provider_npi", "screened_on", "result", "source"]
TRUTH_COLUMNS = ["key", "defect", "amount"]


@dataclass
class EnrollPlan:
    enrollments: list[dict] = field(default_factory=list)
    screenings: list[dict] = field(default_factory=list)
    truth: list[dict] = field(default_factory=list)


def plan_defects(pairs: set[tuple[str, str]], as_of: date, seed: int) -> dict[tuple[str, str], tuple[str, date | None]]:
    """pair -> (defect, date the payer starts denying or None). Deterministic from the seed and the sorted pairs."""
    rng = random.Random(seed + 71)
    out: dict[tuple[str, str], tuple[str, date | None]] = {}
    for pair in sorted(pairs):
        draw = rng.random()
        defect = next((name for name, upper in BANDS if draw < upper), "")
        if not defect:
            continue
        if defect == "no_record":
            out[pair] = (defect, as_of - timedelta(days=LOOKBACK_DAYS))
        elif defect in ("lapsed", "denied_enrollment"):
            out[pair] = (defect, as_of - timedelta(days=rng.randint(60, 300)))
        else:
            out[pair] = (defect, None)
    return out


def denial_dates(defects: dict[tuple[str, str], tuple[str, date | None]]) -> dict[tuple[str, str], date]:
    return {pair: when for pair, (_, when) in defects.items() if when is not None}


def plan_enrollment(
    claims: list[SimClaim], visits: list[SimVisit], as_of: date, seed: int,
    defects: dict[tuple[str, str], tuple[str, date | None]],
) -> EnrollPlan:
    rng = random.Random(seed + 73)
    plan = EnrollPlan()
    window_start = as_of - timedelta(days=WINDOW_DAYS)
    services: dict[tuple[str, str], list[tuple[date, Decimal]]] = {}
    for c in claims:
        for ln in c.lines:
            services.setdefault((c.provider_npi, c.payer.payer_id), []).append((c.dos, ln.expected_pay))
    for v in visits:
        services.setdefault((v.provider_npi, v.payer.payer_id), []).append((v.dos, v.expected_pay))

    def at_risk(pair, after: date) -> Decimal:
        start = max(after, window_start)
        return money(sum((amt for d, amt in services.get(pair, []) if start < d <= as_of), Decimal(0)))

    for n, pair in enumerate(sorted(services), start=1):
        npi, payer = pair
        defect, when = defects.get(pair, ("", None))
        ref = f"SYNEN{n:05d}"
        row = {"enrollment_id": ref, "provider_npi": npi, "payer_id": payer, "status": "active",
               "status_on": "", "submitted_on": "", "effective_on": "", "expires_on": ""}  # fmt: skip
        submitted = as_of - timedelta(days=rng.randint(500, 900))
        effective = submitted + timedelta(days=rng.randint(20, 60))
        if defect == "no_record":
            row = None
        elif defect == "lapsed":  # history: active until it expires, then expired on that day
            row.update(submitted_on=submitted.isoformat(), effective_on=effective.isoformat(),
                       expires_on=when.isoformat(), status_on=effective.isoformat())  # fmt: skip
            plan.enrollments.append(row)
            row = {**row, "enrollment_id": ref + "E", "status": "expired", "status_on": when.isoformat()}
        elif defect == "denied_enrollment":  # history: pending since the application, then denied
            asked = (when - timedelta(days=40)).isoformat()
            plan.enrollments.append({**row, "status": "pending", "submitted_on": asked, "status_on": asked})
            row = {**row, "enrollment_id": ref + "D", "status": "denied", "submitted_on": asked,
                   "status_on": when.isoformat()}  # fmt: skip
        elif defect == "pending_long":
            sub = as_of - timedelta(days=rng.randint(100, 200))
            row.update(status="pending", submitted_on=sub.isoformat(), status_on=sub.isoformat())
        else:
            span = rng.randint(20, 80) if defect == "expiring_soon" else rng.randint(120, 700)
            expires = as_of + timedelta(days=span)
            row.update(submitted_on=submitted.isoformat(), effective_on=effective.isoformat(),
                       expires_on=expires.isoformat(), status_on=effective.isoformat())  # fmt: skip
        if row is not None:
            plan.enrollments.append(row)
        key = f"{npi}|{payer}"
        if defect in ("lapsed", "no_record", "denied_enrollment"):
            amount = at_risk(pair, when)
            if amount > 0:
                kind = "enrollment_expired" if defect == "lapsed" else "billing_without_enrollment"
                plan.truth.append({"key": key, "defect": kind, "amount": f"{amount:.2f}"})
        elif defect == "pending_long":
            plan.truth.append({"key": key, "defect": "pending_too_long", "amount": "0.00"})
        elif defect == "expiring_soon":
            plan.truth.append({"key": key, "defect": "expiring_soon", "amount": "0.00"})

    providers = sorted({npi for npi, _ in services})
    for i, npi in enumerate(providers):
        stale, excluded = i == 0, i == 1 and len(providers) >= 3
        when = as_of - timedelta(days=rng.randint(60, 120) if stale else rng.randint(1, 25))
        plan.screenings.append({"screening_id": f"SYNSC{i + 1:05d}", "provider_npi": npi,
                                "screened_on": when.isoformat(), "result": "excluded" if excluded else "clear",
                                "source": "OIG"})  # fmt: skip
        if stale:
            plan.truth.append({"key": npi, "defect": "screening_stale", "amount": "0.00"})
        if excluded:
            plan.truth.append({"key": npi, "defect": "excluded_provider", "amount": "0.00"})
    return plan
