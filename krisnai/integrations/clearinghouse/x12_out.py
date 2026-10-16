"""Build the transactions a bot sends (270, 276, corrected 837) and read the 277 status answer.

Envelopes and segment helpers come from the simulator's writers so everything the mock service returns is read by the
same parsers the daily loader uses. Members and names are whatever the practice's own extract holds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from krisnai.integrations.clearinghouse.claim_store import StoredClaim
from krisnai.ingest.x12 import X12Error, read_transactions
from krisnai.synthea.x12out import BILLING_NPI, CLINIC, SENDER, TAX_ID, _amt, _envelope, _seg


def write_270(payer_id: str, payer_name: str, member_id: str, last: str, first: str, dob: str, dos: date,
              ref: str, ctrl: int, when: date, npi: str = BILLING_NPI) -> str:  # fmt: skip
    """Eligibility inquiry for one subscriber and one date of service (general benefit inquiry, EQ*30)."""
    body = [
        _seg("BHT", "0022", "13", ref, when.strftime("%Y%m%d"), "1200"),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "PR", "2", payer_name, "", "", "", "", "PI", payer_id),
        _seg("HL", 2, 1, "21", 1),
        _seg("NM1", "1P", "2", CLINIC, "", "", "", "", "XX", npi),
        _seg("HL", 3, 2, "22", 0),
        _seg("TRN", "1", ref, SENDER.ljust(10, "0")[:10]),  # TRN-03 must be 10 characters
        _seg("NM1", "IL", "1", last, first, "", "", "", "MI", member_id),
        _seg("DMG", "D8", dob or "19700101"),
        _seg("DTP", "291", "D8", dos.strftime("%Y%m%d")),
        _seg("EQ", "30"),
    ]
    return _envelope("HS", "005010X279A1", "270", "005010X279A1", body, ctrl, SENDER, payer_id, when)


def write_276(claim: StoredClaim, payer_claim_no: str, ref: str, ctrl: int, when: date) -> str:
    """Claim status request for one claim, identified by the patient control number (TRN) and the subscriber."""
    dos = claim.dos or when
    body = [
        _seg("BHT", "0010", "13", ref, when.strftime("%Y%m%d"), "1200"),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "PR", "2", claim.payer_name, "", "", "", "", "PI", claim.payer_id),
        _seg("HL", 2, 1, "21", 1),
        _seg("NM1", "41", "2", CLINIC, "", "", "", "", "46", SENDER),
        _seg("HL", 3, 2, "19", 1),
        _seg("NM1", "1P", "2", CLINIC, "", "", "", "", "XX", BILLING_NPI),
        _seg("HL", 4, 3, "22", 0),
        _seg("DMG", "D8", claim.dob or "19700101", claim.sex or "U"),
        _seg("NM1", "IL", "1", claim.last, claim.first, "", "", "", "MI", claim.member_id),
        _seg("TRN", "1", claim.claim_id),
        _seg("REF", "1K", payer_claim_no) if payer_claim_no else "",
        _seg("AMT", "T3", _amt(claim.billed)),
        _seg("DTP", "472", "D8", dos.strftime("%Y%m%d")),
    ]
    return _envelope("HR", "005010X212", "276", "005010X212", [s for s in body if s], ctrl, SENDER, claim.payer_id, when)


def write_corrected_837(claim: StoredClaim, payer_claim_no: str, ctrl: int, when: date) -> str:
    """The claim again as a replacement (CLM05-3 = 7) that points at the payer's original claim number (REF*F8)."""
    dos = claim.dos or when
    body = [
        _seg("BHT", "0019", "00", f"SYN837R{ctrl}", when.strftime("%Y%m%d"), "1200", "CH"),
        _seg("NM1", "41", "2", CLINIC, "", "", "", "", "46", SENDER),
        _seg("PER", "IC", "SYNTHETIC BILLING", "TE", "5550000000"),
        _seg("NM1", "40", "2", claim.payer_name, "", "", "", "", "46", claim.payer_id),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "85", "2", CLINIC, "", "", "", "", "XX", BILLING_NPI),
        _seg("N3", "100 SYNTHETIC WAY"),
        _seg("N4", "TESTVILLE", "TX", "750010000"),
        _seg("REF", "EI", TAX_ID),
        _seg("HL", 2, 1, "22", 0),
        _seg("SBR", "P", "18", "", "", "", "", "", "", "CI"),
        _seg("NM1", "IL", "1", claim.last, claim.first, "", "", "", "MI", claim.member_id),
        _seg("N3", "100 SYNTHETIC WAY"),
        _seg("N4", "TESTVILLE", "TX", "750010000"),
        _seg("DMG", "D8", claim.dob or "19700101", claim.sex or "U"),
        _seg("NM1", "PR", "2", claim.payer_name, "", "", "", "", "PI", claim.payer_id),
        _seg("CLM", claim.claim_id, _amt(claim.billed), "", "", "11:B:7", "Y", "A", "Y", "Y"),
        _seg("REF", "F8", payer_claim_no),
        _seg("HI", *[("ABK" if i == 0 else "ABF") + ":" + dx for i, dx in enumerate(claim.dx)]) if claim.dx else "",
        _seg("NM1", "82", "1", "SYNRENDER", "SYNPROV", "", "", "", "XX", claim.rendering_npi or BILLING_NPI),
    ]
    for n, ln in enumerate(claim.lines, start=1):
        body += [
            _seg("LX", n),
            _seg("SV1", f"HC:{ln.cpt}", _amt(ln.billed), "UN", ln.units, "", "", "1"),
            _seg("DTP", "472", "D8", dos.strftime("%Y%m%d")),
        ]
    return _envelope("HC", "005010X222A1", "837", "005010X222A1", [s for s in body if s], ctrl, SENDER,
                     claim.payer_id, when)  # fmt: skip


