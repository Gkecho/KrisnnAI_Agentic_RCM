"""Prior-authorization records (PM / payer portal extract) and the payer + CPT pairs that require one."""

from __future__ import annotations

from sqlalchemy import Date, Integer, String

from krisnai.model.base import Base, FromFile, Mapped, Scoped, col, date, fk, scoped


class Authorization(Scoped, FromFile, Base):
    """One authorization request and its outcome, from the authorizations CSV (read-only extract)."""

    __tablename__ = "prior_authorization"
    __table_args__ = scoped(
        [("payer_id", "payer"), ("patient_ref_id", "patient_ref")],
        unique=[("auth_ref",)],
        checks=[("status", "status IN ('requested', 'approved', 'denied', 'expired')")],
    )

    auth_ref: Mapped[str] = col(String(40), "authorizations CSV authorization_id (the payer or PM reference)")
    payer_id: Mapped[int] = fk("authorizations CSV payer_id, resolved to payer.id")
    patient_ref_id: Mapped[int] = fk("authorizations CSV patient_ref (member id), hashed to patient_ref.id")
    cpt: Mapped[str] = col(String(5), "authorizations CSV cpt: the service the authorization covers")
    appointment_ref: Mapped[str | None] = col(
        String(40), "authorizations CSV appointment_id: the booked service it was requested for, empty if unlinked"
    )
    units_approved: Mapped[int | None] = col(Integer, "authorizations CSV units_approved, empty until decided")
    units_used: Mapped[int | None] = col(Integer, "authorizations CSV units_used as of units_as_of")
    units_as_of: Mapped[date | None] = col(Date, "authorizations CSV units_as_of: the day units_used was true")
    start_date: Mapped[date | None] = col(Date, "authorizations CSV start_date of the approved window")
    end_date: Mapped[date | None] = col(Date, "authorizations CSV end_date of the approved window, empty = open")
    status: Mapped[str] = col(String(10), "authorizations CSV status: requested, approved, denied or expired")
    requested_on: Mapped[date] = col(Date, "authorizations CSV requested_on")
    decided_on: Mapped[date | None] = col(Date, "authorizations CSV decided_on, empty while pending")


class AuthRequirement(Scoped, Base):
    """Payer + CPT pairs that need prior authorization (practice configuration; placeholders until signed off)."""

    __tablename__ = "auth_requirement"
    __table_args__ = scoped([("payer_id", "payer")], unique=[("payer_id", "cpt")], from_file=False)

    payer_id: Mapped[int] = fk("payer that requires the authorization")
    cpt: Mapped[str] = col(String(5), "auth config: the CPT that needs prior authorization")
    validity_days: Mapped[int] = col(Integer, "auth config: how long an approval normally stays valid")
