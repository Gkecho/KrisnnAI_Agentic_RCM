"""A payer simulator for the live encounter stream: it reads an 837 and decides, deterministically in S1.

It is a stand-in written for the demo. It is NOT a model of any real payer: its fee schedule and its denial rules are
configured here, and the agents must never import this module (they see only the X12 files and portal pages it produces;
`tests/test_live_s1.py` enforces that).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from krisnai.ingest import p837
from krisnai.ingest.x12 import Transaction, read_transactions
from krisnai.synthea.types import PayerInfo, Person, SimClaim, SimLine

CENT = Decimal("0.01")
DEFAULT_FEES = {"99202": "95.00", "99203": "125.00", "99213": "90.00", "99214": "130.00", "99283": "210.00"}
COINSURANCE = Decimal("0.20")


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class Decision:
    claim: SimClaim
    outcome: str  # paid | denied
    reason: str


@dataclass
class PayerSim:
    payer_id: str
    name: str
    fees: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_FEES))
    deny: dict[str, str] = field(default_factory=dict)  # CPT -> CARC that this payer denies, S1 only (no randomness)
    members: dict[str, bool] = field(default_factory=dict)  # member id -> coverage active

    def enrol(self, member: str, active: bool = True) -> None:
        self.members[member] = active

    def eligibility(self, member: str) -> tuple[bool, bool]:
        """(found, active). A member the payer never enrolled is 'not found', which a real payer also answers."""
        return (member in self.members, self.members.get(member, False))

    # ------------------------------------------------------------------------------------------------ claims
    def to_sim_claims(self, text: str, when: date) -> list[SimClaim]:
        """The claims in an 837 as SimClaim objects (names, member id, lines), not yet adjudicated."""
        out: list[SimClaim] = []
        payer = PayerInfo(self.payer_id, self.name, Decimal("1"), 14)
        for tx in read_transactions(text):
            recs = p837.parse(tx, "live")
            people = _people(tx)
            for rec in recs:
                person = people.get(rec.claim_submitter_id) or next(iter(people.values()), None)
                if person is None:
                    person = Person("", "", "", date(1900, 1, 1), "U")
                lines = [SimLine(ln.cpt, int(ln.units), ln.charge, Decimal("0")) for ln in rec.lines]
                out.append(SimClaim(rec.claim_submitter_id, payer, rec.provider_npi or "", person,
                                    rec.service_date, [d for _, d in rec.dx], lines, when))  # fmt: skip
        return out

    def decide(self, claim: SimClaim, remit_date: date) -> Decision:
        """Pay at the fee schedule less coinsurance, or deny with the configured CARC. Fills the claim in place."""
        claim.remit_date = remit_date
        denied = {ln.cpt: self.deny[ln.cpt] for ln in claim.lines if ln.cpt in self.deny}
        if denied:
            claim.scenario, claim.carc = "denial", next(iter(denied.values()))
            for ln in claim.lines:
                ln.allowed = money(Decimal(self.fees.get(ln.cpt, "0")) * ln.units)
                ln.paid = ln.pr = Decimal("0")
                ln.cas = [("CO", claim.carc, ln.billed)]
            return Decision(claim, "denied", f"CARC {claim.carc} on CPT {', '.join(denied)}")
        claim.scenario = "clean"
        for ln in claim.lines:
            fee = Decimal(self.fees.get(ln.cpt, str(ln.billed)))
            ln.allowed = money(min(fee * ln.units, ln.billed))
            ln.pr = money(ln.allowed * COINSURANCE)
            ln.paid = ln.allowed - ln.pr
            ln.cas = [("CO", "45", ln.billed - ln.allowed), ("PR", "2", ln.pr)]
        return Decision(claim, "paid", f"allowed {sum((ln.allowed for ln in claim.lines), Decimal(0))}")


def _people(tx: Transaction) -> dict[str, Person]:
    """Subscriber per claim from NM1*IL and DMG, keyed by the claim id that follows (OpenEMR writes one per claim)."""
    people: dict[str, Person] = {}
    last = first = member = ""
    dob, sex = date(1900, 1, 1), "U"
    for seg in tx.segments:
        if seg.id == "NM1" and seg[1] == "IL":
            last, first, member = seg[3], seg[4], seg[9]
        elif seg.id == "DMG" and len(seg[2]) == 8:
            dob, sex = date(int(seg[2][:4]), int(seg[2][4:6]), int(seg[2][6:])), seg[3] or "U"
        elif seg.id == "CLM":
            people[seg[1]] = Person(member, last, first, dob, sex)
    return people


def remit_day(submitted: date, days: int = 14) -> date:
    return submitted + timedelta(days=days)
