"""Load parsed files into events and the normalized tables, idempotently.

Order of work for one file: hash -> skip if this tenant already has it -> parse (no DB writes) ->
one transaction that writes source_file, events and normalized rows. A file that cannot be parsed
is recorded as `failed` with its reason and writes nothing else.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from krisnai.ingest import acks, eligibility, hashing, p837, r835
from krisnai.ingest.records import (
    Ack277Rec,
    Ack999Rec,
    ClaimRec,
    Elig271Rec,
    PaymentRec,
    RemitRec,
    to_json,
)  # fmt: skip
from krisnai.ingest.x12 import Transaction, X12Error, read_transactions
from krisnai.model import (
    Ack277Ca,
    Ack999,
    Adjustment,
    Appointment,
    Authorization,
    BankDeposit,
    Charge,
    Claim,
    ClaimDx,
    ClaimLine,
    EligibilityResponse,
    Event,
    FeeSchedule,
    PatientRef,
    Payer,
    Payment,
    PlbAdjustment,
    Posting,
    Provider,
    Remit,
    RemitLine,
    RemitRemark,
    SourceFile,
    Visit,
    VisitNote,
    tenant_session,
)  # fmt: skip

FILE_TYPES = {"837": "837P", "835": "835", "999": "999", "277": "277CA", "271": "271"}
CSV_NAME_HINTS = ("fee", "visit", "note", "charge", "appoint", "authoriz", "deposit", "posting")
X12_SUFFIXES = {".x12", ".edi", ".837", ".835", ".837p", ".999", ".277", ".277ca", ".txt"}


@dataclass
class IngestResult:
    path: str
    status: str  # loaded | skipped | failed
    file_type: str = ""
    reason: str = ""
    events: int = 0


class Lookups:
    """Get-or-create payer / provider / patient_ref rows for one file (tenant filter is automatic)."""

    def __init__(self, session: Session, source_file_id: int):
        self.s, self.sf = session, source_file_id
        self._payers: dict[str, int] = {}
        self._providers: dict[str, int] = {}
        self._patients: dict[bytes, int] = {}

    def payer(self, code: str, name: str) -> int:
        if code not in self._payers:
            row = self.s.scalars(select(Payer).where(Payer.payer_id_code == code)).first()
            if row is None:
                row = Payer(source_file_id=self.sf, payer_id_code=code, name=name or code)
                self.s.add(row)
                self.s.flush()
            self._payers[code] = row.id
        return self._payers[code]

    def provider(self, npi: str, name: str, tax_id: str | None) -> int:
        if npi not in self._providers:
            row = self.s.scalars(select(Provider).where(Provider.npi == npi)).first()
            if row is None:
                row = Provider(source_file_id=self.sf, npi=npi, name=name or npi, tax_id=tax_id)
                self.s.add(row)
                self.s.flush()
            self._providers[npi] = row.id
        return self._providers[npi]

    def patient(self, ref_hash: bytes | None) -> int | None:
        if ref_hash is None:
            return None
        if ref_hash not in self._patients:
            row = self.s.scalars(select(PatientRef).where(PatientRef.ref_hash == ref_hash)).first()
            if row is None:
                row = PatientRef(source_file_id=self.sf, ref_hash=ref_hash)
                self.s.add(row)
                self.s.flush()
            self._patients[ref_hash] = row.id
        return self._patients[ref_hash]


def parse_x12(text: str, salt: str) -> tuple[str, list[tuple[Transaction, str, list]]]:
    """Parse every transaction. Returns (file_type, [(transaction, event_type, records)])."""
    out = []
    kinds = set()
    for tx in read_transactions(text):
        kind = FILE_TYPES.get(tx.st01)
        if kind is None:
            raise X12Error(f"unsupported transaction set {tx.st01}")
        kinds.add(kind)
        if kind == "837P":
            claims = p837.parse(tx, salt)
            if not claims:
                raise X12Error("837 transaction contains no claims")
            out.append((tx, "837P.claim", claims))
        elif kind == "835":
            payment, remits = r835.parse(tx, salt)
            out.append((tx, "835", [payment, *remits]))
        elif kind == "999":
            out.append((tx, "999.ack", acks.parse_999(tx)))
        elif kind == "271":
            out.append((tx, "271.response", eligibility.parse_271(tx, salt)))
        else:
            out.append((tx, "277CA.claim_status", acks.parse_277ca(tx)))
    return "+".join(sorted(kinds)), out


def _event(s: Session, sf: int, tx: Transaction, seq: int, event_type: str, rec) -> Event:
    ev = Event(
        source_file_id=sf, event_type=event_type, isa13=tx.isa13, gs06=tx.gs06, st02=tx.st02,
        seq_in_file=seq, known_at=datetime.combine(tx.isa_date, datetime.min.time()),
        payload=to_json(rec),
    )  # fmt: skip
    s.add(ev)
    s.flush()
    return ev


def _write_claim(s: Session, sf: int, ev: Event, rec: ClaimRec, lk: Lookups) -> None:
    claim = Claim(
        source_file_id=sf, event_id=ev.id,
        payer_id=lk.payer(rec.payer_code, rec.payer_name),
        provider_id=lk.provider(rec.provider_npi, rec.provider_name, rec.tax_id),
        patient_ref_id=lk.patient(rec.patient_hash),
        claim_submitter_id=rec.claim_submitter_id, total_charge=rec.total_charge,
        place_of_service=rec.place_of_service, frequency_code=rec.frequency_code,
        payer_claim_control_number=rec.payer_claim_control_number,
        service_date=rec.service_date, submitted_on=rec.submitted_on,
    )  # fmt: skip
    s.add(claim)
    s.flush()
    for i, (qual, code) in enumerate(rec.dx, start=1):
        s.add(ClaimDx(source_file_id=sf, claim_id=claim.id, seq=i, dx_qualifier=qual, dx_code=code))
    for ln in rec.lines:
        mods = (ln.modifiers + [None] * 4)[:4]
        s.add(ClaimLine(
            source_file_id=sf, claim_id=claim.id, line_number=ln.line_number, cpt=ln.cpt,
            modifier_1=mods[0], modifier_2=mods[1], modifier_3=mods[2], modifier_4=mods[3],
            charge=ln.charge, units=ln.units, unit_basis=ln.unit_basis,
            diagnosis_pointer=ln.dx_pointer, service_date=ln.service_date,
        ))  # fmt: skip


def _write_adjustments(s, sf, remit_id, line_id, adjustments, remarks) -> None:
    for i, a in enumerate(adjustments, start=1):
        s.add(Adjustment(
            source_file_id=sf, remit_id=remit_id, remit_line_id=line_id, seq=i,
            group_code=a.group_code, reason_code=a.reason_code, amount=a.amount, quantity=a.quantity,
        ))  # fmt: skip
    for qual, code in dict.fromkeys(remarks):
        s.add(RemitRemark(source_file_id=sf, remit_id=remit_id, remit_line_id=line_id,
                          code_qualifier=qual, remark_code=code))  # fmt: skip


def _write_remit(s, sf, ev, rec: RemitRec, payment_id: int, lk: Lookups) -> None:
    remit = Remit(
        source_file_id=sf, event_id=ev.id, payment_id=payment_id,
        patient_ref_id=lk.patient(rec.patient_hash),
        claim_submitter_id=rec.claim_submitter_id, claim_status_code=rec.status_code,
        total_charge=rec.total_charge, total_paid=rec.total_paid,
        patient_responsibility=rec.patient_responsibility, filing_indicator=rec.filing_indicator,
        payer_claim_control_number=rec.payer_claim_control_number, service_date=rec.service_date,
    )  # fmt: skip
    s.add(remit)
    s.flush()
    _write_adjustments(s, sf, remit.id, None, rec.adjustments, rec.remarks)
    for ln in rec.lines:
        mods = (ln.modifiers + [None] * 4)[:4]
        line = RemitLine(
            source_file_id=sf, remit_id=remit.id, line_number=ln.line_number, cpt=ln.cpt,
            modifier_1=mods[0], modifier_2=mods[1], modifier_3=mods[2], modifier_4=mods[3],
            charge=ln.charge, paid=ln.paid, units=ln.units, allowed_amount=ln.allowed,
            service_date=ln.service_date,
        )  # fmt: skip
        s.add(line)
        s.flush()
        _write_adjustments(s, sf, remit.id, line.id, ln.adjustments, ln.remarks)


def _already_loaded(s: Session, tx: Transaction, event_type: str, first_rec) -> bool:
    """Same ISA13/GS06/ST02 and identical content already in the event log (a re-sent file)."""
    first_type = "835.payment" if event_type == "835" else event_type
    found = s.scalars(
        select(Event.id)
        .where(Event.isa13 == tx.isa13, Event.gs06 == tx.gs06, Event.st02 == tx.st02)
        .where(Event.event_type == first_type, Event.payload == to_json(first_rec))
        .limit(1)
    ).first()
    return found is not None


def _write_x12(s: Session, sf: int, parsed: list[tuple[Transaction, str, list]]) -> int:
    lk = Lookups(s, sf)
    n_events = 0
    for tx, event_type, recs in parsed:
        if _already_loaded(s, tx, event_type, recs[0]):
            continue
        seq = 0
        payment_id: int | None = None
        for rec in recs:
            seq += 1
            et = event_type
            if event_type == "835":
                et = "835.payment" if isinstance(rec, PaymentRec) else "835.remit"
            ev = _event(s, sf, tx, seq, et, rec)
            n_events += 1
            if isinstance(rec, ClaimRec):
                _write_claim(s, sf, ev, rec, lk)
            elif isinstance(rec, PaymentRec):
                pay = Payment(
                    source_file_id=sf, event_id=ev.id, payer_id=lk.payer(rec.payer_code, rec.payer_name),
                    trace_number=rec.trace_number, payment_amount=rec.amount,
                    credit_debit=rec.credit_debit, payment_method=rec.method,
                    payment_date=rec.payment_date,
                )  # fmt: skip
                s.add(pay)
                s.flush()
                payment_id = pay.id
                for p in rec.plb:
                    s.add(PlbAdjustment(
                        source_file_id=sf, payment_id=pay.id, seq=p.seq, provider_ref=p.provider_ref,
                        fiscal_period_date=p.fiscal_period_date, reason_code=p.reason_code,
                        reference_id=p.reference_id, amount=p.amount,
                    ))  # fmt: skip
            elif isinstance(rec, RemitRec):
                _write_remit(s, sf, ev, rec, payment_id, lk)
            elif isinstance(rec, Ack999Rec):
                s.add(Ack999(source_file_id=sf, event_id=ev.id, acked_gs06=rec.acked_gs06,
                             acked_st02=rec.acked_st02, transaction_set=rec.transaction_set,
                             transaction_status=rec.transaction_status, group_status=rec.group_status,
                             error_codes=rec.error_codes))  # fmt: skip
            elif isinstance(rec, Elig271Rec):
                s.add(EligibilityResponse(
                    source_file_id=sf, event_id=ev.id, payer_id=lk.payer(rec.payer_code, rec.payer_name),
                    patient_ref_id=lk.patient(rec.patient_hash), response_ref=rec.response_ref,
                    checked_on=rec.checked_on, service_date=rec.service_date, active=rec.active,
                    plan_begin=rec.plan_begin, plan_end=rec.plan_end, other_payer=rec.other_payer,
                    copay=rec.copay, coinsurance=rec.coinsurance, deductible_remaining=rec.deductible_remaining,
                ))  # fmt: skip
            elif isinstance(rec, Ack277Rec):
                s.add(Ack277Ca(source_file_id=sf, event_id=ev.id,
                               claim_submitter_id=rec.claim_submitter_id,
                               status_category=rec.status_category, status_code=rec.status_code,
                               entity_code=rec.entity_code, status_date=rec.status_date,
                               total_charge=rec.total_charge,
                               payer_claim_number=rec.payer_claim_number))  # fmt: skip
        s.flush()
    return n_events


def parse_fee_schedule(text: str) -> list[dict]:
    """CSV columns: payer_id, cpt, modifier, allowed_amount, effective_date[, end_date]."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    need = {"payer_id", "cpt", "allowed_amount", "effective_date"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise X12Error(f"fee schedule CSV needs columns {sorted(need)}")
    for n, r in enumerate(reader, start=2):
        try:
            rows.append({
                "payer": r["payer_id"].strip(), "cpt": r["cpt"].strip(),
                "modifier": (r.get("modifier") or "").strip(),
                "allowed": Decimal(r["allowed_amount"]),
                "effective": date.fromisoformat(r["effective_date"]),
                "end": date.fromisoformat(r["end_date"]) if r.get("end_date") else None,
            })  # fmt: skip
        except (InvalidOperation, ValueError, KeyError) as e:
            raise X12Error(f"fee schedule line {n}: {e}") from None
    if not rows:
        raise X12Error("fee schedule CSV has no rows")
    return rows


