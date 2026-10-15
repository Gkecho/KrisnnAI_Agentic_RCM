"""Bank deposits (bank / lockbox extract) and payment postings (PM extract), for the cash reconciliation agent."""

from __future__ import annotations

from sqlalchemy import Date, String

from krisnai.model.base import Base, Decimal, FromFile, Mapped, Money, Scoped, col, date, fk, scoped


class BankDeposit(Scoped, FromFile, Base):
    """One deposit line from the bank or lockbox file (read-only extract)."""

    __tablename__ = "bank_deposit"
    __table_args__ = scoped([("payer_id", "payer")], unique=[("deposit_ref",)])

    deposit_ref: Mapped[str] = col(String(40), "bank deposits CSV deposit_id (the bank's own line reference)")
    deposit_date: Mapped[date] = col(Date, "bank deposits CSV deposit_date: when the money reached the account")
    amount: Mapped[Decimal] = col(Money, "bank deposits CSV amount")
    payer_id: Mapped[int | None] = fk("bank deposits CSV payer_id when the bank line names the payer, else empty")
    trace_ref: Mapped[str | None] = col(String(50), "bank deposits CSV trace: the 835 TRN02 reassociation trace, if sent")
    method: Mapped[str] = col(String(10), "bank deposits CSV method (ACH, CHK, LOCKBOX)")


class Posting(Scoped, FromFile, Base):
    """One claim payment posted in the practice-management system (read-only extract)."""

    __tablename__ = "posting"
    __table_args__ = scoped(unique=[("posting_ref",)])

    posting_ref: Mapped[str] = col(String(40), "postings CSV posting_id (the PM system's own number)")
    payment_trace: Mapped[str] = col(String(50), "postings CSV payment_trace: the 835 TRN02 the posting came from")
    claim_submitter_id: Mapped[str] = col(String(38), "postings CSV claim_id (CLM01)")
    posted_on: Mapped[date] = col(Date, "postings CSV posted_on")
    posted_amount: Mapped[Decimal] = col(Money, "postings CSV posted_amount")
    posted_by_role: Mapped[str] = col(String(20), "postings CSV posted_by_role (a role, never a person's name)")
