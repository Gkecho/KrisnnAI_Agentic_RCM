"""Expected payer payment for a set of lines, as of a date. Shared by the agents that need a dollar figure.

Used by A6, A7 and A8.

The data is loaded once per tenant (until a table grows) and each day's pricer is built from the rows known by that day,
so replaying events spread over a long history reads the database once, not once per day.
Lines can be claim lines or remit lines: anything with cpt, modifier_1, units, charge and service_date.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import krisnnai.model as m

from krisnnai.agents.a15_lite.config import A15Config
from krisnnai.agents.a15_lite.expected import FEE, UNPRICED, Pricer, money, worst_basis
from krisnnai.agents.a15_lite.snapshot import load_snapshot

BILLED_FALLBACK = "billed_fallback"


class ClaimPricer:
    def __init__(self) -> None:
        self._pricers: dict[tuple[int, date], Pricer] = {}
        self._source: dict[int, tuple[tuple, list, list]] = {}  # tenant -> (version, remits, fees), everything known

    @staticmethod
    def _version(session: Session) -> tuple:
        return (
            session.scalar(select(func.count()).select_from(m.Remit)),
            session.scalar(select(func.max(m.Remit.id))),
            session.scalar(select(func.count()).select_from(m.FeeSchedule)),
            session.scalar(select(func.max(m.FeeSchedule.id))),
        )

    def pricer(self, session: Session, as_of: date) -> Pricer:
        """The cached A15 pricer for this tenant and day, built from the rows known by that day."""
        tenant = session.info["tenant_id"]
        version = self._version(session)
        have = self._source.get(tenant)
        if have is None or have[0] != version:  # first use, or rows were added since: reload and drop the day cache
            snap = load_snapshot(session.get_bind(), tenant, date.max)
            self._source[tenant] = (version, snap.remits, snap.fees)
            self._pricers = {k: v for k, v in self._pricers.items() if k[0] != tenant}
            have = self._source[tenant]
        key = (tenant, as_of)
        if key not in self._pricers:
            view = SimpleNamespace(
                remits=[r for r in have[1] if r.known is not None and r.known <= as_of],
                fees=[f for f in have[2] if f.effective <= as_of],
            )
            self._pricers[key] = Pricer(view, A15Config())
        return self._pricers[key]

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
        pricer = self.pricer(session, as_of)
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