# ----------------------------------------------------------------------------------------- mock answers


def write_277(payer_id: str, payer_name: str, claim_id: str, member: str, category: str, code: str,
              charge: Decimal, paid: Decimal, payer_claim_no: str, dos: date | None, ctrl: int, when: date) -> str:  # fmt: skip
    """The 277 claim status response (unsolicited-style single claim), STC01 = category:code:entity."""
    body = [
        _seg("BHT", "0010", "08", f"SYN277R{ctrl}", when.strftime("%Y%m%d"), "1200", "DG"),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "PR", "2", payer_name, "", "", "", "", "PI", payer_id),
        _seg("HL", 2, 1, "21", 1),
        _seg("NM1", "41", "2", CLINIC, "", "", "", "", "46", SENDER),
        _seg("HL", 3, 2, "19", 1),
        _seg("NM1", "1P", "2", CLINIC, "", "", "", "", "XX", BILLING_NPI),
        _seg("HL", 4, 3, "22", 0),
        _seg("NM1", "IL", "1", "", "", "", "", "", "MI", member),
        _seg("TRN", "2", claim_id),
        _seg("STC", f"{category}:{code}:PR", when.strftime("%Y%m%d"), "WQ", _amt(charge), _amt(paid)),
        _seg("REF", "1K", payer_claim_no) if payer_claim_no else "",
        _seg("DTP", "472", "D8", dos.strftime("%Y%m%d")) if dos else "",
    ]
    return _envelope("HN", "005010X212", "277", "005010X212", [s for s in body if s], ctrl, payer_id, SENDER, when)


@dataclass
class StatusAnswer:
    claim_id: str
    category: str  # A1/A2 accepted, A3/A4 rejected, P* pending, F1 paid, F2 denied, E* error
    code: str
    charge: Decimal
    paid: Decimal
    payer_claim_no: str


def parse_277_status(text: str) -> list[StatusAnswer]:
    out: list[StatusAnswer] = []
    for tx in read_transactions(text):
        if tx.st01 != "277":
            continue
        claim = ""
        pending: StatusAnswer | None = None
        for seg in tx.segments:
            if seg.id == "TRN" and seg[1] == "2":
                claim = seg[2]
            elif seg.id == "STC":
                pending = StatusAnswer(claim, seg.comp(1, 1), seg.comp(1, 2), Decimal(seg[4] or "0"),
                                       Decimal(seg[5] or "0"), "")  # fmt: skip
                out.append(pending)
            elif seg.id == "REF" and seg[1] == "1K" and pending is not None:
                pending.payer_claim_no = seg[2]
    if not out:
        raise X12Error("277 has no STC status segment")
    return out
