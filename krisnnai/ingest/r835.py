"""835 (005010X221A1) remittance parser."""

from __future__ import annotations

from krisnnai.ingest.hashing import patient_hash
from krisnnai.ingest.records import (
    AdjustmentRec,
    PaymentRec,
    PlbRec,
    RemitLineRec,
    RemitRec,
)  # fmt: skip
from krisnnai.ingest.x12 import Segment, Transaction, X12Error, money, x12_date


def _adjustments(seg: Segment, where: str) -> list[AdjustmentRec]:
    """CAS01 group, then repeating (reason, amount, quantity) triplets."""
    out = []
    i = 2
    while i < len(seg.els):
        reason = seg[i]
        if not reason:
            break
        amount = money(seg[i + 1], f"{where} CAS{i + 1:02d}")
        qty = money(seg[i + 2], f"{where} CAS{i + 2:02d}") if seg[i + 2] else None
        out.append(AdjustmentRec(seg[1], reason, amount, qty))
        i += 3
    return out


def parse(tx: Transaction, salt: str) -> tuple[PaymentRec, list[RemitRec]]:
    payment: PaymentRec | None = None
    remits: list[RemitRec] = []
    remit: RemitRec | None = None
    line: RemitLineRec | None = None
    bpr = trn = None
    payer = {"code": "", "name": ""}
    plb_seq = 0
    plbs: list[PlbRec] = []

    for seg in tx.segments:
        sid = seg.id
        where = f"835 {sid}"
        if sid == "BPR":
            bpr = seg
        elif sid == "TRN" and remit is None:
            trn = seg
        elif sid == "N1" and seg[1] == "PR":
            payer = {"code": seg[4], "name": seg[2]}
        elif sid == "CLP":
            remit, line = None, None
            if not seg[1]:
                raise X12Error("835 CLP01 is empty")
            remit = RemitRec(
                claim_submitter_id=seg[1],
                status_code=seg[2],
                total_charge=money(seg[3], f"{where} CLP03"),
                total_paid=money(seg[4], f"{where} CLP04"),
                patient_responsibility=money(seg[5] or "0", f"{where} CLP05"),
                filing_indicator=seg[6] or None,
                payer_claim_control_number=seg[7],
                patient_hash=None,
                service_date=None,
            )
            remits.append(remit)
        elif sid == "PLB":  # trailer: follows the last claim
            ref, fiscal = seg[1], x12_date(seg[2], "PLB02")
            for i in range(3, len(seg.els) - 1, 2):
                if not seg[i]:
                    break
                plb_seq += 1
                plbs.append(
                    PlbRec(
                        plb_seq,
                        ref,
                        fiscal,
                        seg.comp(i, 1),
                        seg.comp(i, 2) or None,
                        money(seg[i + 1], f"{where} PLB{i + 1:02d}"),
                    )  # fmt: skip
                )
        elif remit is None:
            continue
        elif sid == "NM1" and seg[1] == "QC":
            member = seg[9] or f"{seg[3]}|{seg[4]}"
            remit.patient_hash = patient_hash(salt, member)
        elif sid == "DTM" and seg[1] == "232" and line is None:
            remit.service_date = x12_date(seg[2], f"{where} DTM02")
        elif sid == "SVC":
            line = RemitLineRec(
                line_number=len(remit.lines) + 1,
                cpt=seg.comp(1, 2),
                modifiers=[m for m in (seg.comp(1, j) for j in range(3, 7)) if m],
                charge=money(seg[2], f"{where} SVC02"),
                paid=money(seg[3] or "0", f"{where} SVC03"),
                units=money(seg[5], f"{where} SVC05") if seg[5] else None,
                allowed=None,
                service_date=None,
            )
            remit.lines.append(line)
        elif sid == "DTM" and seg[1] == "472" and line is not None:
            line.service_date = x12_date(seg[2], f"{where} DTM02")
        elif sid == "AMT" and seg[1] == "B6" and line is not None:
            line.allowed = money(seg[2], f"{where} AMT02")
        elif sid == "CAS":
            (line or remit).adjustments.extend(_adjustments(seg, where))
        elif sid == "LQ" and seg[1] == "HE":
            (line or remit).remarks.append((seg[1], seg[2]))

    if bpr is None:
        raise X12Error("835 has no BPR segment")
    if trn is None:
        raise X12Error("835 has no TRN segment")
    payment = PaymentRec(
        trace_number=trn[2],
        amount=money(bpr[2], "835 BPR02"),
        credit_debit=bpr[3],
        method=bpr[4],
        payment_date=x12_date(bpr[16], "835 BPR16"),
        payer_code=payer["code"],
        payer_name=payer["name"],
        plb=plbs,
    )
    return payment, remits
