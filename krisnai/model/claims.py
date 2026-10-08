"""Billed side: 837P claims and lines, plus the 999 / 277CA acknowledgements."""

from __future__ import annotations

from sqlalchemy import Date, Integer, String

from krisnai.model.base import (
    Base,
    Decimal,
    FromFile,
    Mapped,
    Money,
    Scoped,
    Units,
    col,
    date,
    fk,
    scoped,
)  # fmt: skip


class Claim(Scoped, FromFile, Base):
    """One 837P claim version (CLM). A replacement claim (CLM05-3 = 7) is a new row."""

    __tablename__ = "claim"
    __table_args__ = scoped(
        [("event_id", "event"), ("payer_id", "payer"), ("provider_id", "provider"),
         ("patient_ref_id", "patient_ref")],
        unique=[("event_id",)],
    )  # fmt: skip

    event_id: Mapped[int] = fk("event this row was built from")
    payer_id: Mapped[int] = fk("NM1*PR loop 2010BB, resolved to payer.id")
    provider_id: Mapped[int] = fk("NM1*85 loop 2010AA, resolved to provider.id")
    patient_ref_id: Mapped[int] = fk("NM1*IL loop 2010BA member id, hashed to patient_ref.id")
    claim_submitter_id: Mapped[str] = col(String(38), "CLM01 patient control number")
    total_charge: Mapped[Decimal] = col(Money, "CLM02 total claim charge")
    place_of_service: Mapped[str | None] = col(String(2), "CLM05-1 facility code")
    frequency_code: Mapped[str] = col(String(1), "CLM05-3 (1 original, 7 replacement, 8 void)")
    payer_claim_control_number: Mapped[str | None] = col(String(50), "REF*F8 original reference number")
    service_date: Mapped[date | None] = col(Date, "DTP*472 / DTP*434 earliest service date")
    submitted_on: Mapped[date | None] = col(Date, "BHT04 transaction creation date")


class ClaimLine(Scoped, FromFile, Base):
    __tablename__ = "claim_line"
    __table_args__ = scoped([("claim_id", "claim")], unique=[("claim_id", "line_number")])

    claim_id: Mapped[int] = fk("parent claim")
    line_number: Mapped[int] = col(Integer, "LX01 assigned number")
    cpt: Mapped[str] = col(String(5), "SV101-2 procedure code")
    modifier_1: Mapped[str | None] = col(String(2), "SV101-3")
    modifier_2: Mapped[str | None] = col(String(2), "SV101-4")
    modifier_3: Mapped[str | None] = col(String(2), "SV101-5")
    modifier_4: Mapped[str | None] = col(String(2), "SV101-6")
    charge: Mapped[Decimal] = col(Money, "SV102 line charge")
    units: Mapped[Decimal] = col(Units, "SV104 service unit count")
    unit_basis: Mapped[str] = col(String(2), "SV103 (UN units, MJ minutes)")
    diagnosis_pointer: Mapped[str | None] = col(String(8), "SV107 diagnosis code pointer")
    service_date: Mapped[date | None] = col(Date, "DTP*472 line service date")


class ClaimDx(Scoped, FromFile, Base):
    __tablename__ = "claim_dx"
    __table_args__ = scoped([("claim_id", "claim")], unique=[("claim_id", "seq")])

    claim_id: Mapped[int] = fk("parent claim")
    seq: Mapped[int] = col(Integer, "position within HI (1 = principal)")
    dx_qualifier: Mapped[str] = col(String(3), "HI01-1 (ABK principal, ABF other)")
    dx_code: Mapped[str] = col(String(8), "HI01-2 ICD-10-CM code, no decimal point")


class Ack999(Scoped, FromFile, Base):
    """Functional acknowledgement of one 837 transaction set."""

    __tablename__ = "ack_999"
    __table_args__ = scoped([("event_id", "event")], unique=[("event_id",)])

    event_id: Mapped[int] = fk("event this row was built from")
    acked_gs06: Mapped[str] = col(String(9), "AK1-02 group control number being acknowledged")
    acked_st02: Mapped[str] = col(String(9), "AK2-02 transaction set control number acknowledged")
    transaction_set: Mapped[str] = col(String(3), "AK2-01 (837)")
    transaction_status: Mapped[str] = col(String(1), "IK5-01 (A accepted, E accepted with errors, R rejected)")
    group_status: Mapped[str | None] = col(String(1), "AK9-01")
    error_codes: Mapped[str | None] = col(String(100), "IK5-02..06 / IK4-03 joined with commas")


class Ack277Ca(Scoped, FromFile, Base):
    """Claim-level acknowledgement from the payer or clearinghouse."""

    __tablename__ = "ack_277ca"
    __table_args__ = scoped([("event_id", "event"), ("claim_id", "claim")], unique=[("event_id", "claim_submitter_id")])

    event_id: Mapped[int] = fk("event this row was built from")
    claim_id: Mapped[int | None] = fk("matched claim (set by matching, null until then)")
    claim_submitter_id: Mapped[str] = col(String(38), "TRN02 (echo of CLM01)")
    status_category: Mapped[str] = col(String(5), "STC01-1 (A1 received, A2 accepted, A3 returned, A4 not found)")
    status_code: Mapped[str | None] = col(String(5), "STC01-2")
    entity_code: Mapped[str | None] = col(String(5), "STC01-3")
    status_date: Mapped[date | None] = col(Date, "STC02")
    total_charge: Mapped[Decimal | None] = col(Money, "STC04")
    payer_claim_number: Mapped[str | None] = col(String(50), "REF*1K payer claim control number")
