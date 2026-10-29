"""Reference data: payers, providers, hashed patient references, fee schedules."""

from __future__ import annotations

from sqlalchemy import Date, LargeBinary, String

from krisnnai.model.base import Base, Decimal, FromFile, Mapped, Money, Scoped, col, date, fk, scoped


class Payer(Scoped, FromFile, Base):
    __tablename__ = "payer"
    __table_args__ = scoped(unique=[("payer_id_code",)])

    payer_id_code: Mapped[str] = col(String(80), "NM109 where NM101 = PR/PI (payer identifier)")
    name: Mapped[str] = col(String(200), "NM103 payer name")


class Provider(Scoped, FromFile, Base):
    __tablename__ = "provider"
    __table_args__ = scoped(unique=[("npi",)])

    npi: Mapped[str] = col(String(10), "NM109 where NM108 = XX (billing / pay-to NPI)")
    name: Mapped[str] = col(String(200), "NM103 organization or provider name")
    tax_id: Mapped[str | None] = col(String(9), "REF*EI (employer identification number)")


class PatientRef(Scoped, FromFile, Base):
    """Salted SHA-256 of the patient identifier. Raw name, DOB and member ID are never stored."""

    __tablename__ = "patient_ref"
    __table_args__ = scoped(unique=[("ref_hash",)])

    ref_hash: Mapped[bytes] = col(
        LargeBinary(32),
        "SHA-256(tenant salt + NM109 member id), computed before the row is written",
    )


class FeeSchedule(Scoped, FromFile, Base):
    """Contracted allowed amount per payer + CPT + modifier, valid for a date range."""

    __tablename__ = "fee_schedule"
    __table_args__ = scoped([("payer_id", "payer")], unique=[("payer_id", "cpt", "modifier", "effective_date")])

    payer_id: Mapped[int] = fk("fee schedule CSV payer_id, resolved to payer.id")
    cpt: Mapped[str] = col(String(5), "fee schedule CSV cpt (matches SV1-01-2 / SVC01-2)")
    modifier: Mapped[str] = col(String(2), "fee schedule CSV modifier, empty string when none")
    allowed_amount: Mapped[Decimal] = col(Money, "fee schedule CSV allowed_amount")
    effective_date: Mapped[date] = col(Date, "fee schedule CSV effective_date")
    end_date: Mapped[date | None] = col(Date, "fee schedule CSV end_date, null = open ended")
