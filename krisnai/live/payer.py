# ruff: noqa: E501
"""A payer simulator for the live encounter stream: it reads an 837 and decides, seeded and replayable.

It is a stand-in written for the demo. It is NOT a model of any real payer. What it does:

  * follows the PUBLISHED rules in the Knowledge Book (coverage, prior authorization) when it has one;
  * on top of that behaves like a payer: some claims pend for records, some are denied for ordinary reasons;
  * and, at a configured rate, DEVIATES from what it published (a wrong denial, a stale rule version, an unpublished edit, an
    underpayment). Every decision, and what the book said it should have been, goes to the truth log.

Agents must never import this module (they see only the X12 files and portal pages it produces; `tests/test_live_s1.py`
enforces that). Decisions come from a per-claim random stream seeded by (seed, claim id), so the same seed and the same
claims give a byte-identical truth log whatever the order they arrive in.
"""

from __future__ import annotations

import csv
import hashlib
import io
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from krisnai.ingest import p837
from krisnai.ingest.x12 import Transaction, read_transactions
from krisnai.knowledge import Book
from krisnai.live.catalog import condition_by_icd, service_by_cpt
from krisnai.synthea.types import PayerInfo, Person, SimClaim, SimLine

CENT = Decimal("0.01")
DEFAULT_FEES = {"99202": "95.00", "99203": "125.00", "99204": "190.00", "99213": "90.00", "99214": "130.00", "99283": "210.00"}
COINSURANCE = Decimal("0.20")
ORDINARY_CARCS = (("50", 0.35), ("16", 0.20), ("18", 0.10), ("97", 0.20), ("4", 0.15))  # ordinary denials (CARC, weight)
DEVIATIONS = (("wrong_denial", 0.30), ("stale_version", 0.25), ("unpublished_rule", 0.20), ("underpay_off_schedule", 0.25))
TRUTH_COLUMNS = ["claim_id", "config_id", "received", "remit_date", "outcome", "carc", "published", "published_reason", "deviation",
                 "pended", "billed", "allowed", "paid"]  # fmt: skip
EXTRA_COLUMNS = ["claim_id", "payer_id", "cause", "cpts", "dx", "dos"]  # the network's second truth file: who decided and why


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PayerConfig:
    """Rates are shares of claims. All zero (the default) means: follow the book, pay the rest, no surprises (S1)."""

    seed: int = 7
    pend_rate: float = 0.0
    deny_rate: float = 0.0
    deviation_rate: float = 0.0
    pay_days: int = 14
    pend_days: int = 21
    underpay_cut: tuple[float, float] = (0.10, 0.25)

    @property
    def config_id(self) -> str:
        return hashlib.sha256(repr(self).encode()).hexdigest()[:8]


@dataclass
class Decision:
    claim: SimClaim
    outcome: str  # paid | underpaid | denied
    reason: str
    carc: str = ""
    deviation: str = ""  # "" when the payer did what it published
    published: str = ""  # paid | denied: what the book says should have happened
    published_reason: str = ""
    pended: bool = False
    received: date | None = None
    remit_date: date | None = None
    issued: bool = False  # an 835 has been written
    cause: str = ""  # network payers only: why (coverage_lapsed, no_prior_auth, bundled, ..., deviation:<kind>, ordinary:<carc>, paid)


@dataclass(frozen=True)
class PayerProfile:
    """How one payer of the network behaves. Its published rules (coverage, authorization, necessity, filing) are in the Knowledge Book."""

    payer_id: str
    name: str
    share: float  # market share weight
    fee_mult: str = "1.00"  # its fee schedule against the base schedule
    pay_days: int = 14
    pend_days: int = 21
    pend_rate: float = 0.08  # share of claims that pend for records
    deny_rate: float = 0.06  # ordinary denials the book cannot predict
    deviation_rate: float = 0.08  # breaks its own published rules
    underpay_rate: float = 0.03  # pays below its own fee schedule
    underpay_cut: tuple[float, float] = (0.10, 0.25)
    ordinary: tuple[tuple[str, float], ...] = (("50", 0.30), ("16", 0.30), ("97", 0.20), ("4", 0.20))  # ordinary denial propensity by CARC
    filing_days: int = 180  # used when the book has no filing rule for the service date
    rules: dict = field(default_factory=dict, hash=False, compare=False)  # the rule spec the Knowledge Book was built from (for display)


