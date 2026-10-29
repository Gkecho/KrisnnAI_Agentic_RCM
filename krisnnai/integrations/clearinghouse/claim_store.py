"""What the practice's own extract knows about its claims: the raw 837s, the 277CA and 835 answers, the appointments.

A bot that sends a 270, a 276 or a corrected 837 needs the member id and the full claim. Our database deliberately
keeps only salted hashes, so the bot reads the practice's own files (the PM / clearinghouse extract the daily loader
already receives), exactly as a real bot would read the PM system. Nothing here is written back anywhere.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from krisnnai.ingest.x12 import X12Error, read_transactions, x12_date


@dataclass
class StoredLine:
    cpt: str
    billed: Decimal
    units: str


@dataclass
class StoredClaim:
    claim_id: str
    payer_id: str
    payer_name: str
    member_id: str
    last: str
    first: str
    dob: str  # YYYYMMDD
    sex: str
    billed: Decimal
    dos: date | None
    dx: list[str] = field(default_factory=list)
    rendering_npi: str = ""
    lines: list[StoredLine] = field(default_factory=list)


@dataclass
class Adjudication:
    """Latest known answer for a claim: rejected by the 277CA, or adjudicated on an 835."""

    state: str  # rejected | paid | denied | pending
    status_code: str = ""
    paid: Decimal = Decimal(0)
    payer_claim_no: str = ""


@dataclass
class PmExtract:
    claims: dict[str, StoredClaim] = field(default_factory=dict)
    answers: dict[str, Adjudication] = field(default_factory=dict)
    appointments: dict[str, dict] = field(default_factory=dict)  # appointment_id -> csv row

    def find_appointment(self, payer_id: str, member_id: str, dos: date) -> dict | None:
        key = (payer_id, member_id, dos.isoformat())
        return self._appt_index().get(key)

    def _appt_index(self) -> dict:
        if not hasattr(self, "_idx"):
            self._idx = {(a["payer_id"], a["patient_ref"], a["appt_date"]): a for a in self.appointments.values()}
        return self._idx


def _scan_837(text: str, out: dict[str, StoredClaim]) -> None:
    for tx in read_transactions(text):
        if tx.st01 != "837":
            continue
        payer_id = payer_name = ""
        member = last = first = dob = sex = ""
        cur: StoredClaim | None = None
        for seg in tx.segments:
            sid = seg.id
            if sid == "NM1" and seg[1] == "PR":
                payer_name, payer_id = seg[3], seg[9]
            elif sid == "NM1" and seg[1] == "IL":
                last, first, member = seg[3], seg[4], seg[9]
                dob = sex = ""
            elif sid == "DMG":
                dob, sex = seg[2], seg[3]
            elif sid == "CLM":
                cur = StoredClaim(seg[1], payer_id, payer_name, member, last, first, dob, sex,
                                  Decimal(seg[2] or "0"), None)  # fmt: skip
                out[cur.claim_id] = cur
            elif cur is None:
                continue
            elif sid == "HI":
                cur.dx = [seg.comp(i, 2) for i in range(1, len(seg.els)) if seg.comp(i, 2)]
            elif sid == "NM1" and seg[1] == "82":
                cur.rendering_npi = seg[9]
            elif sid == "SV1":
                cur.lines.append(StoredLine(seg.comp(1, 2), Decimal(seg[2] or "0"), seg[4] or "1"))
            elif sid == "DTP" and seg[1] == "472":
                cur.dos = x12_date(seg[3], "837 DTP*472")


def _scan_835(text: str, out: dict[str, Adjudication]) -> None:
    for tx in read_transactions(text):
        if tx.st01 != "835":
            continue
        for seg in tx.segments:
            if seg.id == "CLP":
                code = seg[2]
                state = "denied" if code == "4" else "paid"
                out[seg[1]] = Adjudication(state, code, Decimal(seg[4] or "0"), seg[7])


def _scan_277ca(text: str, out: dict[str, Adjudication]) -> None:
    for tx in read_transactions(text):
        if tx.st01 != "277":
            continue
        claim = ""
        for seg in tx.segments:
            if seg.id == "TRN" and seg[1] == "2":
                claim = seg[2]
            elif seg.id == "STC" and claim:
                category = seg.comp(1, 1)
                if category.startswith("A3") or category.startswith("A4"):
                    out.setdefault(claim, Adjudication("rejected", seg.comp(1, 2)))


def load_extract(folder: Path) -> PmExtract:
    """Scan a folder (searched recursively) of the practice's own files."""
    ex = PmExtract()
    adjudicated: dict[str, Adjudication] = {}
    rejected: dict[str, Adjudication] = {}
    for p in sorted(folder.rglob("*")):
        if not p.is_file():
            continue
        name = p.name.lower()
        try:
            if p.suffix.lower() == ".csv" and "appoint" in name:
                with p.open(encoding="utf-8-sig") as f:
                    for r in csv.DictReader(f):
                        ex.appointments[r["appointment_id"]] = r
            elif p.suffix.lower() in (".x12", ".edi", ".txt"):
                text = p.read_text(encoding="utf-8", errors="ignore")
                if name.startswith("837"):
                    _scan_837(text, ex.claims)
                elif name.startswith("835"):
                    _scan_835(text, adjudicated)
                elif name.startswith("277ca"):
                    _scan_277ca(text, rejected)
        except (X12Error, KeyError, ValueError):
            continue  # a bad file is the loader's business; the bot just does not learn from it
    ex.answers = {**rejected, **adjudicated}  # an 835 supersedes an earlier rejection (a corrected claim was paid)
    return ex