def _write_fee_schedule(s: Session, sf: int, rows: list[dict]) -> int:
    lk = Lookups(s, sf)
    for r in rows:
        s.add(FeeSchedule(
            source_file_id=sf, payer_id=lk.payer(r["payer"], r["payer"]), cpt=r["cpt"],
            modifier=r["modifier"], allowed_amount=r["allowed"], effective_date=r["effective"],
            end_date=r["end"],
        ))  # fmt: skip
    s.flush()
    return len(rows)


def parse_visits(text: str, salt: str) -> list[dict]:
    """CSV columns: visit_id, payer_id, provider_npi, patient_ref (member id), dos, cpt, units. Hashes the member id."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    need = {"visit_id", "payer_id", "provider_npi", "patient_ref", "dos", "cpt", "units"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise X12Error(f"visits CSV needs columns {sorted(need)}")
    for n, r in enumerate(reader, start=2):
        try:
            rows.append({
                "ref": r["visit_id"].strip(), "payer": r["payer_id"].strip(), "npi": r["provider_npi"].strip(),
                "patient": hashing.patient_hash(salt, r["patient_ref"]),
                "dos": date.fromisoformat(r["dos"]), "cpt": r["cpt"].strip(), "units": Decimal(r["units"]),
            })  # fmt: skip
        except (InvalidOperation, ValueError, KeyError) as e:
            raise X12Error(f"visits line {n}: {e}") from None
    if not rows:
        raise X12Error("visits CSV has no rows")
    return rows


def _write_visits(s: Session, sf: int, rows: list[dict]) -> int:
    lk = Lookups(s, sf)
    for r in rows:
        s.add(Visit(
            source_file_id=sf, visit_ref=r["ref"], payer_id=lk.payer(r["payer"], r["payer"]),
            provider_id=lk.provider(r["npi"], "", None), patient_ref_id=lk.patient(r["patient"]),
            service_date=r["dos"], cpt=r["cpt"], units=r["units"],
        ))  # fmt: skip
    s.flush()
    return len(rows)


def parse_appointments(text: str, salt: str) -> list[dict]:
    """CSV columns: appointment_id, payer_id, provider_npi, patient_ref (member id), appt_date, booked_on, cpt."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    need = {"appointment_id", "payer_id", "provider_npi", "patient_ref", "appt_date", "booked_on", "cpt"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise X12Error(f"appointments CSV needs columns {sorted(need)}")
    for n, r in enumerate(reader, start=2):
        try:
            rows.append({
                "ref": r["appointment_id"].strip(), "payer": r["payer_id"].strip(), "npi": r["provider_npi"].strip(),
                "patient": hashing.patient_hash(salt, r["patient_ref"]),
                "appt": date.fromisoformat(r["appt_date"]), "booked": date.fromisoformat(r["booked_on"]),
                "cpt": r["cpt"].strip(), "status": (r.get("status") or "booked").strip(),
            })  # fmt: skip
        except (ValueError, KeyError) as e:
            raise X12Error(f"appointments line {n}: {e}") from None
    if not rows:
        raise X12Error("appointments CSV has no rows")
    return rows