@dataclass
class PayerSim:
    payer_id: str
    name: str
    fees: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_FEES))
    deny: dict[str, str] = field(default_factory=dict)  # scripted denials, CPT -> CARC (used by S1)
    members: dict[str, bool] = field(default_factory=dict)  # member id -> coverage active
    config: PayerConfig = field(default_factory=PayerConfig)
    book: Book | None = None
    auths: set[tuple[str, str]] = field(default_factory=set)  # (member, CPT) with an authorization on file
    cases: dict[str, Decision] = field(default_factory=dict)
    profile: PayerProfile | None = None  # set for a payer of the network: decisions then come from the claim's content
    other_primary: set[str] = field(default_factory=set)  # members whose other insurance is primary (this payer denies with CARC 22)
    seen: dict[tuple, str] = field(default_factory=dict)  # (member, service date, CPTs) -> first claim id, to spot duplicates

    def enrol(self, member: str, active: bool = True) -> None:
        self.members[member] = active

    def set_other_primary(self, member: str) -> None:
        self.other_primary.add(member)

    def grant_auth(self, member: str, cpt: str) -> None:
        self.auths.add((member, cpt))

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

    def _published(self, claim: SimClaim) -> tuple[str, str, str]:
        """What the book says should happen: (paid | denied, CARC, reason). The book silent or absent means 'paid'."""
        if self.book is None or claim.dos is None:
            return "paid", "", ""
        cpt, member = claim.lines[0].cpt, claim.patient.ref
        dates = {"service_date": claim.dos}
        if self.members.get(member) is False:
            return "denied", "27", "coverage was not active on the service date"
        cov = self.book.lookup(self.payer_id, "coverage", cpt, dates, claim.submitted)
        if cov.ok and cov.rule.content.get("covered") is False:
            return "denied", "96", f"not covered ({cov.rule.rule_id} v{cov.rule.version})"
        pa = self.book.lookup(self.payer_id, "prior_auth", cpt, dates, claim.submitted)
        if pa.ok and pa.rule.content.get("required") and (member, cpt) not in self.auths:
            return "denied", "197", f"prior authorization required and none on file ({pa.rule.rule_id} v{pa.rule.version})"
        return "paid", "", ""

    def _stale_auth_applies(self, claim: SimClaim) -> bool:
        """True when applying the prior-auth rule of ANOTHER year would require an authorization the claim lacks."""
        if self.book is None or claim.dos is None:
            return False
        cpt = claim.lines[0].cpt
        now = self.book.lookup(self.payer_id, "prior_auth", cpt, {"service_date": claim.dos}, claim.submitted)
        if now.ok and now.rule.content.get("required"):
            return False
        for other in (claim.dos.replace(year=claim.dos.year + 1), claim.dos.replace(year=claim.dos.year - 1)):
            f = self.book.lookup(self.payer_id, "prior_auth", cpt, {"service_date": other}, claim.submitted)
            if f.ok and f.rule.content.get("required"):
                return True
        return False

    def adjudicate(self, claim: SimClaim, received: date, remit_date: date | None = None) -> Decision:
        """Decide a claim. Fills the claim in place, records the decision, and returns it (not yet visible to anyone)."""
        if self.profile is not None:
            return self._adjudicate_net(claim, received, remit_date)
        cfg = self.config
        rng = random.Random(int(hashlib.sha256(f"{cfg.seed}:{claim.claim_id}".encode()).hexdigest(), 16))
        u_dev, u_kind, u_pend, u_deny, u_carc, u_cut = (rng.random() for _ in range(6))
        pub, pub_carc, pub_reason = self._published(claim)
        scripted = {ln.cpt: self.deny[ln.cpt] for ln in claim.lines if ln.cpt in self.deny}
        outcome, carc, reason, deviation, pended = "paid", "", "", "", False
        cut = Decimal("0")
        if scripted:
            outcome, carc, reason = "denied", next(iter(scripted.values())), "scripted denial"
        elif pub == "denied":
            outcome, carc, reason = "denied", pub_carc, pub_reason  # the payer follows what it published
        elif u_dev < cfg.deviation_rate:
            deviation = _pick(DEVIATIONS, u_kind)
            if deviation == "stale_version" and not self._stale_auth_applies(claim):
                deviation = "unpublished_rule"  # no rule changed for this service, so there is no stale version to apply
            if deviation == "underpay_off_schedule":
                lo, hi = cfg.underpay_cut
                cut, outcome = Decimal(str(round(lo + (hi - lo) * u_cut, 3))), "underpaid"
                reason = f"paid {cut * 100:.1f}% under the fee schedule"
            else:
                outcome = "denied"
                carc = {"wrong_denial": "31", "stale_version": "197", "unpublished_rule": "97"}[deviation]
                reason = {"wrong_denial": "coverage was confirmed active but the payer says the patient cannot be identified",
                          "stale_version": "applied a prior-authorization rule that was not in force on the service date",
                          "unpublished_rule": "an edit that is not in the published rules"}[deviation]
        else:
            if u_pend < cfg.pend_rate:
                pended = True
            if u_deny < cfg.deny_rate:
                outcome, carc, reason = "denied", _pick(ORDINARY_CARCS, u_carc), "ordinary denial"
        days = cfg.pay_days + (cfg.pend_days if pended else 0)
        remit = remit_date or (received + timedelta(days=days))
        claim.remit_date = remit
        self._price(claim, outcome, carc, cut)
        d = Decision(claim, outcome, reason, carc, deviation, pub, pub_reason, pended, received, remit)
        self.cases[claim.claim_id] = d
        return d

    # ------------------------------------------------------------------------------------------------ the network payer
    def _filing_limit(self, claim: SimClaim) -> int:
        assert self.profile is not None
        if self.book is not None and claim.dos is not None:
            f = self.book.lookup(self.payer_id, "billing", "FILING", {"service_date": claim.dos}, claim.submitted)
            if f.ok and f.rule.content.get("filing_days"):
                return int(f.rule.content["filing_days"])
        return self.profile.filing_days

    def _published_net(self, claim: SimClaim) -> tuple[str, str, str, str]:
        """What this payer's own rules and the claim's facts say: (paid | denied, CARC, reason, cause). Checked in this order."""
        member, dos, cpts = claim.patient.ref, claim.dos, [ln.cpt for ln in claim.lines]
        dx = [d.replace(".", "") for d in claim.dx]
        if self.members.get(member) is False:
            return "denied", "27", "coverage was not active on the service date", "coverage_lapsed"
        if member in self.other_primary:
            return "denied", "22", "the patient's other insurance is primary; this payer is secondary", "other_primary"
        key = (member, dos, tuple(sorted(cpts)))
        if self.seen.get(key, claim.claim_id) != claim.claim_id:
            return "denied", "18", f"duplicate of claim {self.seen[key]}", "duplicate"
        if dos is not None and claim.submitted is not None:
            limit = self._filing_limit(claim)
            if (claim.submitted - dos).days > limit:
                return "denied", "29", f"filed {(claim.submitted - dos).days} days after the service; the limit is {limit}", "timely_filing"
        if self.book is None or dos is None:
            return "paid", "", "", "paid"
        dates = {"service_date": dos}
        for cpt in cpts:
            cov = self.book.lookup(self.payer_id, "coverage", cpt, dates, claim.submitted)
            if not cov.ok:
                continue
            if cov.rule.content.get("covered") is False:
                return "denied", "96", f"not covered ({cov.rule.rule_id} v{cov.rule.version})", "not_covered"
            into = [p for p in cov.rule.content.get("bundled_into", []) if p in cpts and p != cpt]
            if into:
                return "denied", "97", f"{cpt} is bundled into {into[0]} ({cov.rule.rule_id} v{cov.rule.version})", "bundled"
        for cpt in cpts:
            pa = self.book.lookup(self.payer_id, "prior_auth", cpt, dates, claim.submitted)
            if pa.ok and pa.rule.content.get("required") and (member, cpt) not in self.auths:
                return "denied", "197", f"prior authorization required for {cpt} and none on file ({pa.rule.rule_id} v{pa.rule.version})", "no_prior_auth"
        for cpt in cpts:
            mn = self.book.lookup(self.payer_id, "medical_necessity", cpt, dates, claim.submitted)
            prefixes = mn.rule.content.get("dx_prefixes") if mn.ok else None
            if prefixes and not any(d.startswith(tuple(prefixes)) for d in dx):
                return "denied", "50", f"no diagnosis on the claim supports {cpt} ({mn.rule.rule_id})", "no_medical_necessity"
        return "paid", "", "", "paid"

    def _ordinary_options(self, claim: SimClaim) -> list[tuple[str, float]]:
        """Ordinary denial reasons that make sense for what the claim contains (each CARC only where the content could cause it)."""
        assert self.profile is not None
        svcs = [s for s in (service_by_cpt(ln.cpt) for ln in claim.lines) if s is not None]
        unspecified = any((c := condition_by_icd(_dotted(d))) is not None and c.unspecified for d in claim.dx)
        applies = {
            "50": True,
            "16": unspecified or any(s.needs_time for s in svcs),
            "97": len(claim.lines) > 1 or any(s.family in ("procedure", "injection", "lab") for s in svcs),
            "4": any(s.needs_laterality or s.family in ("procedure", "injection") for s in svcs),
        }
        opts = [(c, w) for c, w in self.profile.ordinary if applies.get(c, True)]
        return opts or [("16", 1.0)]

    def _adjudicate_net(self, claim: SimClaim, received: date, remit_date: date | None) -> Decision:
        prof, cfg = self.profile, self.config
        assert prof is not None
        rng = random.Random(int(hashlib.sha256(f"{cfg.seed}:{self.payer_id}:{claim.claim_id}".encode()).hexdigest(), 16))
        u_dev, u_kind, u_pend, u_deny, u_carc, u_cut, u_under = (rng.random() for _ in range(7))
        pub, pub_carc, pub_reason, cause = self._published_net(claim)
        outcome, carc, reason, deviation, pended = "paid", "", "", "", False
        cut = Decimal("0")
        if pub == "denied":
            outcome, carc, reason = "denied", pub_carc, pub_reason
        elif u_dev < cfg.deviation_rate:
            deviation = _pick(DEVIATIONS, u_kind)
            if deviation == "stale_version" and not self._stale_auth_applies(claim):
                deviation = "unpublished_rule"
            if deviation == "underpay_off_schedule":
                outcome, cut = "underpaid", _cut(prof.underpay_cut, u_cut)
                reason = f"paid {cut * 100:.1f}% under the fee schedule"
            else:
                outcome = "denied"
                carc = {"wrong_denial": "31", "stale_version": "197", "unpublished_rule": "97"}[deviation]
                reason = {"wrong_denial": "coverage was confirmed active but the payer says the patient cannot be identified",
                          "stale_version": "applied a prior-authorization rule that was not in force on the service date",
                          "unpublished_rule": "an edit that is not in the published rules"}[deviation]
            cause = f"deviation:{deviation}"
        else:
            if u_under < prof.underpay_rate:
                deviation, outcome, cut = "underpay_off_schedule", "underpaid", _cut(prof.underpay_cut, u_cut)
                reason, cause = f"paid {cut * 100:.1f}% under the fee schedule", "deviation:underpay_off_schedule"
            elif u_deny < cfg.deny_rate:
                outcome, carc, reason = "denied", _pick(tuple(self._ordinary_options(claim)), u_carc), "ordinary denial"
                cause = f"ordinary:{carc}"
            big = claim.billed >= Decimal("300")  # a costly claim is more likely to be pulled for records
            pended = u_pend < min(1.0, cfg.pend_rate * (2.0 if big else 1.0))
        days = cfg.pay_days + (cfg.pend_days if pended else 0)
        remit = remit_date or (received + timedelta(days=days))
        claim.remit_date = remit
        self._price(claim, outcome, carc, cut)
        key = (claim.patient.ref, claim.dos, tuple(sorted(ln.cpt for ln in claim.lines)))
        self.seen.setdefault(key, claim.claim_id)
        d = Decision(claim, outcome, reason, carc, deviation, pub, pub_reason, pended, received, remit, cause=cause)
        self.cases[claim.claim_id] = d
        return d

    def truth_extra_csv(self) -> str:
        """Which payer decided each claim and why: claim id, payer, cause, CPTs, diagnoses. Kept apart from the truth log's columns."""
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(EXTRA_COLUMNS)
        for cid in sorted(self.cases):
            d = self.cases[cid]
            w.writerow([cid, self.payer_id, d.cause, "|".join(ln.cpt for ln in d.claim.lines), "|".join(d.claim.dx), d.claim.dos])
        return buf.getvalue()

    def decide(self, claim: SimClaim, remit_date: date) -> Decision:
        """S1 entry point: adjudicate with a fixed remit date."""
        return self.adjudicate(claim, claim.submitted, remit_date)

    def _price(self, claim: SimClaim, outcome: str, carc: str, cut: Decimal) -> None:
        if outcome == "denied":
            claim.scenario, claim.carc = "denial", carc
            for ln in claim.lines:
                ln.allowed = money(Decimal(self.fees.get(ln.cpt, "0")) * ln.units)
                ln.paid = ln.pr = Decimal("0")
                ln.cas = [("CO", carc, ln.billed)]
            return
        claim.scenario = "clean"
        for ln in claim.lines:
            fee = Decimal(self.fees.get(ln.cpt, str(ln.billed)))
            sched = money(min(fee * ln.units, ln.billed))
            ln.allowed = money(sched * (1 - cut))
            ln.pr = money(ln.allowed * COINSURANCE)
            ln.paid = ln.allowed - ln.pr
            ln.cas = [("CO", "45", ln.billed - ln.allowed), ("PR", "2", ln.pr)]

    # ------------------------------------------------------------------------------------------------ over time
    def remits_due(self, day: date) -> list[Decision]:
        """Decisions whose remittance date has come and that have not had an 835 yet; marks them issued."""
        due = sorted((d for d in self.cases.values() if not d.issued and d.remit_date and d.remit_date <= day),
                     key=lambda d: d.claim.claim_id)  # fmt: skip
        for d in due:
            d.issued = True
        return due

    def status(self, claim_id: str, day: date) -> tuple[str, str, Decimal, str, str, bool]:
        """What a status request or the portal shows on `day`: (category, code, paid, payer claim no, reason, records_open)."""
        d = self.cases.get(claim_id)
        if d is None:
            return "P1", "21", Decimal(0), "", "In normal processing", False
        no = d.claim.payer_claim_no
        if d.remit_date and day < d.remit_date:
            if d.pended:
                return "P1", "21", Decimal(0), no, "Records requested: medical records for the date of service", True
            return "P1", "21", Decimal(0), no, "In normal processing", False
        if d.outcome == "denied":
            return "F2", "3", Decimal(0), no, "Denied: see remittance advice", False
        return "F1", "65", d.claim.paid, no, "Finalized: see remittance advice", False

    # ------------------------------------------------------------------------------------------------ the truth log
    def truth_csv(self) -> str:
        """One row per decision, sorted by claim id: identical for the same seed, config and claims."""
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=TRUTH_COLUMNS, lineterminator="\n")
        w.writeheader()
        for cid in sorted(self.cases):
            d = self.cases[cid]
            w.writerow({"claim_id": cid, "config_id": self.config.config_id, "received": d.received, "remit_date": d.remit_date,
                        "outcome": d.outcome, "carc": d.carc, "published": d.published, "published_reason": d.published_reason,
                        "deviation": d.deviation, "pended": int(d.pended), "billed": d.claim.billed,
                        "allowed": sum((ln.allowed for ln in d.claim.lines), Decimal(0)), "paid": d.claim.paid})  # fmt: skip
        return buf.getvalue()


def _cut(bounds: tuple[float, float], u: float) -> Decimal:
    lo, hi = bounds
    return Decimal(str(round(lo + (hi - lo) * u, 3)))


def _dotted(icd: str) -> str:
    """'J029' back to 'J02.9' (the claim carries ICD-10 without the dot)."""
    return icd if "." in icd or len(icd) <= 3 else f"{icd[:3]}.{icd[3:]}"


def _pick(weighted: tuple[tuple[str, float], ...], u: float) -> str:
    total = sum(w for _, w in weighted)
    acc = 0.0
    for key, w in weighted:
        acc += w / total
        if u < acc:
            return key
    return weighted[-1][0]


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
