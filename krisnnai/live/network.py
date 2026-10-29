# ruff: noqa: E501
"""The payer network of the live stream: six invented payers with clearly different behaviour. Nothing here is a real payer.

Each payer has a profile (market share, fee schedule, how fast it pays, how often it pends, denies, underpays or breaks its own
published rules) and a rule set in the Knowledge Book (coverage, prior authorization, bundling edits, medical-necessity edits,
timely-filing limit, appeal window, several of them changing on 2026-01-01). A visit's payer is picked at random, in proportion
to market share, and deterministically for a seed and a key: nobody chooses it from a list.

A payer then decides each claim from what the claim contains (see `PayerSim._adjudicate_net`): codes, units, diagnoses, whether
an authorization is on file, coverage, duplicates, filing age, plus seeded randomness. All rates are demo settings, not payer statistics.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal

from krisnnai.knowledge.book import Book
from krisnnai.knowledge.demo import NETWORK_RULES, network_book
from krisnnai.live.catalog import SERVICES
from krisnnai.live.payer import PayerConfig, PayerProfile, PayerSim

BASE_ALLOWED = Decimal("0.82")  # the base fee schedule is 82% of the practice's charge

PROFILES: tuple[PayerProfile, ...] = (
    PayerProfile("SYNAETNA", "SYNAETNA Demo Payer", 0.26, fee_mult="1.00", pay_days=14, pend_days=21, pend_rate=0.08, deny_rate=0.07, deviation_rate=0.09, underpay_rate=0.03, filing_days=365,
                 ordinary=(("50", 0.30), ("16", 0.30), ("97", 0.20), ("4", 0.20))),
    PayerProfile("SYNCIGNA", "SYNCIGNA Demo Payer", 0.20, fee_mult="1.08", pay_days=21, pend_days=28, pend_rate=0.10, deny_rate=0.10, deviation_rate=0.12, underpay_rate=0.04, filing_days=180,
                 ordinary=(("50", 0.35), ("16", 0.15), ("97", 0.30), ("4", 0.20))),
    PayerProfile("SYNUNITED", "SYNUNITED Demo Payer", 0.24, fee_mult="0.97", pay_days=12, pend_days=21, pend_rate=0.15, deny_rate=0.12, deviation_rate=0.10, underpay_rate=0.05, filing_days=180,
                 ordinary=(("50", 0.40), ("16", 0.20), ("97", 0.25), ("4", 0.15))),
    PayerProfile("SYNBLUE", "SYNBLUE Demo Payer", 0.14, fee_mult="0.93", pay_days=18, pend_days=14, pend_rate=0.06, deny_rate=0.05, deviation_rate=0.06, underpay_rate=0.02, filing_days=365,
                 ordinary=(("50", 0.20), ("16", 0.45), ("97", 0.10), ("4", 0.25))),
    PayerProfile("SYNMCARE", "SYNMCARE Demo Payer", 0.10, fee_mult="0.80", pay_days=14, pend_days=30, pend_rate=0.07, deny_rate=0.08, deviation_rate=0.04, underpay_rate=0.01, filing_days=365,
                 ordinary=(("50", 0.45), ("16", 0.20), ("97", 0.20), ("4", 0.15))),
    PayerProfile("SYNMCAID", "SYNMCAID Demo Payer", 0.06, fee_mult="0.65", pay_days=30, pend_days=30, pend_rate=0.20, deny_rate=0.14, deviation_rate=0.14, underpay_rate=0.06, filing_days=180,
                 ordinary=(("16", 0.40), ("50", 0.25), ("4", 0.20), ("97", 0.15))),
)
PAYER_IDS = tuple(p.payer_id for p in PROFILES)


def fee_schedule(profile: PayerProfile) -> dict[str, str]:
    """The payer's allowed amount for every service in the catalog (read at call time, so new catalog entries are priced)."""
    mult = Decimal(profile.fee_mult)
    return {s.cpt: str((Decimal(s.fee) * BASE_ALLOWED * mult).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) for s in SERVICES}


class Network:
    """Six payers sharing one Knowledge Book. `pend_rate`, `deny_rate` and `deviation_rate` left as None keep each payer's own rate;
    a number overrides it for every payer (0.0 switches that kind of trouble off, 1.0 forces it)."""

    def __init__(self, seed: int = 7, pend_rate: float | None = None, deny_rate: float | None = None, deviation_rate: float | None = None,
                 profiles: tuple[PayerProfile, ...] = PROFILES, book: Book | None = None):  # fmt: skip
        self.seed = seed
        self.profiles = {p.payer_id: replace(p, rules=NETWORK_RULES.get(p.payer_id, {})) for p in profiles}
        self.book = book if book is not None else network_book()
        self.payers: dict[str, PayerSim] = {}
        for pid, p in self.profiles.items():
            dev = p.deviation_rate if deviation_rate is None else deviation_rate
            under = p.underpay_rate if deviation_rate is None else (p.underpay_rate * deviation_rate / p.deviation_rate if p.deviation_rate else 0.0)
            eff = replace(p, underpay_rate=min(1.0, under))
            cfg = PayerConfig(seed=seed, pend_rate=p.pend_rate if pend_rate is None else pend_rate, deny_rate=p.deny_rate if deny_rate is None else deny_rate,
                              deviation_rate=dev, pay_days=p.pay_days, pend_days=p.pend_days, underpay_cut=p.underpay_cut)  # fmt: skip
            self.payers[pid] = PayerSim(pid, p.name, fees=fee_schedule(p), config=cfg, book=self.book, profile=eff)

    def pick_payer(self, visit_key: str) -> str:
        """Weighted random by market share, the same payer for the same (seed, key) every time."""
        u = int(hashlib.sha256(f"{self.seed}:payer:{visit_key}".encode()).hexdigest(), 16) / 16**64
        total = sum(p.share for p in self.profiles.values())
        acc = 0.0
        for pid, p in self.profiles.items():
            acc += p.share / total
            if u < acc:
                return pid
        return next(reversed(self.profiles))

    def payer(self, payer_id: str) -> PayerSim:
        return self.payers[payer_id]

    def name(self, payer_id: str) -> str:
        return self.profiles[payer_id].name

    def fee_schedule_rows(self, effective: str = "2020-01-01") -> list[str]:
        """Lines of the practice's contract fee schedule file for every payer (A10 compares payments to it)."""
        rows = []
        for pid, sim in self.payers.items():
            rows += [f"{pid},{cpt},,{amt},{effective}" for cpt, amt in sorted(sim.fees.items())]
        return rows
