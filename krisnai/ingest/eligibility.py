"""271 eligibility responses (X12 005010X279A1), the subset the pre-visit clearance agent reads.

One record per subscriber loop (HL level 22). Benefit lines used: EB01 1 active, 6 inactive, R other or additional
payer (named by the NM1*PR that follows), B copayment (EB07), A coinsurance (EB08, a percent), C deductible with
EB06 29 = remaining (EB07). Plan dates come from DTP*346 (begin) and DTP*347 (end); DTP*291 is the date the answer
applies to; TRN*2 carries the trace number; the interchange date is when the answer was produced.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from krisnai.ingest.hashing import patient_hash
from krisnai.ingest.records import Elig271Rec
from krisnai.ingest.x12 import Transaction, X12Error, money, x12_date


def _percent(text: str) -> Decimal | None:
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise X12Error(f"271 EB08 is not a number: {text!r}") from None
    return value / 100 if value > 1 else value  # a payer may send 0.2 or 20


def parse_271(tx: Transaction, salt: str) -> list[Elig271Rec]:
    payer_code, payer_name = "", ""
    cur: dict | None = None
    out: list[dict] = []
    want_other = False
    for seg in tx.segments:
        sid = seg.id
        if sid == "NM1" and seg[1] == "PR" and cur is None:
            payer_name, payer_code = seg[3], seg[9]
        elif sid == "HL":
            if cur is not None:
                out.append(cur)
            cur = {"ref": "", "member": "", "service": None, "begin": None, "end": None, "active": None,
                   "other": None, "copay": None, "coins": None, "ded": None} if seg[3] == "22" else None  # fmt: skip
            want_other = False
        elif cur is None:
            continue
        elif sid == "TRN" and seg[1] == "2":
            cur["ref"] = seg[2]
        elif sid == "NM1" and seg[1] == "IL":
            cur["member"] = seg[9]
        elif sid == "NM1" and seg[1] == "PR" and want_other:
            cur["other"] = seg[3] or seg[9]
            want_other = False
        elif sid == "DTP":
            when = x12_date(seg[3], f"271 DTP*{seg[1]}")
            if seg[1] == "291":
                cur["service"] = when
            elif seg[1] == "346":
                cur["begin"] = when
            elif seg[1] == "347":
                cur["end"] = when
        elif sid == "EB":
            code = seg[1]
            if code == "1":
                cur["active"] = True
            elif code == "6":
                cur["active"] = False
            elif code == "R":
                want_other = True
            elif code == "B" and seg[7]:
                cur["copay"] = money(seg[7], "271 EB07 copayment")
            elif code == "A" and seg[8]:
                cur["coins"] = _percent(seg[8])
            elif code == "C" and seg[6] == "29" and seg[7]:
                cur["ded"] = money(seg[7], "271 EB07 deductible remaining")
    if cur is not None:
        out.append(cur)
    if not out:
        raise X12Error("271 has no subscriber loop (HL level 22)")
    recs = []
    for c in out:
        if not c["ref"] or not c["member"] or c["active"] is None:
            raise X12Error("271 subscriber needs TRN*2, NM1*IL member id and an EB 1 or 6 coverage line")
        recs.append(
            Elig271Rec(
                response_ref=c["ref"], payer_code=payer_code, payer_name=payer_name,
                patient_hash=patient_hash(salt, c["member"]), checked_on=tx.isa_date,
                service_date=c["service"], active=c["active"], plan_begin=c["begin"], plan_end=c["end"],
                other_payer=c["other"], copay=c["copay"], coinsurance=c["coins"], deductible_remaining=c["ded"],
            )
        )  # fmt: skip
    return recs