def _write_appointments(s: Session, sf: int, rows: list[dict]) -> int:
    lk = Lookups(s, sf)
    for r in rows:
        s.add(Appointment(
            source_file_id=sf, appt_ref=r["ref"], payer_id=lk.payer(r["payer"], r["payer"]),
            provider_id=lk.provider(r["npi"], "", None), patient_ref_id=lk.patient(r["patient"]),
            appt_date=r["appt"], booked_on=r["booked"], cpt=r["cpt"], status=r["status"],
        ))  # fmt: skip
    s.flush()
    return len(rows)


def parse_authorizations(text: str, salt: str) -> list[dict]:
    """CSV: authorization_id, payer_id, patient_ref, cpt, status, requested_on; optional appointment_id, units_approved,
    units_used, units_as_of, start_date, end_date, decided_on (empty = not known)."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    need = {"authorization_id", "payer_id", "patient_ref", "cpt", "status", "requested_on"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise X12Error(f"authorizations CSV needs columns {sorted(need)}")

    def day(r, key):
        v = (r.get(key) or "").strip()
        return date.fromisoformat(v) if v else None

    def num(r, key):
        v = (r.get(key) or "").strip()
        return int(v) if v else None

    for n, r in enumerate(reader, start=2):
        try:
            status = r["status"].strip().lower()
            if status not in ("requested", "approved", "denied", "expired"):
                raise ValueError(f"status {status!r}")
            rows.append({
                "ref": r["authorization_id"].strip(), "payer": r["payer_id"].strip(),
                "appointment": (r.get("appointment_id") or "").strip() or None,
                "patient": hashing.patient_hash(salt, r["patient_ref"]), "cpt": r["cpt"].strip(), "status": status,
                "requested": date.fromisoformat(r["requested_on"]), "decided": day(r, "decided_on"),
                "approved": num(r, "units_approved"), "used": num(r, "units_used"),
                "units_as_of": day(r, "units_as_of"),
                "start": day(r, "start_date"), "end": day(r, "end_date"),
            })  # fmt: skip
        except (ValueError, KeyError) as e:
            raise X12Error(f"authorizations line {n}: {e}") from None
    if not rows:
        raise X12Error("authorizations CSV has no rows")
    return rows


def _write_authorizations(s: Session, sf: int, rows: list[dict]) -> int:
    lk = Lookups(s, sf)
    for r in rows:
        s.add(Authorization(
            source_file_id=sf, auth_ref=r["ref"], payer_id=lk.payer(r["payer"], r["payer"]),
            patient_ref_id=lk.patient(r["patient"]), cpt=r["cpt"], appointment_ref=r["appointment"],
            units_approved=r["approved"],
            units_used=r["used"], units_as_of=r["units_as_of"], start_date=r["start"], end_date=r["end"],
            status=r["status"], requested_on=r["requested"], decided_on=r["decided"],
        ))  # fmt: skip
    s.flush()
    return len(rows)


def parse_deposits(text: str) -> list[dict]:
    """CSV: deposit_id, deposit_date, amount; optional payer_id, trace (835 TRN02), method."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    need = {"deposit_id", "deposit_date", "amount"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise X12Error(f"bank deposits CSV needs columns {sorted(need)}")
    for n, r in enumerate(reader, start=2):
        try:
            rows.append({
                "ref": r["deposit_id"].strip(), "date": date.fromisoformat(r["deposit_date"]),
                "amount": Decimal(r["amount"]), "payer": (r.get("payer_id") or "").strip() or None,
                "trace": (r.get("trace") or "").strip() or None, "method": (r.get("method") or "ACH").strip(),
            })  # fmt: skip
        except (InvalidOperation, ValueError, KeyError) as e:
            raise X12Error(f"bank deposits line {n}: {e}") from None
    if not rows:
        raise X12Error("bank deposits CSV has no rows")
    return rows


