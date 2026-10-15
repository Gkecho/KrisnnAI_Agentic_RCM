"""Provider enrollment with each payer and sanctions screening results, for the credentialing agent."""

from __future__ import annotations

from sqlalchemy import Date, String

from krisnai.model.base import Base, FromFile, Mapped, Scoped, col, date, fk, scoped


class Enrollment(Scoped, FromFile, Base):
    """One provider's enrollment with one payer, from the credentialing extract (read-only)."""

    __tablename__ = "enrollment"
    __table_args__ = scoped(
        [("provider_id", "provider"), ("payer_id", "payer")],
        unique=[("enrollment_ref",)],
        checks=[("status", "status IN ('pending', 'active', 'expired', 'denied', 'terminated')")],
    )

    enrollment_ref: Mapped[str] = col(String(40), "enrollments CSV enrollment_id (the credentialing system's number)")
    provider_id: Mapped[int] = fk("enrollments CSV provider_npi, resolved to provider.id")
    payer_id: Mapped[int] = fk("enrollments CSV payer_id, resolved to payer.id")
    status: Mapped[str] = col(String(12), "enrollments CSV status: pending, active, expired, denied or terminated")
    submitted_on: Mapped[date | None] = col(Date, "enrollments CSV submitted_on: when the application went in")
    effective_on: Mapped[date | None] = col(Date, "enrollments CSV effective_on: when it became active")
    expires_on: Mapped[date | None] = col(Date, "enrollments CSV expires_on, empty = no expiry on file")
    status_on: Mapped[date] = col(Date, "enrollments CSV status_on: the day this status was recorded")


class ProviderScreening(Scoped, FromFile, Base):
    """One sanctions / exclusion screening result for a provider (the result is a feed, not a live lookup)."""

    __tablename__ = "provider_screening"
    __table_args__ = scoped(
        [("provider_id", "provider")],
        unique=[("screening_ref",)],
        checks=[("result", "result IN ('clear', 'excluded')")],
    )

    screening_ref: Mapped[str] = col(String(40), "screenings CSV screening_id")
    provider_id: Mapped[int] = fk("screenings CSV provider_npi, resolved to provider.id")
    screened_on: Mapped[date] = col(Date, "screenings CSV screened_on")
    result: Mapped[str] = col(String(10), "screenings CSV result: clear or excluded")
    source: Mapped[str] = col(String(20), "screenings CSV source list (e.g. OIG, SAM, STATE)")
