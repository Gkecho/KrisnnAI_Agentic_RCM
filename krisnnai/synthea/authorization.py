"""Prior-authorization feed for the simulated book, with planted defects and an answer key.

Synthea has no authorizations, so they are simulated. A claim carrying a CPT that needs prior authorization gets an
approved authorization covering the visit, or one planted defect (decided in `simulate()`, which also makes the first
two defects real CARC 197 denials):

    no_authorization       no request exists
    expired_authorization  approved, but the window ended before the visit
    pending_late           still requested 10 to 16 days before the visit, never decided
    units_exhausted        approved for 2 units, both already used a few days before the visit

The simulator keeps its own constants, apart from the agent's configuration, so the answer key does not borrow the
agent's rules.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from krisnnai.synthea.types import SimClaim, money

AUTH_CPTS = frozenset({"71046", "45378", "77067"})  # placeholder: imaging, colonoscopy, mammography
AUTH_COLUMNS = [
    "authorization_id", "appointment_id", "payer_id", "patient_ref", "cpt", "status", "requested_on", "decided_on",
    "units_approved", "units_used", "units_as_of", "start_date", "end_date",
]  # fmt: skip
TRUTH_COLUMNS = ["appointment_id", "authorization_id", "defect", "claim_id", "expected_amount"]


@dataclass
class AuthPlan:
    rows: list[dict] = field(default_factory=list)
    truth: list[dict] = field(default_factory=list)


def plan_authorizations(claims: list[SimClaim], seed: int) -> AuthPlan:
    rng = random.Random(seed + 59)
    plan = AuthPlan()
    for c in claims:
        line = next((ln for ln in c.lines if ln.cpt in AUTH_CPTS), None)
        if line is None:
            continue
        ref, appt = f"SYNAU{c.claim_id[-6:]}", f"SYNAP{c.claim_id[-6:]}"
        defect = c.auth_defect
        requested = c.dos - timedelta(days=rng.randint(10, 25))
        decided = requested + timedelta(days=rng.randint(2, 6))
        row = {"authorization_id": ref, "appointment_id": appt, "payer_id": c.payer.payer_id,
               "patient_ref": c.patient.ref, "cpt": line.cpt, "status": "approved",
               "requested_on": requested.isoformat(), "decided_on": decided.isoformat(),
               "units_approved": 4, "units_used": 0, "units_as_of": (c.dos - timedelta(days=1)).isoformat(),
               "start_date": (c.dos - timedelta(days=30)).isoformat(),
               "end_date": (c.dos + timedelta(days=60)).isoformat()}  # fmt: skip
        if defect == "no_authorization":
            row = None
        elif defect == "expired_authorization":
            row["end_date"] = (c.dos - timedelta(days=rng.randint(1, 10))).isoformat()
        elif defect == "pending_late":
            row.update(status="requested", decided_on="", units_approved="", units_used="", units_as_of="",
                       start_date="", end_date="",
                       requested_on=(c.dos - timedelta(days=rng.randint(10, 16))).isoformat())  # fmt: skip
        elif defect == "units_exhausted":
            row.update(units_approved=2, units_used=2, units_as_of=(c.dos - timedelta(days=3)).isoformat())
        if row is not None:
            plan.rows.append(row)
        if defect:
            amount = sum((ln.expected_pay for ln in c.lines), Decimal(0)) if c.scenario == "denial" else Decimal(0)
            plan.truth.append({"appointment_id": appt, "authorization_id": ref, "defect": defect,
                               "claim_id": c.claim_id, "expected_amount": f"{money(amount):.2f}"})  # fmt: skip
    return plan