def _write_deposits(s: Session, sf: int, rows: list[dict]) -> int:
    lk = Lookups(s, sf)
    for r in rows:
        s.add(BankDeposit(
            source_file_id=sf, deposit_ref=r["ref"], deposit_date=r["date"], amount=r["amount"],
            payer_id=lk.payer(r["payer"], r["payer"]) if r["payer"] else None, trace_ref=r["trace"],
            method=r["method"],
        ))  # fmt: skip
    s.flush()
    return len(rows)


def parse_postings(text: str) -> list[dict]:
    """CSV: posting_id, payment_trace, claim_id, posted_on, posted_amount; optional posted_by_role."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    need = {"posting_id", "payment_trace", "claim_id", "posted_on", "posted_amount"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise X12Error(f"postings CSV needs columns {sorted(need)}")
    for n, r in enumerate(reader, start=2):
        try:
            rows.append({
                "ref": r["posting_id"].strip(), "trace": r["payment_trace"].strip(), "claim": r["claim_id"].strip(),
                "on": date.fromisoformat(r["posted_on"]), "amount": Decimal(r["posted_amount"]),
                "role": (r.get("posted_by_role") or "payment_poster").strip(),
            })  # fmt: skip
        except (InvalidOperation, ValueError, KeyError) as e:
            raise X12Error(f"postings line {n}: {e}") from None
    if not rows:
        raise X12Error("postings CSV has no rows")
    return rows


def _write_postings(s: Session, sf: int, rows: list[dict]) -> int:
    for r in rows:
        s.add(Posting(
            source_file_id=sf, posting_ref=r["ref"], payment_trace=r["trace"], claim_submitter_id=r["claim"],
            posted_on=r["on"], posted_amount=r["amount"], posted_by_role=r["role"],
        ))  # fmt: skip
    s.flush()
    return len(rows)


def parse_notes(text: str) -> list[dict]:
    """CSV columns: visit_id, note_date, signed_date (empty = unsigned), minutes (optional), elements (comma list)."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    need = {"visit_id", "note_date", "signed_date", "elements"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise X12Error(f"notes CSV needs columns {sorted(need)}")
    for n, r in enumerate(reader, start=2):
        try:
            signed = (r["signed_date"] or "").strip()
            minutes = (r.get("minutes") or "").strip()
            rows.append({
                "ref": r["visit_id"].strip(), "note_date": date.fromisoformat(r["note_date"]),
                "signed": date.fromisoformat(signed) if signed else None,
                "minutes": int(minutes) if minutes else None, "elements": ",".join(
                    e.strip() for e in (r["elements"] or "").split(",") if e.strip()
                ),
            })  # fmt: skip
        except (ValueError, KeyError) as e:
            raise X12Error(f"notes line {n}: {e}") from None
    if not rows:
        raise X12Error("notes CSV has no rows")
    return rows


