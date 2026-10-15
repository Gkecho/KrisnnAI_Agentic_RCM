"""Appointment and 271 eligibility feed for the simulated book, with planted coverage problems and an answer key.

Synthea has no appointment or eligibility transactions, so these are simulated. Each billed claim gets an appointment
(booked 3 to 13 days before the visit, coverage on file = the payer billed) and a 271 answer produced at booking:

    coverage_inactive  the 271 says coverage had ended (given to every claim the payer denied with CARC 27 or 31)
    cob_other_payer    the 271 shows another payer is primary
    no_check           no 271 exists for the appointment
    stale_check        booked 20 to 40 days ahead, checked once at booking, never again

Normal answers are active with 10% coinsurance (the simulator's patient share), so the clearance estimate can be
compared with what the patient later owes. The simulator keeps its own constants, apart from the agent's configuration.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from krisnai.synthea.types import PayerInfo, SimClaim, money
from krisnai.synthea.x12out import BILLING_NPI, CLINIC, SENDER, _amt, _envelope, _seg

SHARES = {"cob_other_payer": 0.04, "no_check": 0.08, "stale_check": 0.05}
COVERAGE_CARCS = ("27", "31")
COINSURANCE = "0.10"
APPOINTMENT_COLUMNS = ["appointment_id", "payer_id", "provider_npi", "patient_ref", "appt_date", "booked_on", "cpt",
                       "status"]  # fmt: skip
TRUTH_COLUMNS = ["appointment_id", "defect", "claim_id", "expected_amount"]


@dataclass
class EligPlan:
    appointments: list[dict] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)  # file name -> 271 text
    truth: list[dict] = field(default_factory=list)


@dataclass
class _Answer:
    ref: str
    claim: SimClaim
    checked_on: date
    active: bool = True
    plan_end: date | None = None
    other: str = ""


def plan_eligibility(
    claims: list[SimClaim], as_of: date, seed: int, prefer_cpts: frozenset[str] = frozenset()
) -> EligPlan:
    """`prefer_cpts`: the appointment is booked for one of these services when the claim carries it (a scheduled
    procedure), else for the first line."""
    rng = random.Random(seed + 29)
    plan = EligPlan()
    answers: list[_Answer] = []
    order = list(range(len(claims)))
    rng.shuffle(order)
    kind_of: dict[int, str] = {}
    for kind, share in SHARES.items():
        want = max(1, int(len(claims) * share))
        for idx in order:
            if want == 0:
                break
            if idx in kind_of or claims[idx].scenario != "clean":
                continue
            kind_of[idx] = kind
            want -= 1

    for idx, c in enumerate(claims):
        ref = f"SYNAP{c.claim_id[-6:]}"
        inactive = c.scenario == "denial" and c.carc in COVERAGE_CARCS
        kind = "coverage_inactive" if inactive else kind_of.get(idx, "")
        ahead = rng.randint(20, 40) if kind == "stale_check" else rng.randint(3, 13)
        booked = c.dos - timedelta(days=ahead)
        plan.appointments.append({
            "appointment_id": ref, "payer_id": c.payer.payer_id, "provider_npi": c.provider_npi,
            "patient_ref": c.patient.ref, "appt_date": c.dos.isoformat(), "booked_on": booked.isoformat(),
            "cpt": next((ln.cpt for ln in c.lines if ln.cpt in prefer_cpts), c.lines[0].cpt), "status": "booked",
        })  # fmt: skip
        if kind != "no_check":
            ans = _Answer(ref, c, booked)
            if kind == "coverage_inactive":
                ans.active, ans.plan_end = False, c.dos - timedelta(days=rng.randint(10, 60))
            elif kind == "cob_other_payer":
                ans.other = "OTHER PRIMARY PAYER"
            answers.append(ans)
        if kind:
            amount = sum((ln.expected_pay for ln in c.lines), Decimal(0)) if kind == "coverage_inactive" else Decimal(0)
            plan.truth.append({"appointment_id": ref, "defect": kind, "claim_id": c.claim_id,
                               "expected_amount": f"{money(amount):.2f}"})  # fmt: skip

    ctrl = 50000
    by_file: dict[tuple[str, date], list[_Answer]] = {}
    for a in answers:
        by_file.setdefault((a.claim.payer.payer_id, a.checked_on), []).append(a)
    for (pid, day), items in sorted(by_file.items()):
        ctrl += 1
        plan.files[f"271_{pid}_{day:%Y%m%d}.x12"] = write_271(items[0].claim.payer, items, ctrl, day)
    return plan


def write_271(payer: PayerInfo, answers: list[_Answer], ctrl: int, when: date) -> str:
    body = [
        _seg("BHT", "0022", "11", f"SYN271{ctrl}", when.strftime("%Y%m%d"), "1200"),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "PR", "2", payer.name, "", "", "", "", "PI", payer.payer_id),
        _seg("HL", 2, 1, "21", 1),
        _seg("NM1", "1P", "2", CLINIC, "", "", "", "", "XX", BILLING_NPI),
    ]
    for hl, a in enumerate(answers, start=3):
        c, p = a.claim, a.claim.patient
        body += [
            _seg("HL", hl, 2, "22", 0),
            _seg("TRN", "2", f"TRC{a.ref}", SENDER),
            _seg("NM1", "IL", "1", p.last, p.first, "", "", "", "MI", p.ref),
            _seg("DTP", "291", "D8", c.dos.strftime("%Y%m%d")),
            _seg("DTP", "346", "D8", (c.dos - timedelta(days=365)).strftime("%Y%m%d")),
        ]
        if a.plan_end is not None:
            body.append(_seg("DTP", "347", "D8", a.plan_end.strftime("%Y%m%d")))
        body.append(_seg("EB", "1" if a.active else "6", "IND", "30"))
        if a.other:
            body += [_seg("EB", "R", "IND", "30"), _seg("NM1", "PR", "2", a.other, "", "", "", "", "PI", "OTHERPAY")]
        if a.active:
            body.append(_seg("EB", "A", "IND", "98", "", "", "", "", COINSURANCE))
            body.append(_seg("EB", "C", "IND", "30", "", "", "29", _amt(Decimal("0"))))
    return _envelope("HB", "005010X279A1", "271", "005010X279A1", body, ctrl, payer.payer_id, SENDER, when)
