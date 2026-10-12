"""Expected payer payment for a set of lines, as of a date. Shared by the agents that need a dollar figure.

Used by A6, A7 and A8.

One A15 snapshot is loaded per tenant and as-of date and reused, so replaying many events on one day stays cheap.
Lines can be claim lines or remit lines: anything with cpt, modifier_1, units, charge and service_date.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from krisnai.agents.a15_lite.config import A15Config
from krisnai.agents.a15_lite.expected import FEE, UNPRICED, Pricer, money, worst_basis
from krisnai.agents.a15_lite.snapshot import load_snapshot

BILLED_FALLBACK = "billed_fallback"


class ClaimPricer:
    def __init__(self) -> None:
        self._pricers: dict[tuple[int, date], Pricer] = {}

    def price(
        self,
        session: Session,
        as_of: date,
        payer_code: str,
        lines,
        fallback_date: date | None = None,
        empty_default: Decimal | None = None,
    ) -> tuple[Decimal, str]:
        """(amount, basis). A line the fee schedule and history cannot price counts at its billed charge.

        `empty_default` is what to return when there are no lines at all (for example the claim's total charge).
        """
        key = (session.info["tenant_id"], as_of)
        if key not in self._pricers:
            self._pricers[key] = Pricer(load_snapshot(session.get_bind(), key[0], key[1]), A15Config())
        pricer = self._pricers[key]
        total, bases = Decimal(0), []
        for ln in lines:
            value, basis = pricer.payer_expected(
                payer_code, ln.cpt, ln.modifier_1 or "", ln.service_date or fallback_date, ln.units or Decimal(1)
            )
            if basis == UNPRICED:
                value, basis = ln.charge, BILLED_FALLBACK
            total += value
            bases.append(basis)
        if not bases:
            return (money(empty_default), BILLED_FALLBACK) if empty_default is not None else (money(total), FEE)
        if BILLED_FALLBACK in bases:
            return money(total), BILLED_FALLBACK
        return money(total), worst_basis(bases)
