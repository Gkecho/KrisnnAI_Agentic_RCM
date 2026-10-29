"""Practice-management extract: scheduled / completed visits, used to find visits that were never billed."""

from __future__ import annotations

from sqlalchemy import Date, Integer, String

from krisnnai.model.base import Base, Decimal, FromFile, Mapped, Scoped, Units, col, date, fk, scoped


class Visit(Scoped, FromFile, Base):
    """One visit line from the PM system's visits CSV (read-only extract, never written back)."""

    __tablename__ = "visit"
    __table_args__ = scoped(
        [("payer_id", "payer"), ("provider_id", "provider"), ("patient_ref_id", "patient_ref")],
        unique=[("visit_ref",)],
    )  # fmt: skip

    visit_ref: Mapped[str] = col(String(40), "visits CSV visit_id (the PM system's own visit number)")
    payer_id: Mapped[int] = fk("visits CSV payer_id, resolved to payer.id")
    provider_id: Mapped[int] = fk("visits CSV provider_npi, resolved to provider.id")
    patient_ref_id: Mapped[int] = fk("visits CSV patient_ref (member id), hashed to patient_ref.id")
    service_date: Mapped[date] = col(Date, "visits CSV dos")
    cpt: Mapped[str] = col(String(5), "visits CSV cpt")
    units: Mapped[Decimal] = col(Units, "visits CSV units")


class VisitNote(Scoped, FromFile, Base):
    """Documentation status of one visit, from the EHR (read-only extract). Elements only: no note text is stored."""

    __tablename__ = "visit_note"
    __table_args__ = scoped(unique=[("visit_ref",)])

    visit_ref: Mapped[str] = col(String(40), "notes CSV visit_id (matches visit.visit_ref)")
    note_date: Mapped[date] = col(Date, "notes CSV note_date: when the note was started")
    signed_date: Mapped[date | None] = col(Date, "notes CSV signed_date, empty = not signed")
    minutes: Mapped[int | None] = col(Integer, "notes CSV minutes, empty = no time documented")
    elements: Mapped[str] = col(String(200), "notes CSV elements: comma list of documented element names")


class Charge(Scoped, FromFile, Base):
    """One charge line entered in the practice-management system for a visit (read-only extract)."""

    __tablename__ = "charge"
    __table_args__ = scoped(unique=[("charge_ref",)])

    charge_ref: Mapped[str] = col(String(40), "charges CSV charge_id (the PM system's own charge number)")
    visit_ref: Mapped[str] = col(String(40), "charges CSV visit_id (matches visit.visit_ref)")
    cpt: Mapped[str] = col(String(5), "charges CSV cpt")
    units: Mapped[Decimal] = col(Units, "charges CSV units")
    entered_date: Mapped[date] = col(Date, "charges CSV entered_date: when the charge was keyed")