def _write_notes(s: Session, sf: int, rows: list[dict]) -> int:
    for r in rows:
        s.add(VisitNote(
            source_file_id=sf, visit_ref=r["ref"], note_date=r["note_date"], signed_date=r["signed"],
            minutes=r["minutes"], elements=r["elements"],
        ))  # fmt: skip
    s.flush()
    return len(rows)


def parse_charges(text: str) -> list[dict]:
    """CSV columns: charge_id, visit_id, cpt, units, entered_date."""
    rows = []
    reader = csv.DictReader(io.StringIO(text))
    need = {"charge_id", "visit_id", "cpt", "units", "entered_date"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise X12Error(f"charges CSV needs columns {sorted(need)}")
    for n, r in enumerate(reader, start=2):
        try:
            rows.append({
                "ref": r["charge_id"].strip(), "visit": r["visit_id"].strip(), "cpt": r["cpt"].strip(),
                "units": Decimal(r["units"]), "entered": date.fromisoformat(r["entered_date"]),
            })  # fmt: skip
        except (InvalidOperation, ValueError, KeyError) as e:
            raise X12Error(f"charges line {n}: {e}") from None
    if not rows:
        raise X12Error("charges CSV has no rows")
    return rows


def _write_charges(s: Session, sf: int, rows: list[dict]) -> int:
    for r in rows:
        s.add(Charge(
            source_file_id=sf, charge_ref=r["ref"], visit_ref=r["visit"], cpt=r["cpt"], units=r["units"],
            entered_date=r["entered"],
        ))  # fmt: skip
    s.flush()
    return len(rows)


def csv_kind(name: str) -> str:
    """Which CSV this is, from its file name: charges, notes, visits, else a fee schedule."""
    low = name.lower()
    names = {"charge": "charges", "note": "notes", "appoint": "appointments", "authoriz": "authorizations",
             "deposit": "deposits", "posting": "postings", "visit": "visits"}  # fmt: skip
    for kind, file_type in names.items():
        if kind in low:
            return file_type
    return "fee_schedule"


def ingest_parsed(
    engine: Engine, tenant_id: int, name: str, fingerprint: str, file_type: str, parsed: list, size: int = 0
) -> IngestResult:
    """Load already-parsed transactions that did not come from file bytes (e.g. the Valley database).

    `fingerprint` plays the role of the file hash: loading the same fingerprint twice is a no-op.
    """
    sha = hashlib.sha256(fingerprint.encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        existing = s.scalars(select(SourceFile).where(SourceFile.file_sha256 == sha)).first()
        if existing is not None:
            return IngestResult(name, "skipped", file_type, f"already loaded as source_file {existing.id}")
        sf = SourceFile(file_name=name[:500], file_sha256=sha, file_type=file_type, byte_size=size, status="loaded")
        s.add(sf)
        s.flush()
        try:
            n = _write_x12(s, sf.id, parsed)
            if n == 0:
                s.rollback()
                return IngestResult(name, "skipped", file_type, "same transactions already loaded")
            s.commit()
        except Exception:
            s.rollback()
            raise
        return IngestResult(name, "loaded", file_type, events=n)


def ingest_file(engine: Engine, tenant_id: int, path: Path, salt: str) -> IngestResult:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        existing = s.scalars(select(SourceFile).where(SourceFile.file_sha256 == sha)).first()
        if existing is not None:
            return IngestResult(str(path), "skipped", existing.file_type,
                                f"already ingested as source_file {existing.id} ({existing.status})")  # fmt: skip

        is_csv = path.suffix.lower() == ".csv"
        kind = csv_kind(path.name) if is_csv else ""
        file_type = kind if is_csv else "unknown"
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = None
        try:
            if text is None:
                raise X12Error("file is not UTF-8 text")
            if kind == "visits":
                parsed, payload = "visits", parse_visits(text, salt)
            elif kind == "notes":
                parsed, payload = "notes", parse_notes(text)
            elif kind == "appointments":
                parsed, payload = "appointments", parse_appointments(text, salt)
            elif kind == "authorizations":
                parsed, payload = "authorizations", parse_authorizations(text, salt)
            elif kind == "deposits":
                parsed, payload = "deposits", parse_deposits(text)
            elif kind == "postings":
                parsed, payload = "postings", parse_postings(text)
            elif kind == "charges":
                parsed, payload = "charges", parse_charges(text)
            elif is_csv:
                parsed, payload = "fee_schedule", parse_fee_schedule(text)
            else:
                file_type, payload = parse_x12(text, salt)
                parsed = file_type
        except X12Error as e:
            s.add(SourceFile(file_name=path.name, file_sha256=sha, file_type=file_type,
                             byte_size=len(raw), status="failed", failure_reason=str(e)[:1000]))  # fmt: skip
            s.commit()
            return IngestResult(str(path), "failed", file_type, str(e))

        sf = SourceFile(file_name=path.name, file_sha256=sha, file_type=parsed,
                        byte_size=len(raw), status="loaded")  # fmt: skip
        s.add(sf)
        s.flush()
        try:
            if kind == "visits":
                n = _write_visits(s, sf.id, payload)
            elif kind == "notes":
                n = _write_notes(s, sf.id, payload)
            elif kind == "appointments":
                n = _write_appointments(s, sf.id, payload)
            elif kind == "authorizations":
                n = _write_authorizations(s, sf.id, payload)
            elif kind == "deposits":
                n = _write_deposits(s, sf.id, payload)
            elif kind == "postings":
                n = _write_postings(s, sf.id, payload)
            elif kind == "charges":
                n = _write_charges(s, sf.id, payload)
            else:
                n = _write_fee_schedule(s, sf.id, payload) if is_csv else _write_x12(s, sf.id, payload)
            if n == 0:  # every transaction in this file was already loaded from another file
                s.rollback()
                return IngestResult(str(path), "skipped", parsed,
                                    "same transactions (control numbers + content) already loaded")  # fmt: skip
            s.commit()
        except Exception:
            s.rollback()
            raise
        return IngestResult(str(path), "loaded", parsed, events=n)


def ingest_path(engine: Engine, tenant_id: int, path: Path, salt: str) -> list[IngestResult]:
    """Ingest a file, or every X12 / CSV file under a folder, in name order."""
    if path.is_file():
        return [ingest_file(engine, tenant_id, path, salt)]
    files = sorted(
        p for p in path.rglob("*")
        if p.is_file() and (p.suffix.lower() in X12_SUFFIXES or p.suffix.lower() == ".csv")
        and (p.suffix.lower() != ".csv" or any(k in p.name.lower() for k in CSV_NAME_HINTS))
    )  # fmt: skip
    return [ingest_file(engine, tenant_id, p, salt) for p in files]
