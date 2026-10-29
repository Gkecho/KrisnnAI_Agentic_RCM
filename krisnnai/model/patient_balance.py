"""Patient payments and statement / account status, for the patient engagement agent (staff-facing worklist only)."""

from __future__ import annotations

from sqlalchemy import Date, String

from krisnnai.model.base import Base, Decimal, FromFile, Mapped, Money, Scoped, col, date, scoped


class PatientPayment(Scoped, FromFile, Base):
    """One payment received from a patient against a claim (read-only extract)."""

    __tablename__ = "patient_payment"
    __table_args__ = scoped(unique=[("payment_ref",)])

    payment_ref: Mapped[str] = col(String(40), "patient payments CSV payment_id (the PM system's own number)")
    claim_submitter_id: Mapped[str] = col(String(38), "patient payments CSV claim_id (CLM01) the payment applies to")
    paid_on: Mapped[date] = col(Date, "patient payments CSV paid_on")
    amount: Mapped[Decimal] = col(Money, "patient payments CSV amount")
    method: Mapped[str] = col(String(10), "patient payments CSV method (CARD, CHECK, CASH, ONLINE)")


class PatientStatement(Scoped, FromFile, Base):
    """One statement sent, or one change in the account's status (dispute, plan, hardship), for a claim."""

    __tablename__ = "patient_statement"
    __table_args__ = scoped(
        unique=[("statement_ref",)],
        checks=[("status", "status IN ('sent', 'disputed', 'plan', 'hardship', 'returned')")],
    )

    statement_ref: Mapped[str] = col(String(40), "statements CSV statement_id")
    claim_submitter_id: Mapped[str] = col(String(38), "statements CSV claim_id (CLM01)")
    sent_on: Mapped[date] = col(Date, "statements CSV sent_on: the day of the statement or the status change")
    channel: Mapped[str] = col(String(10), "statements CSV channel (mail, portal, sms, phone, none)")
    status: Mapped[str] = col(String(10), "statements CSV status: sent, disputed, plan, hardship or returned")
