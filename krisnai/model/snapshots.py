"""Point-in-time snapshots derived from the transactional tables."""

from __future__ import annotations

from sqlalchemy import Date, Integer, String

from krisnai.model.base import Base, Decimal, FromFile, Mapped, Money, Scoped, col, date, fk, scoped


class ArSnapshot(Scoped, FromFile, Base):
    """Open balance of a claim as of a date, so AR metrics can be replayed as of any day."""

    __tablename__ = "ar_snapshot"
    __table_args__ = scoped([("claim_id", "claim")], unique=[("claim_id", "as_of_date")])

    claim_id: Mapped[int] = fk("claim the balance belongs to")
    as_of_date: Mapped[date] = col(Date, "snapshot date; only data known by this date is used")
    balance: Mapped[Decimal] = col(Money, "claim charge less paid, adjusted and patient amounts as of the date")
    days_outstanding: Mapped[int] = col(Integer, "as_of_date minus claim service date")
    aging_bucket: Mapped[str] = col(String(10), "0-30 | 31-60 | 61-90 | 91-120 | 120+")
