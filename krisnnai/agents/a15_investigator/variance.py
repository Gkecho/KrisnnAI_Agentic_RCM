"""Realisation against contract by slice, recent window vs baseline, from one Snapshot.

Per remit line (matched, not reversed, priced from the fee schedule): expected = the contract allowed amount,
actual = paid plus the patient's share (a denied line pays nothing). Realisation = actual / expected. A slice (a payer,
or a payer and a CPT) is flagged when realisation fell by the configured number of points with enough lines and
dollars behind it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from krisnnai.agents.a15_investigator import config
from krisnnai.agents.a15_lite.config import A15Config
from krisnnai.agents.a15_lite.expected import FEE, Pricer
from krisnnai.agents.a15_lite.snapshot import Remit, RemitLine, Snapshot

ZERO = Decimal(0)


@dataclass
class Line:
    remit: Remit
    line: RemitLine
    claim_sid: str
    payer: str
    cpt: str
    paid_on: date
    expected: Decimal
    actual: Decimal


@dataclass
class Slice:
    key: str  # "payer" or "payer|cpt"
    payer: str
    cpt: str | None
    baseline: Decimal
    recent: Decimal
    expected_recent: Decimal
    lines_recent: int
    lines_baseline: int
    shortfall_lines: list[Line] = field(default_factory=list)

    @property
    def drop(self) -> Decimal:
        return self.baseline - self.recent

    @property
    def impact(self) -> Decimal:
        return (self.drop * self.expected_recent).quantize(Decimal("0.01"))


def priced_lines(snap: Snapshot, cfg: A15Config | None = None) -> list[Line]:
    pricer = Pricer(snap, cfg or A15Config())
    out: list[Line] = []
    for r in snap.remits:
        claim = snap.claims.get(r.claim_id) if r.claim_id is not None else None
        if claim is None or r.status == "22":
            continue
        for ln in r.lines:
            dos = ln.service_date or claim.service_date
            allowed, basis = pricer.allowed(r.payer, ln.cpt, ln.modifier, dos, ln.units)
            if allowed is None or basis != FEE or allowed <= 0:
                continue
            out.append(Line(r, ln, claim.sid, r.payer, ln.cpt, r.payment_date, allowed, ln.paid + ln.patient_share))
    return out


def _realisation(lines: list[Line]) -> tuple[Decimal, Decimal]:
    expected = sum((x.expected for x in lines), ZERO)
    actual = sum((x.actual for x in lines), ZERO)
    return (actual / expected if expected > 0 else ZERO), expected


def slices(snap: Snapshot, as_of: date | None = None, cfg: A15Config | None = None) -> list[Slice]:
    """Every flagged slice at `as_of`, the largest dollar impact first."""
    as_of = as_of or snap.as_of
    recent_from = as_of - timedelta(days=config.RECENT_DAYS)
    base_from = recent_from - timedelta(days=config.BASELINE_DAYS)
    lines = [x for x in priced_lines(snap, cfg) if base_from < x.paid_on <= as_of]
    groups: dict[tuple[str, str | None], tuple[list[Line], list[Line]]] = {}
    for x in lines:
        for key in ((x.payer, None), (x.payer, x.cpt)):
            recent, base = groups.setdefault(key, ([], []))
            (recent if x.paid_on > recent_from else base).append(x)
    out: list[Slice] = []
    for (payer, cpt), (recent, base) in groups.items():
        if len(recent) < config.MIN_LINES or len(base) < config.MIN_LINES:
            continue
        r_real, r_exp = _realisation(recent)
        b_real, _ = _realisation(base)
        if r_exp < config.MIN_EXPECTED or b_real - r_real < config.DROP_POINTS:
            continue
        key = payer if cpt is None else f"{payer}|{cpt}"
        out.append(Slice(key, payer, cpt, b_real, r_real, r_exp, len(recent), len(base),
                         [x for x in recent if x.expected - x.actual > Decimal("0.005")]))  # fmt: skip
    out.sort(key=lambda s: (-s.impact, s.key))
    return out
