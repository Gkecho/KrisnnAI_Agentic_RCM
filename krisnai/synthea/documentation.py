"""Note and charge feed for the simulated book, with planted documentation defects and an answer key.

Synthea has no note text, signature state or charge-entry log, so those are simulated here. Every billed claim line is
one "visit" (one billable service); each gets a note and a charge, and some are broken on purpose:

    missing_note     no note at all
    unsigned_note    note written, never signed
    missing_element  a required element is absent from the note
    charge_lag       charge keyed 4 or more days after the service
    missed_charge    visit with a signed note and no charge (the planted unbilled visits)

Defects are only planted on visits old enough that a check run at `as_of` can know about them. The constants below are
the simulator's own, kept apart from the agent's configuration so the answer key does not borrow the agent's rules.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from krisnai.synthea.types import SimClaim, SimVisit, money

SHARES = {"missing_note": 0.05, "unsigned_note": 0.06, "missing_element": 0.06, "charge_lag": 0.08}
MIN_AGE_DAYS = 10  # a defect is planted only on a visit at least this old at as_of
LAG_MIN_SUBMIT_GAP = 5  # charge_lag needs room before the claim goes out (charge keyed the day before submission)
MISSED_CHARGE_MIN_AGE = 4

EM = {"99213", "99214", "99203", "99204", "99283", "99395", "99396"}
SCREEN = {"96127"}
REQUIRED = {"em": ("assessment", "plan"), "procedure": ("procedure_note",), "screen": ("result",)}


def group_of(cpt: str) -> str:
    return "em" if cpt in EM else "screen" if cpt in SCREEN else "procedure"


@dataclass
class DocPlan:
    visit_rows: list[dict] = field(default_factory=list)
    note_rows: list[dict] = field(default_factory=list)
    charge_rows: list[dict] = field(default_factory=list)
    truth_rows: list[dict] = field(default_factory=list)


VISIT_COLUMNS = ["visit_id", "payer_id", "provider_npi", "patient_ref", "dos", "cpt", "units"]
NOTE_COLUMNS = ["visit_id", "note_date", "signed_date", "minutes", "elements"]
CHARGE_COLUMNS = ["charge_id", "visit_id", "cpt", "units", "entered_date"]
TRUTH_COLUMNS = ["visit_id", "defect", "detail", "expected_amount"]


def plan_documentation(claims: list[SimClaim], visits: list[SimVisit], as_of: date, seed: int) -> DocPlan:
    rng = random.Random(seed + 13)  # own stream: the claims and payer behaviour already drawn do not move
    doc = DocPlan()
    lines = []  # (visit_ref, claim, line_no, line)
    for c in claims:
        for n, ln in enumerate(c.lines, start=1):
            lines.append((f"SYNVC{c.claim_id[-6:]}L{n}", c, n, ln))
    order = list(range(len(lines)))
    rng.shuffle(order)
    plant: dict[int, str] = {}
    for kind, share in SHARES.items():
        want = max(1, int(len(lines) * share))
        for idx in order:
            if want == 0:
                break
            ref, c, _, _ = lines[idx]
            if idx in plant or (as_of - c.dos).days < MIN_AGE_DAYS:
                continue
            if kind == "charge_lag" and (c.submitted - c.dos).days < LAG_MIN_SUBMIT_GAP:
                continue
            plant[idx] = kind
            want -= 1

    for idx, (ref, c, _, ln) in enumerate(lines):
        doc.visit_rows.append({
            "visit_id": ref, "payer_id": c.payer.payer_id, "provider_npi": c.provider_npi,
            "patient_ref": c.patient.ref, "dos": c.dos.isoformat(), "cpt": ln.cpt, "units": ln.units,
        })  # fmt: skip
        kind = plant.get(idx, "")
        required = list(REQUIRED[group_of(ln.cpt)])
        if kind != "missing_note":
            elements = list(required)
            detail = ""
            if kind == "missing_element":
                gone = rng.choice(required)
                elements.remove(gone)
                detail = f"missing {gone}"
            note_date = c.dos + timedelta(days=rng.randint(0, 1))
            signed = None if kind == "unsigned_note" else note_date + timedelta(days=rng.randint(0, 2))
            doc.note_rows.append({
                "visit_id": ref, "note_date": note_date.isoformat(),
                "signed_date": signed.isoformat() if signed else "",
                "minutes": "", "elements": ",".join(elements),
            })  # fmt: skip
            if kind == "missing_element":
                doc.truth_rows.append(_truth(ref, kind, detail, Decimal("0")))
        if kind == "charge_lag":
            entered = c.submitted - timedelta(days=1)
        else:
            entered = c.dos + timedelta(days=rng.randint(0, 2))
        doc.charge_rows.append({
            "charge_id": f"SYNCH{ref[5:]}", "visit_id": ref, "cpt": ln.cpt, "units": ln.units,
            "entered_date": entered.isoformat(),
        })  # fmt: skip
        if kind == "charge_lag":
            doc.truth_rows.append(_truth(ref, kind, f"entered {(entered - c.dos).days}d after service", Decimal("0")))
        elif kind in ("missing_note", "unsigned_note"):
            doc.truth_rows.append(_truth(ref, kind, "", Decimal("0")))

    for v in visits:  # planted unbilled visits: a complete, signed note and no charge
        doc.visit_rows.append({
            "visit_id": v.visit_id, "payer_id": v.payer.payer_id, "provider_npi": v.provider_npi,
            "patient_ref": v.patient.ref, "dos": v.dos.isoformat(), "cpt": v.cpt, "units": v.units,
        })  # fmt: skip
        note_date = v.dos
        doc.note_rows.append({
            "visit_id": v.visit_id, "note_date": note_date.isoformat(),
            "signed_date": (note_date + timedelta(days=1)).isoformat(), "minutes": "",
            "elements": ",".join(REQUIRED[group_of(v.cpt)]),
        })  # fmt: skip
        if (as_of - v.dos).days >= MISSED_CHARGE_MIN_AGE:
            doc.truth_rows.append(_truth(v.visit_id, "missed_charge", "", money(v.expected_pay)))
    return doc


def _truth(ref: str, defect: str, detail: str, amount: Decimal) -> dict:
    return {"visit_id": ref, "defect": defect, "detail": detail, "expected_amount": f"{amount:.2f}"}
