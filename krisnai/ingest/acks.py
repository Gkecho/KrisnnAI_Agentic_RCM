"""999 implementation acknowledgements and 277CA claim acknowledgements."""

from __future__ import annotations

from krisnai.ingest.records import Ack277Rec, Ack999Rec
from krisnai.ingest.x12 import Transaction, X12Error, money, x12_date


def parse_999(tx: Transaction) -> list[Ack999Rec]:
    """One record per acknowledged transaction set (AK2 ... IK5)."""
    acked_gs06 = ""
    current: dict | None = None
    done: list[dict] = []
    group_status = None
    for seg in tx.segments:
        if seg.id == "AK1":
            acked_gs06 = seg[2]
        elif seg.id == "AK2":
            current = {"set": seg[1], "st02": seg[2], "errors": []}
        elif seg.id in ("IK3", "IK4") and current is not None:
            code = seg[3] if seg.id == "IK4" else seg[4]
            if code:
                current["errors"].append(f"{seg.id}:{code}")
        elif seg.id == "IK5" and current is not None:
            current["status"] = seg[1]
            current["errors"] += [f"IK5:{c}" for c in seg.els[2:] if c]
            done.append(current)
            current = None
        elif seg.id == "AK9":
            group_status = seg[1] or None
    if not done:
        raise X12Error("999 has no AK2/IK5 acknowledgement")
    return [
        Ack999Rec(
            acked_gs06=acked_gs06,
            acked_st02=d["st02"],
            transaction_set=d["set"],
            transaction_status=d["status"],
            group_status=group_status,
            error_codes=",".join(d["errors"]) or None,
        )
        for d in done
    ]


def parse_277ca(tx: Transaction) -> list[Ack277Rec]:
    """One record per STC status line, tied to the claim named by the TRN before it."""
    out: list[Ack277Rec] = []
    claim_id = None
    payer_claim = None
    for seg in tx.segments:
        if seg.id == "HL":
            claim_id = payer_claim = None
        elif seg.id == "TRN":
            claim_id = seg[2]
        elif seg.id == "REF" and seg[1] == "1K":
            payer_claim = seg[2]
            for rec in out:
                if rec.claim_submitter_id == claim_id and rec.payer_claim_number is None:
                    rec.payer_claim_number = payer_claim
        elif seg.id == "STC":
            if not claim_id:
                raise X12Error("277CA STC before any TRN claim reference")
            out.append(
                Ack277Rec(
                    claim_submitter_id=claim_id,
                    status_category=seg.comp(1, 1),
                    status_code=seg.comp(1, 2) or None,
                    entity_code=seg.comp(1, 3) or None,
                    status_date=x12_date(seg[2], "277CA STC02") if seg[2] else None,
                    total_charge=money(seg[4], "277CA STC04") if seg[4] else None,
                    payer_claim_number=payer_claim,
                )
            )
    if not out:
        raise X12Error("277CA has no STC status lines")
    return out
