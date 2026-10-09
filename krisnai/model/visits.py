"""Practice-management extract: scheduled / completed visits, used to find visits that were never billed."""

from __future__ import annotations

from sqlalchemy import Date, String

from krisnai.model.base import Base, Decimal, FromFile, Mapped, Scoped, Units, col, date, fk, scoped


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
