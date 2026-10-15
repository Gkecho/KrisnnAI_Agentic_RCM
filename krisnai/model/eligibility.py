"""Appointments (PM extract) and eligibility responses (271), for the pre-visit clearance agent."""

from __future__ import annotations

from sqlalchemy import Boolean, Date, Numeric, String

from krisnai.model.base import Base, Decimal, FromFile, Mapped, Money, Scoped, col, date, fk, scoped


class Appointment(Scoped, FromFile, Base):
    """One booked visit from the PM system's appointments CSV (read-only extract, never written back)."""

    __tablename__ = "appointment"
    __table_args__ = scoped(
        [("payer_id", "payer"), ("provider_id", "provider"), ("patient_ref_id", "patient_ref")],
        unique=[("appt_ref",)],
    )  # fmt: skip

    appt_ref: Mapped[str] = col(String(40), "appointments CSV appointment_id (the PM system's own number)")
    payer_id: Mapped[int] = fk("appointments CSV payer_id: the coverage on file at booking")
    provider_id: Mapped[int] = fk("appointments CSV provider_npi, resolved to provider.id")
    patient_ref_id: Mapped[int] = fk("appointments CSV patient_ref (member id), hashed to patient_ref.id")
    appt_date: Mapped[date] = col(Date, "appointments CSV appt_date: the day of the visit")
    booked_on: Mapped[date] = col(Date, "appointments CSV booked_on: when it was scheduled")
    cpt: Mapped[str] = col(String(5), "appointments CSV cpt: the expected service")
    status: Mapped[str] = col(String(12), "appointments CSV status (booked, cancelled)")


class EligibilityResponse(Scoped, FromFile, Base):
    """One subscriber answer from a 271 eligibility response."""

    __tablename__ = "eligibility_response"
    __table_args__ = scoped(
        [("event_id", "event"), ("payer_id", "payer"), ("patient_ref_id", "patient_ref")],
        unique=[("event_id",)],
    )  # fmt: skip

    event_id: Mapped[int] = fk("271.response event this row was built from")
    payer_id: Mapped[int] = fk("271 NM1*PR payer id, resolved to payer.id")
    patient_ref_id: Mapped[int | None] = fk("271 NM1*IL member id, hashed to patient_ref.id")
    response_ref: Mapped[str] = col(String(50), "271 TRN02 trace number")
    checked_on: Mapped[date] = col(Date, "271 BHT04 date the answer was produced (interchange date)")
    service_date: Mapped[date | None] = col(Date, "271 DTP*291 date the answer applies to")
    active: Mapped[bool] = col(Boolean, "271 EB01: true = 1 active coverage, false = 6 inactive")
    plan_begin: Mapped[date | None] = col(Date, "271 DTP*346 plan begin")
    plan_end: Mapped[date | None] = col(Date, "271 DTP*347 plan end, null = open ended")
    other_payer: Mapped[str | None] = col(String(60), "271 EB*R followed by NM1*PR: another payer is primary")
    copay: Mapped[Decimal | None] = col(Money, "271 EB*B amount: flat copayment")
    coinsurance: Mapped[Decimal | None] = col(Numeric(5, 4), "271 EB*A percent as a fraction (0.2 = 20%)")
    deductible_remaining: Mapped[Decimal | None] = col(Money, "271 EB*C amount still to be met")
