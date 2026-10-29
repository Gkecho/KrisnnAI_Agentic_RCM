"""837P (005010X222A1) professional claim parser."""

from __future__ import annotations

from decimal import Decimal

from krisnnai.ingest.hashing import patient_hash
from krisnnai.ingest.records import ClaimLineRec, ClaimRec
from krisnnai.ingest.x12 import Transaction, X12Error, money, x12_date


def parse(tx: Transaction, salt: str) -> list[ClaimRec]:
    claims: list[ClaimRec] = []
    submitted_on = None
    provider = {"npi": "", "name": "", "tax_id": None}
    payer = {"code": "", "name": ""}
    member_id = ""
    claim: ClaimRec | None = None
    line: ClaimLineRec | None = None
    last_nm1 = ""

    def close() -> None:
        nonlocal claim, line
        if claim is not None:
            if claim.service_date is None:
                dates = [ln.service_date for ln in claim.lines if ln.service_date]
                claim.service_date = min(dates) if dates else None
            claims.append(claim)
        claim = line = None

    for seg in tx.segments:
        sid = seg.id
        where = f"837 {sid}"
        if sid == "BHT":
            submitted_on = x12_date(seg[4], "BHT04") if seg[4] else None
        elif sid == "HL":
            close()
            if seg[3] == "22":
                member_id = ""
        elif sid == "NM1":
            last_nm1 = seg[1]
            if seg[1] == "85":
                provider = {"npi": seg[9], "name": seg[3], "tax_id": None}
            elif seg[1] == "IL":
                member_id = seg[9]
            elif seg[1] == "PR":
                payer = {"code": seg[9], "name": seg[3]}
        elif sid == "REF":
            if seg[1] == "EI" and last_nm1 == "85" and claim is None:
                provider["tax_id"] = seg[2]
            elif seg[1] == "F8" and claim is not None and line is None:
                claim.payer_claim_control_number = seg[2]
        elif sid == "CLM":
            close()
            if not seg[1]:
                raise X12Error("837 CLM01 is empty")
            if not member_id:
                raise X12Error(f"837 claim {seg[1]} has no subscriber member id (NM1*IL)")
            claim = ClaimRec(
                claim_submitter_id=seg[1],
                total_charge=money(seg[2], f"{where} CLM02"),
                place_of_service=seg.comp(5, 1) or None,
                frequency_code=seg.comp(5, 3) or "1",
                payer_claim_control_number=None,
                service_date=None,
                submitted_on=submitted_on,
                payer_code=payer["code"],
                payer_name=payer["name"],
                provider_npi=provider["npi"],
                provider_name=provider["name"],
                tax_id=provider["tax_id"],
                patient_hash=patient_hash(salt, member_id),
            )
        elif claim is None:
            continue
        elif sid == "HI":
            for comp_el in range(1, len(seg.els)):
                qual, code = seg.comp(comp_el, 1), seg.comp(comp_el, 2)
                if code:
                    claim.dx.append((qual, code))
        elif sid == "LX":
            line = None
            number = int(seg[1]) if seg[1].isdigit() else len(claim.lines) + 1
            claim.lines.append(ClaimLineRec(number, "", [], Decimal("0"), Decimal("0"), "UN", None, None))
            line = claim.lines[-1]
        elif sid == "SV1":
            if line is None:
                raise X12Error(f"837 SV1 without LX in claim {claim.claim_submitter_id}")
            line.cpt = seg.comp(1, 2)
            line.modifiers = [m for m in (seg.comp(1, j) for j in range(3, 7)) if m]
            line.charge = money(seg[2], f"{where} SV102")
            line.unit_basis = seg[3] or "UN"
            line.units = money(seg[4] or "1", f"{where} SV104")
            line.dx_pointer = seg.comp(7, 1) or None
            if not line.cpt:
                raise X12Error(f"837 SV1 in claim {claim.claim_submitter_id} has no procedure code")
        elif sid == "DTP" and seg[1] in ("472", "431", "434"):
            d = x12_date(seg[3], f"{where} DTP03") if seg[2] == "D8" else None
            if line is not None and seg[1] == "472":
                line.service_date = d
            elif line is None and d is not None and claim.service_date is None:
                claim.service_date = d
    close()
    return claims
