"""A tiny, hand-made folder shaped like Synthea's CSV exporter output (same file and column names), no real data.

Used to test the importer and the payer simulator without Java or Docker. `write(out_dir, n_claims, seed)` is
deterministic. A real Synthea run is a manual verification step.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

PAYERS = [("pay-medicare", "Medicare"), ("pay-aetna", "Aetna"), ("pay-humana", "Humana"), ("pay-none", "NO_INSURANCE")]
CLASSES = ["ambulatory"] * 5 + ["wellness"] * 2 + ["urgentcare", "emergency", "inpatient", "home"]
CONDITIONS = ["59621000", "44054006", "195662009", "10509002", "999999999", ""]  # last two are unmapped / blank
PROCEDURES = ["399208008", "29303009", "73761001", "123456789"]  # last one is unmapped
FIRST_DAY = date(2025, 3, 1)
LAST_DAY = date(2026, 6, 20)


def _write(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def write(out_dir: Path, n_claims: int = 400, seed: int = 11, n_patients: int = 60) -> Path:
    rng = random.Random(seed)
    csv_dir = out_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    patients = [
        {"id": f"pat-{i:04d}", "birthdate": (date(1940, 1, 1) + timedelta(days=rng.randint(0, 27000))).isoformat(),
         "first": f"Test{i}", "last": f"Person{i}", "gender": rng.choice("MF")}
        for i in range(n_patients)
    ]  # fmt: skip
    encounters, claims, transactions = [], [], []
    for n in range(n_claims):
        pat = rng.choice(patients)
        payer = rng.choice(PAYERS)
        klass = rng.choice(CLASSES)
        dos = FIRST_DAY + timedelta(days=rng.randint(0, (LAST_DAY - FIRST_DAY).days))
        enc_id, claim_id = f"enc-{n:05d}", f"clm-{n:05d}"
        encounters.append({"id": enc_id, "start": f"{dos}T09:00:00Z", "patient": pat["id"], "payer": payer[0],
                           "encounterclass": klass, "code": "185349003"})  # fmt: skip
        claim = {"id": claim_id, "patientid": pat["id"], "providerid": f"prov-{rng.randint(1, 4)}",
                 "servicedate": f"{dos}T09:00:00Z", "appointmentid": enc_id}  # fmt: skip
        for k in range(1, 9):
            claim[f"diagnosis{k}"] = rng.choice(CONDITIONS) if k <= 3 else ""
        claims.append(claim)
        for code in rng.sample(PROCEDURES, rng.randint(0, 2)):
            transactions.append({"id": f"t-{len(transactions)}", "claimid": claim_id, "type": "CHARGE",
                                 "procedurecode": code, "amount": "100.00"})  # fmt: skip
        transactions.append({"id": f"t-{len(transactions)}", "claimid": claim_id, "type": "PAYMENT",
                             "procedurecode": "", "amount": "50.00"})  # fmt: skip
    _write(csv_dir / "patients.csv", ["id", "birthdate", "first", "last", "gender"], patients)
    _write(csv_dir / "encounters.csv", ["id", "start", "patient", "payer", "encounterclass", "code"], encounters)
    _write(csv_dir / "claims.csv",
           ["id", "patientid", "providerid", "servicedate", "appointmentid"] + [f"diagnosis{k}" for k in range(1, 9)],
           claims)  # fmt: skip
    _write(csv_dir / "claims_transactions.csv", ["id", "claimid", "type", "procedurecode", "amount"], transactions)
    _write(csv_dir / "payers.csv", ["id", "name"], [{"id": i, "name": n} for i, n in PAYERS])
    return out_dir
