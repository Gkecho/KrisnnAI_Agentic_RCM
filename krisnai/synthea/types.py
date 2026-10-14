"""Plain data shapes shared by the Synthea bundle builder, the payer simulator and the X12 writers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")
PATIENT_SHARE = Decimal("0.10")
BILLED_MARKUP = Decimal("1.6")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, ROUND_HALF_UP)


@dataclass(frozen=True)
class PayerInfo:
    payer_id: str
    name: str
    fee_multiplier: Decimal
    pay_days: int


@dataclass(frozen=True)
class Person:
    ref: str  # member id on the claim
    last: str
    first: str
    dob: date
    sex: str


@dataclass
class Bundle:
    """One billable encounter before any payer behaviour is applied."""

    claim_id: str
    synthea_id: str
    payer: PayerInfo
    patient: Person
    provider_npi: str
    dos: date
    dx: list[str]
    cpts: list[tuple[str, int]]  # (cpt, units)


@dataclass
class SimLine:
    cpt: str
    units: int
    billed: Decimal
    allowed: Decimal
    pr: Decimal = Decimal("0")
    paid: Decimal = Decimal("0")
    cas: list[tuple[str, str, Decimal]] = field(default_factory=list)  # (group, reason, amount)

    @property
    def expected_pay(self) -> Decimal:
        return self.allowed - money(self.allowed * PATIENT_SHARE)


@dataclass
class SimClaim:
    claim_id: str
    payer: PayerInfo
    provider_npi: str
    patient: Person
    dos: date
    dx: list[str]
    lines: list[SimLine]
    submitted: date
    scenario: str = "clean"  # clean denial timely_filing underpayment rejection open
    carc: str = ""
    remit_date: date | None = None
    shortfall_line: int | None = None
    shortfall: Decimal = Decimal("0")

    @property
    def billed(self) -> Decimal:
        return sum((ln.billed for ln in self.lines), Decimal("0"))

    @property
    def paid(self) -> Decimal:
        return sum((ln.paid for ln in self.lines), Decimal("0"))

    @property
    def pr(self) -> Decimal:
        return sum((ln.pr for ln in self.lines), Decimal("0"))

    @property
    def payer_claim_no(self) -> str:
        return "PCN" + self.claim_id[-6:]

    @property
    def has_remit(self) -> bool:
        return self.scenario not in ("rejection", "open")


@dataclass
class SimVisit:
    visit_id: str
    payer: PayerInfo
    provider_npi: str
    patient: Person
    dos: date
    cpt: str
    units: int

    @property
    def expected_pay(self) -> Decimal:
        from krisnai.synthea.crosswalk import CPT_BASE_FEE

        allowed = money(CPT_BASE_FEE[self.cpt] * self.payer.fee_multiplier) * self.units
        return allowed - money(allowed * PATIENT_SHARE)
