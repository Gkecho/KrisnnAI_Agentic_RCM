"""Turn Synthea claims into billable bundles (one per professional claim) and say what could not be billed."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

from krisnai.synthea.crosswalk import CONDITION_ICD10, EM_BY_CLASS, FALLBACK_ICD10, PROCEDURE_CPT
from krisnai.synthea.reader import SyntheaData
from krisnai.synthea.types import Bundle, PayerInfo, Person

BILLING_PROVIDERS = tuple(f"18888888{n:02d}" for n in range(5))
MAX_EXTRA_LINES = 2
MAX_DX = 3
MAX_CLAIM_LINES = 4
MAX_CLAIM_DX = 4
NO_COVERAGE = {"NO_INSURANCE", "NONE", ""}
X12_BAD = re.compile(r"[^A-Za-z0-9 .\-]")


def _digest(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)


def _clean(text: str, fallback: str) -> str:
    return X12_BAD.sub("", text).strip().upper() or fallback


def _day(text: str) -> date | None:
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def payer_infos(data: SyntheaData) -> dict[str, PayerInfo]:
    """Synthea payer id -> simulated payer. Behaviour (fee level, days to pay) is a stable function of the name."""
    out: dict[str, PayerInfo] = {}
    for row in data.payers:
        name = row.get("name", "")
        if name.upper() in NO_COVERAGE or not row.get("id"):
            continue
        h = _digest(name)
        out[row["id"]] = PayerInfo(
            payer_id="SYN" + re.sub(r"[^A-Z0-9]", "", name.upper())[:9],
            name=_clean(name, "SYNTHEA PAYER"),
            fee_multiplier=Decimal(85 + h % 31) / 100,  # 0.85 .. 1.15
            pay_days=18 + (h >> 8) % 33,  # 18 .. 50
        )
    return out


def _em_code(klass: str, enc_id: str, age: int) -> str | None:
    options = EM_BY_CLASS.get(klass)
    if not options:
        return None
    if klass == "wellness":
        return options[0] if age < 40 else options[-1]
    return options[_digest(enc_id) % len(options)]


LOOKBACK_DAYS = 548  # Synthea writes a whole lifetime of claims; a practice has about 18 months of open work


def build_bundles(
    data: SyntheaData, as_of: date, lookback_days: int = LOOKBACK_DAYS
) -> tuple[list[Bundle], dict[str, int]]:
    """Return (bundles sorted by date of service, build report).

    Claims dated after `as_of`, or more than `lookback_days` before it, are dropped (and counted).
    """
    report: Counter = Counter()
    since = as_of - timedelta(days=lookback_days)
    payers = payer_infos(data)
    patients = {p["id"]: p for p in data.patients}
    encounters = {e["id"]: e for e in data.encounters}
    charge_codes: dict[str, list[str]] = {}
    for t in data.claims_transactions:
        if t.get("type", "").upper() == "CHARGE" and t.get("procedurecode"):
            charge_codes.setdefault(t.get("claimid", ""), []).append(t["procedurecode"])

    people: dict[str, Person] = {}
    pending: list[tuple[date, str, Bundle]] = []
    for c in data.claims:
        report["claims_read"] += 1
        enc = encounters.get(c.get("appointmentid", ""), {})
        payer = payers.get(enc.get("payer", "")) or payers.get(c.get("primarypatientinsuranceid", ""))
        if payer is None:
            report["skipped_no_coverage"] += 1
            continue
        pat = patients.get(c.get("patientid", ""))
        dos = _day(c.get("servicedate", "")) or _day(enc.get("start", ""))
        if pat is None or dos is None:
            report["skipped_incomplete"] += 1
            continue
        if dos > as_of:
            report["skipped_after_as_of"] += 1
            continue
        if dos < since:
            report["skipped_before_window"] += 1
            continue
        dob = _day(pat.get("birthdate", "")) or date(1970, 1, 1)
        age = dos.year - dob.year
        em = _em_code(enc.get("encounterclass", "").lower(), enc.get("id", c["id"]), age)
        if em is None:
            report["skipped_not_professional"] += 1
            continue

        cpts = [(em, 1)]
        for code in charge_codes.get(c["id"], []):
            cpt = PROCEDURE_CPT.get(code)
            if cpt and cpt not in {x for x, _ in cpts} and len(cpts) <= MAX_EXTRA_LINES:
                cpts.append((cpt, 1))
        report["procedure_lines_mapped"] += len(cpts) - 1
        report["procedure_codes_unmapped"] += sum(1 for x in charge_codes.get(c["id"], []) if x not in PROCEDURE_CPT)

        dx: list[str] = []
        for n in range(1, 9):
            icd = CONDITION_ICD10.get(c.get(f"diagnosis{n}", ""))
            if icd and icd not in dx and len(dx) < MAX_DX:
                dx.append(icd)
        if not dx:
            dx, report["dx_fallback"] = [FALLBACK_ICD10], report["dx_fallback"] + 1

        pid = c.get("patientid", "")
        if pid not in people:
            people[pid] = Person(
                ref=f"SYNM{len(people) + 1:06d}", last=_clean(pat.get("last", ""), "SYNLAST"),
                first=_clean(pat.get("first", ""), "SYNFIRST"), dob=dob,
                sex="F" if pat.get("gender", "").upper().startswith("F") else "M",
            )  # fmt: skip
        pending.append((dos, c["id"], Bundle(
            claim_id="", synthea_id=c["id"], payer=payer, patient=people[pid],
            provider_npi=BILLING_PROVIDERS[_digest(c.get("providerid", "")) % len(BILLING_PROVIDERS)],
            dos=dos, dx=dx, cpts=cpts,
        )))  # fmt: skip

    # Synthea records several encounters for one patient on one day; a practice bills that as one claim
    merged: dict[tuple, tuple[date, str, Bundle]] = {}
    for dos, cid, b in sorted(pending, key=lambda x: (x[0], x[1])):
        key = (b.patient.ref, dos, b.payer.payer_id)
        if key not in merged:
            merged[key] = (dos, cid, b)
            continue
        first = merged[key][2]
        report["merged_same_day"] += 1
        have = {x for x, _ in first.cpts}
        first.cpts += [(x, u) for x, u in b.cpts if x not in have and len(first.cpts) < MAX_CLAIM_LINES]
        first.dx += [d for d in b.dx if d not in first.dx and len(first.dx) < MAX_CLAIM_DX]
    pending = list(merged.values())
    pending.sort(key=lambda x: (x[0], x[1]))
    bundles = []
    for n, (_, _, b) in enumerate(pending, start=1):
        b.claim_id = f"SYNC{n:06d}"
        bundles.append(b)
    report["bundles"] = len(bundles)
    return bundles, dict(report)
