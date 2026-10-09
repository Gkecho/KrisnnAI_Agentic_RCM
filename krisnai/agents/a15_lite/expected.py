"""Expected payment: fee schedule x units, with a flagged fallback, and the patient share learned per payer."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from statistics import median

from krisnai.agents.a15_lite.config import A15Config
from krisnai.agents.a15_lite.snapshot import Fee, Snapshot

CENTS = Decimal("0.01")
FEE = "fee_schedule"
FALLBACK = "fallback"
UNPRICED = "unpriced"


def money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


class Pricer:
    """Prices a service. Allowed amount comes from the contract fee schedule; when there is no row the payer's own
    median paid-per-unit for that CPT is used and the result is flagged `fallback`. The patient share (coinsurance)
    is learned from each payer's paid lines, so nothing about it is hard-coded."""

    def __init__(self, snap: Snapshot, cfg: A15Config):
        self.cfg = cfg
        self._fees: dict[tuple[str, str, str], list[Fee]] = defaultdict(list)
        for f in snap.fees:
            self._fees[(f.payer, f.cpt, f.modifier)].append(f)
        for rows in self._fees.values():
            rows.sort(key=lambda f: f.effective)

        per_unit: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
        share_pr: dict[str, Decimal] = defaultdict(Decimal)
        share_allowed: dict[str, Decimal] = defaultdict(Decimal)
        for r in snap.remits:
            if r.status == "22":
                continue
            for ln in r.lines:
                if ln.paid <= 0:
                    continue
                per_unit[(r.payer, ln.cpt)].append((ln.paid + ln.patient_share) / ln.units)
                # coinsurance = patient share / contract allowed. Dividing by what was paid instead would
                # inflate it on underpaid lines, where the payer paid less but the patient still owes their share.
                allowed, basis = self._fee_allowed(r.payer, ln.cpt, ln.modifier, ln.service_date, ln.units)
                if allowed:
                    share_pr[r.payer] += ln.patient_share
                    share_allowed[r.payer] += allowed
        self._median = {k: median(v) for k, v in per_unit.items()}
        places = Decimal(1).scaleb(-cfg.share_places)
        self._share = {
            p: (share_pr[p] / share_allowed[p]).quantize(places, rounding=ROUND_HALF_UP)
            for p in share_allowed
            if share_allowed[p] > 0
        }
        all_allowed = sum(share_allowed.values(), Decimal(0))
        self._default_share = (
            (sum(share_pr.values(), Decimal(0)) / all_allowed).quantize(places, rounding=ROUND_HALF_UP)
            if all_allowed > 0
            else Decimal(0)
        )

    def share(self, payer: str) -> Decimal:
        return self._share.get(payer, self._default_share)

    def _fee_allowed(self, payer: str, cpt: str, modifier: str, dos: date | None, units: Decimal):
        for f in reversed(self._fees.get((payer, cpt, modifier), [])):
            if dos is None or (f.effective <= dos and (f.end is None or f.end >= dos)):
                return money(f.allowed * units), FEE
        return None, UNPRICED

    def allowed(
        self, payer: str, cpt: str, modifier: str, dos: date | None, units: Decimal
    ) -> tuple[Decimal | None, str]:
        """(allowed amount, basis). basis is fee_schedule, fallback or unpriced (amount None)."""
        amount, basis = self._fee_allowed(payer, cpt, modifier, dos, units)
        if amount is not None:
            return amount, basis
        mid = self._median.get((payer, cpt))
        if mid is not None:
            return money(mid * units), FALLBACK
        return None, UNPRICED

    def payer_expected(self, payer: str, cpt: str, modifier: str, dos: date | None, units: Decimal):
        """What the payer should pay (allowed less the patient's share), with its basis."""
        allowed, basis = self.allowed(payer, cpt, modifier, dos, units)
        if allowed is None:
            return Decimal(0), basis
        return allowed - money(allowed * self.share(payer)), basis


def worst_basis(bases: list[str]) -> str:
    for b in (UNPRICED, FALLBACK):
        if b in bases:
            return b
    return FEE
