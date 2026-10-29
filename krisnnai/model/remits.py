"""Paid side: 835 payments, remits, lines, adjustments, remarks and provider-level adjustments."""

from __future__ import annotations

from sqlalchemy import Date, Integer, String

from krisnnai.model.base import (
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


class Payment(Scoped, FromFile, Base):
    """One payment (BPR / TRN): the EFT or check that carries a set of remits."""

    __tablename__ = "payment"
    __table_args__ = scoped([("event_id", "event"), ("payer_id", "payer")], unique=[("event_id",)])

    event_id: Mapped[int] = fk("event this row was built from")
    payer_id: Mapped[int] = fk("N1*PR loop 1000A, resolved to payer.id")
    trace_number: Mapped[str] = col(String(50), "TRN02 reassociation trace number")
    payment_amount: Mapped[Decimal] = col(Money, "BPR02 total actual provider payment")
    credit_debit: Mapped[str] = col(String(1), "BPR03 (C credit, D debit)")
    payment_method: Mapped[str] = col(String(3), "BPR04 (ACH, CHK, NON)")
    payment_date: Mapped[date] = col(Date, "BPR16 check issue / EFT effective date")


class Remit(Scoped, FromFile, Base):
    """One 835 claim payment (CLP)."""

    __tablename__ = "remit"
    __table_args__ = scoped(
        [("event_id", "event"), ("payment_id", "payment"), ("claim_id", "claim"),
         ("patient_ref_id", "patient_ref")],
        unique=[("event_id",)],
    )  # fmt: skip

    event_id: Mapped[int] = fk("event this row was built from")
    payment_id: Mapped[int] = fk("payment (BPR/TRN) this CLP belongs to")
    claim_id: Mapped[int | None] = fk("matched claim (set by M3 matching, null until then)")
    patient_ref_id: Mapped[int | None] = fk("NM1*QC member id, hashed to patient_ref.id")
    claim_submitter_id: Mapped[str] = col(String(38), "CLP01 patient control number (= CLM01)")
    claim_status_code: Mapped[str] = col(String(2), "CLP02 (1 processed primary, 4 denied, 22 reversal)")
    total_charge: Mapped[Decimal] = col(Money, "CLP03 total claim charge")
    total_paid: Mapped[Decimal] = col(Money, "CLP04 claim payment amount")
    patient_responsibility: Mapped[Decimal] = col(Money, "CLP05 patient responsibility amount")
    filing_indicator: Mapped[str | None] = col(String(2), "CLP06 claim filing indicator code")
    payer_claim_control_number: Mapped[str] = col(String(50), "CLP07 payer claim control number")
    service_date: Mapped[date | None] = col(Date, "DTM*232 claim statement period start")
    match_method: Mapped[str | None] = col(String(30), "rule that linked this remit to a claim (M3)")


class RemitLine(Scoped, FromFile, Base):
    """One 835 service line (SVC)."""

    __tablename__ = "remit_line"
    __table_args__ = scoped(
        [("remit_id", "remit"), ("claim_line_id", "claim_line")],
        unique=[("remit_id", "line_number")],
    )

    remit_id: Mapped[int] = fk("parent remit")
    claim_line_id: Mapped[int | None] = fk("matched claim line (set by M3 matching)")
    line_number: Mapped[int] = col(Integer, "position of the SVC within the CLP loop")
    cpt: Mapped[str] = col(String(5), "SVC01-2 adjudicated procedure code")
    modifier_1: Mapped[str | None] = col(String(2), "SVC01-3")
    modifier_2: Mapped[str | None] = col(String(2), "SVC01-4")
    modifier_3: Mapped[str | None] = col(String(2), "SVC01-5")
    modifier_4: Mapped[str | None] = col(String(2), "SVC01-6")
    charge: Mapped[Decimal] = col(Money, "SVC02 line charge")
    paid: Mapped[Decimal] = col(Money, "SVC03 line payment")
    units: Mapped[Decimal | None] = col(Units, "SVC05 units paid")
    allowed_amount: Mapped[Decimal | None] = col(Money, "AMT*B6 allowed amount")
    service_date: Mapped[date | None] = col(Date, "DTM*472 line service date")
    match_method: Mapped[str | None] = col(String(30), "rule that linked this line to a claim line (M3)")


class Adjustment(Scoped, FromFile, Base):
    """One CAS reason/amount pair. Claim-level CAS has remit_line_id null."""

    __tablename__ = "adjustment"
    __table_args__ = scoped(
        [("remit_id", "remit"), ("remit_line_id", "remit_line")],
        unique=[("remit_id", "remit_line_id", "seq")],
        checks=[("group_code", "group_code IN ('CO', 'CR', 'OA', 'PI', 'PR')")],
    )

    remit_id: Mapped[int] = fk("parent remit")
    remit_line_id: Mapped[int | None] = fk("parent remit line, null for claim-level CAS")
    seq: Mapped[int] = col(Integer, "position of the pair within the remit / line")
    group_code: Mapped[str] = col(
        String(2), "CAS01 (CO contractual, PR patient, OA other, PI payer initiated, CR correction)"
    )
    reason_code: Mapped[str] = col(String(5), "CAS02/05/08/... CARC")
    amount: Mapped[Decimal] = col(Money, "CAS03/06/09/... adjustment amount")
    quantity: Mapped[Decimal | None] = col(Units, "CAS04/07/10/... adjustment quantity")


class RemitRemark(Scoped, FromFile, Base):
    __tablename__ = "remit_remark"
    __table_args__ = scoped(
        [("remit_id", "remit"), ("remit_line_id", "remit_line")],
        unique=[("remit_id", "remit_line_id", "remark_code")],
    )

    remit_id: Mapped[int] = fk("parent remit")
    remit_line_id: Mapped[int | None] = fk("parent remit line, null for claim-level remark")
    code_qualifier: Mapped[str] = col(String(2), "LQ01 (HE healthcare remark codes)")
    remark_code: Mapped[str] = col(String(10), "LQ02 RARC")


class PlbAdjustment(Scoped, FromFile, Base):
    """Provider-level balance adjustment (PLB): recoupments, interest, forwarding balances."""

    __tablename__ = "plb_adjustment"
    __table_args__ = scoped([("payment_id", "payment")], unique=[("payment_id", "seq")])

    payment_id: Mapped[int] = fk("payment this PLB belongs to")
    seq: Mapped[int] = col(Integer, "position of the reason/amount pair within the PLB")
    provider_ref: Mapped[str] = col(String(50), "PLB01 provider identifier")
    fiscal_period_date: Mapped[date] = col(Date, "PLB02")
    reason_code: Mapped[str] = col(String(2), "PLB03-1 adjustment reason (WO, 72, L6, ...)")
    reference_id: Mapped[str | None] = col(String(50), "PLB03-2 reference identification")
    amount: Mapped[Decimal] = col(Money, "PLB04 adjustment amount (sign as sent)")
