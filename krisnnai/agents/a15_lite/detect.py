"""Find the leaks. Pure reads over a Snapshot: nothing here changes data, and nothing is "recovered", only detected."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from krisnnai.agents.a15_lite import config as c
from krisnnai.agents.a15_lite.config import A15Config
from krisnnai.agents.a15_lite.expected import FALLBACK, FEE, Pricer, money, worst_basis
from krisnnai.agents.a15_lite.snapshot import Claim, Remit, Snapshot

RECOVERABLE = "recoverable"
STRUCTURAL = "structural"


@dataclass
class Finding:
    type: str
    claim: str  # CLM01, or "" for an unbilled visit
    visit: str  # PM visit id, or ""
    line_no: int | None
    payer: str
    provider: str
    location: str
    cpt: str
    carc: str
    category: str
    expected_amount: Decimal
    status: str  # recoverable | structural
    deadline: date | None
    agent: str
    basis: str  # fee_schedule | fallback | unpriced
    reason: str

    @property
    def key(self) -> tuple:
        return (self.type, self.claim or self.visit, self.line_no if self.type == c.UNDERPAYMENT else None)

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


def _status(as_of: date, anchor: date | None, window: int) -> tuple[str, date | None]:
    if anchor is None:
        return STRUCTURAL, None
    deadline = anchor + timedelta(days=window)
    return (RECOVERABLE if as_of <= deadline else STRUCTURAL), deadline


def _top_reason(items) -> str:
    """The CARC with the largest dollar amount among non-patient adjustments."""
    totals: Counter = Counter()
    for group, reason, amount in items:
        if group != "PR":
            totals[reason] += abs(amount)
    return totals.most_common(1)[0][0] if totals else ""


def detect(snap: Snapshot, cfg: A15Config | None = None) -> list[Finding]:
    cfg = cfg or A15Config()
    pricer = Pricer(snap, cfg)
    out: list[Finding] = []
    out += _denials(snap, cfg, pricer)
    flagged: set[int] = set()
    out += _underpayments(snap, cfg, pricer, flagged)
    out += _unexplained(snap, cfg, flagged)
    out += _rejections(snap, cfg, pricer)
    out += _unbilled(snap, cfg, pricer)
    out.sort(key=lambda f: (f.type, f.claim, f.visit, f.line_no or 0))
    return out


def _denials(snap: Snapshot, cfg: A15Config, pricer: Pricer) -> list[Finding]:
    out = []
    for claim_id, remit in snap.first_remit().items():
        claim = snap.claims.get(claim_id)
        if claim is None or remit.status != "4":
            continue
        carc = _top_reason([a for ln in remit.lines for a in ln.adjustments] + remit.claim_adjustments)
        category = c.CARC_CATEGORY.get(carc, "other")
        amount, bases = Decimal(0), []
        for ln in remit.lines:
            value, basis = pricer.payer_expected(
                remit.payer, ln.cpt, ln.modifier, ln.service_date or claim.service_date, ln.units
            )
            amount += value
            bases.append(basis)
        if category == "timely_filing":
            status, deadline = STRUCTURAL, None  # the filing window has already been missed
            ftype, agent = c.TIMELY_FILING, c.AGENT_BY_TYPE[c.TIMELY_FILING]
            why = "CARC 29 timely filing loss"
        else:
            window = cfg.appeal_window(remit.payer)
            status, deadline = _status(snap.as_of, remit.payment_date, window)
            ftype, agent = c.DENIAL, c.AGENT_BY_CATEGORY[category]
            why = f"denied {(snap.as_of - remit.payment_date).days}d before as-of, appeal window {window}d"
        out.append(
            Finding(
                ftype,
                claim.sid,
                "",
                None,
                remit.payer,
                claim.provider,
                claim.location,
                "",
                carc,
                category,
                money(amount),
                status,
                deadline,
                agent,
                worst_basis(bases),
                why,
            )
        )
    return out


def _paid_lines(snap: Snapshot):
    for r in snap.remits:
        if r.status == "22" or r.claim_id not in snap.claims:
            continue
        for ln in r.lines:
            if ln.paid > 0:
                yield r, snap.claims[r.claim_id], ln


def _underpayments(snap: Snapshot, cfg: A15Config, pricer: Pricer, flagged: set) -> list[Finding]:
    out = []
    for r, claim, ln in _paid_lines(snap):
        allowed, basis = pricer.allowed(r.payer, ln.cpt, ln.modifier, ln.service_date or claim.service_date, ln.units)
        if allowed is None:
            continue
        gap = money(allowed - (ln.paid + ln.patient_share))
        floor = Decimal(0) if basis == FEE else money(allowed * cfg.fallback_min_shortfall)
        if gap <= 0 or (basis == FALLBACK and gap < floor):
            continue
        window = cfg.appeal_window(r.payer)
        status, deadline = _status(snap.as_of, r.payment_date, window)
        flagged.add(ln.id)
        out.append(
            Finding(
                c.UNDERPAYMENT,
                claim.sid,
                "",
                ln.line_number,
                r.payer,
                claim.provider,
                claim.location,
                ln.cpt,
                _top_reason(ln.adjustments),
                "",
                gap,
                status,
                deadline,
                c.AGENT_BY_TYPE[c.UNDERPAYMENT],
                basis,
                f"paid {(snap.as_of - r.payment_date).days}d before as-of, appeal window {window}d",
            )
        )
    return out


def _unexplained(snap: Snapshot, cfg: A15Config, flagged: set) -> list[Finding]:
    """Non-contractual reductions on lines that were paid and are not already counted as an underpayment."""
    out = []
    for r, claim, ln in _paid_lines(snap):
        if ln.id in flagged:
            continue
        odd = [(g, rc, a) for g, rc, a in ln.adjustments if g in ("CO", "OA", "PI") and rc != "45"]
        total = sum((a for _, _, a in odd), Decimal(0))
        if total <= 0:
            continue
        status, deadline = _status(snap.as_of, r.payment_date, cfg.appeal_window(r.payer))
        out.append(
            Finding(
                c.UNEXPLAINED_ADJUSTMENT,
                claim.sid,
                "",
                ln.line_number,
                r.payer,
                claim.provider,
                claim.location,
                ln.cpt,
                _top_reason(odd),
                "",
                money(total),
                status,
                deadline,
                c.AGENT_BY_TYPE[c.UNEXPLAINED_ADJUSTMENT],
                FEE,
                "adjustment on a paid line other than the contractual write-off (CARC 45)",
            )
        )
    return out


def _claim_expected(claim: Claim, payer: str, pricer: Pricer) -> tuple[Decimal, str]:
    amount, bases = Decimal(0), []
    for ln in claim.lines:
        value, basis = pricer.payer_expected(
            payer, ln.cpt, ln.modifier, ln.service_date or claim.service_date, ln.units
        )
        amount += value
        bases.append(basis)
    return money(amount), worst_basis(bases)


def _rejections(snap: Snapshot, cfg: A15Config, pricer: Pricer) -> list[Finding]:
    answered = {r.claim_id for r in snap.remits if r.claim_id is not None}
    out = []
    for claim_id in sorted(snap.rejected_claim_ids - answered):
        claim = snap.claims[claim_id]
        amount, basis = _claim_expected(claim, claim.payer, pricer)
        window = cfg.filing_window(claim.payer)
        status, deadline = _status(snap.as_of, claim.service_date, window)
        age = (snap.as_of - claim.service_date).days if claim.service_date else None
        out.append(
            Finding(
                c.REJECTION,
                claim.sid,
                "",
                None,
                claim.payer,
                claim.provider,
                claim.location,
                "",
                "",
                "",
                amount,
                status,
                deadline,
                c.AGENT_BY_TYPE[c.REJECTION],
                basis,
                f"rejected by the 999/277CA, service {age}d before as-of, filing limit {window}d",
            )
        )
    return out


def _unbilled(snap: Snapshot, cfg: A15Config, pricer: Pricer) -> list[Finding]:
    out = []
    for v in snap.visits:
        if (v.payer, v.patient_ref_id, v.service_date, v.cpt) in snap.billed_keys:
            continue
        amount, basis = pricer.payer_expected(v.payer, v.cpt, "", v.service_date, v.units)
        window = cfg.filing_window(v.payer)
        status, deadline = _status(snap.as_of, v.service_date, window)
        out.append(
            Finding(
                c.UNBILLED_VISIT,
                "",
                v.ref,
                None,
                v.payer,
                v.provider,
                "",
                v.cpt,
                "",
                "",
                money(amount),
                status,
                deadline,
                c.AGENT_BY_TYPE[c.UNBILLED_VISIT],
                basis,
                f"visit never billed, service {(snap.as_of - v.service_date).days}d before as-of, "
                f"filing limit {window}d",
            )
        )
    return out


__all__ = ["Finding", "RECOVERABLE", "STRUCTURAL", "Remit", "detect"]
