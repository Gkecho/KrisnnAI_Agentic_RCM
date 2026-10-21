"""Write 837P, 999, 277CA and 835 text for simulated claims, in the shapes the ingest parsers already read.

The envelope and segment layout follow tests/fixtures/make_synthetic.py (kept separate so that module stays untouched).
Everything is fabricated: the clinic, its address, tax id and billing NPI are placeholders.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from krisnai.synthea.types import PayerInfo, SimClaim

CLINIC = "SYNTHETIC CLINIC"
BILLING_NPI = "1888888800"
TAX_ID = "999999999"
SENDER = "SYNSENDER"

DENIAL_RARC = {  # CARC -> a plausible RARC, purely synthetic pairing
    "16": "MA130", "18": "N522", "50": "N115", "97": "N19", "27": "N30", "31": "N382", "197": "N54", "4": "N519",
}  # fmt: skip

# CARCs the simulator can plant that are not in the random draw above
# (96, 22 and 29: the live payer network; synthetic pairing)
EXTRA_RARC = {"185": "N290", "96": "N130", "22": "MA04", "29": "N211"}


def _seg(*elements: object) -> str:
    parts = [str(e) for e in elements]
    while parts and parts[-1] == "":
        parts.pop()
    return "*".join(parts)


def _amt(value: Decimal) -> str:
    text = f"{value:.2f}"
    return text[:-3] if text.endswith(".00") else text


def _envelope(gs_code, gs_version, st_code, st_version, body, ctrl, sender, receiver, when: date) -> str:
    isa = _seg(
        "ISA", "00", " " * 10, "00", " " * 10, "ZZ", sender.ljust(15), "ZZ", receiver.ljust(15),
        when.strftime("%y%m%d"), "1200", "^", "00501", f"{ctrl:09d}", "0", "T", ":",
    )  # fmt: skip
    gs = _seg("GS", gs_code, sender, receiver, when.strftime("%Y%m%d"), "1200", ctrl, "X", gs_version)
    st = _seg("ST", st_code, "0001", st_version)
    se = _seg("SE", len(body) + 2, "0001")
    segs = [isa, gs, st, *body, se, _seg("GE", 1, ctrl), _seg("IEA", 1, f"{ctrl:09d}")]
    return "".join(s + "~\n" for s in segs)


def write_837(payer: PayerInfo, claims: list[SimClaim], ctrl: int, when: date) -> str:
    body = [
        _seg("BHT", "0019", "00", f"SYN837{ctrl}", when.strftime("%Y%m%d"), "1200", "CH"),
        _seg("NM1", "41", "2", CLINIC, "", "", "", "", "46", SENDER),
        _seg("PER", "IC", "SYNTHETIC BILLING", "TE", "5550000000"),
        _seg("NM1", "40", "2", payer.name, "", "", "", "", "46", payer.payer_id),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "85", "2", CLINIC, "", "", "", "", "XX", BILLING_NPI),
        _seg("N3", "100 SYNTHETIC WAY"),
        _seg("N4", "TESTVILLE", "TX", "750010000"),
        _seg("REF", "EI", TAX_ID),
    ]
    for hl, c in enumerate(claims, start=2):
        p = c.patient
        body += [
            _seg("HL", hl, 1, "22", 0),
            _seg("SBR", "P", "18", "", "", "", "", "", "", "CI"),
            _seg("NM1", "IL", "1", p.last, p.first, "", "", "", "MI", p.ref),
            _seg("N3", "100 SYNTHETIC WAY"),
            _seg("N4", "TESTVILLE", "TX", "750010000"),
            _seg("DMG", "D8", p.dob.strftime("%Y%m%d"), p.sex),
            _seg("NM1", "PR", "2", payer.name, "", "", "", "", "PI", payer.payer_id),
            _seg("CLM", c.claim_id, _amt(c.billed), "", "", "11:B:1", "Y", "A", "Y", "Y"),
            _seg("HI", *[("ABK" if i == 0 else "ABF") + ":" + dx for i, dx in enumerate(c.dx)]),
            _seg("NM1", "82", "1", "SYNRENDER", "SYNPROV", "", "", "", "XX", c.provider_npi),
        ]
        for n, ln in enumerate(c.lines, start=1):
            body += [
                _seg("LX", n),
                _seg("SV1", f"HC:{ln.cpt}", _amt(ln.billed), "UN", ln.units, "", "", "1"),
                _seg("DTP", "472", "D8", c.dos.strftime("%Y%m%d")),
            ]
    return _envelope("HC", "005010X222A1", "837", "005010X222A1", body, ctrl, SENDER, payer.payer_id, when)


def write_999(payer: PayerInfo, ctrl_837: int, ctrl: int, when: date) -> str:
    body = [
        _seg("AK1", "HC", ctrl_837, "005010X222A1"),
        _seg("AK2", "837", "0001", "005010X222A1"),
        _seg("IK5", "A"),
        _seg("AK9", "A", 1, 1, 1),
    ]
    return _envelope("FA", "005010X231A1", "999", "005010X231A1", body, ctrl, payer.payer_id, SENDER, when)


def write_277ca(payer: PayerInfo, claims: list[SimClaim], ctrl: int, when: date) -> str:
    body = [
        _seg("BHT", "0085", "08", f"SYN277{ctrl}", when.strftime("%Y%m%d"), "1200", "TH"),
        _seg("HL", 1, "", "20", 1),
        _seg("NM1", "PR", "2", payer.name, "", "", "", "", "PI", payer.payer_id),
        _seg("HL", 2, 1, "21", 1),
        _seg("NM1", "41", "2", CLINIC, "", "", "", "", "46", SENDER),
        _seg("HL", 3, 2, "19", 1),
        _seg("NM1", "85", "2", CLINIC, "", "", "", "", "XX", BILLING_NPI),
    ]
    for hl, c in enumerate(claims, start=4):
        status = "A3:21:PR" if c.scenario == "rejection" else "A2:20:PR"  # A3 = returned / rejected
        p = c.patient
        body += [
            _seg("HL", hl, 3, "22", 0),
            _seg("NM1", "IL", "1", p.last, p.first, "", "", "", "MI", p.ref),
            _seg("TRN", "2", c.claim_id),
            _seg("STC", status, when.strftime("%Y%m%d"), "WQ", _amt(c.billed)),
            _seg("REF", "1K", c.payer_claim_no),
            _seg("DTP", "472", "D8", c.dos.strftime("%Y%m%d")),
        ]
    return _envelope("HN", "005010X214", "277", "005010X214", body, ctrl, payer.payer_id, SENDER, when)


def write_835(payer: PayerInfo, remit_date: date, claims: list[SimClaim], ctrl: int) -> str:
    total = sum((c.paid for c in claims), Decimal("0"))
    ymd = remit_date.strftime("%Y%m%d")
    body = [
        _seg("BPR", "I", _amt(total), "C", "ACH", "CCP", "01", "999999999", "DA", "000000001",
             "1999999999", "", "01", "999999999", "DA", "000000002", ymd),
        _seg("TRN", "1", f"TRC{payer.payer_id[-4:]}{ymd}", "1999999999"),
        _seg("DTM", "405", ymd),
        _seg("N1", "PR", payer.name, "PI", payer.payer_id),
        _seg("N1", "PE", CLINIC, "XX", BILLING_NPI),
    ]  # fmt: skip
    for n, c in enumerate(claims, start=1):
        denied = c.scenario in ("denial", "timely_filing")
        p = c.patient
        body += [
            _seg("LX", n),
            _seg("CLP", c.claim_id, 4 if denied else 1, _amt(c.billed), _amt(c.paid),
                 _amt(c.pr), "12", c.payer_claim_no, "11", 1),
            _seg("NM1", "QC", "1", p.last, p.first, "", "", "", "MI", p.ref),
            _seg("DTM", "232", c.dos.strftime("%Y%m%d")),
        ]  # fmt: skip
        for ln in c.lines:
            body.append(_seg("SVC", f"HC:{ln.cpt}", _amt(ln.billed), _amt(ln.paid), "", ln.units))
            body.append(_seg("DTM", "472", c.dos.strftime("%Y%m%d")))
            for group in ("CO", "PR"):
                items = [(r, a) for g, r, a in ln.cas if g == group and a != 0]
                if items:
                    flat = [x for r, a in items for x in (r, _amt(a))]
                    body.append(_seg("CAS", group, *flat))
            body.append(_seg("AMT", "B6", _amt(Decimal("0") if denied else ln.allowed)))
            if c.scenario == "denial":
                body.append(_seg("LQ", "HE", DENIAL_RARC.get(c.carc) or EXTRA_RARC[c.carc]))
    return _envelope("HP", "005010X221A1", "835", "005010X221A1", body, ctrl, payer.payer_id, SENDER, remit_date)
