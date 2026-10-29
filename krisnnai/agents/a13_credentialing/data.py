"""Loads enrollments, services and screenings into the plain shapes the credentialing rules use."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a13_credentialing import config
from krisnnai.agents.a13_credentialing.rules import Enroll, Service
from krisnnai.agents.a15_lite.expected import UNPRICED, Pricer


def enroll_rows(session: Session, provider_id: int, payer_id: int) -> list[Enroll]:
    return [
        Enroll(e.status, e.submitted_on, e.effective_on, e.expires_on, e.status_on)
        for e in session.scalars(
            select(m.Enrollment).where(m.Enrollment.provider_id == provider_id, m.Enrollment.payer_id == payer_id)
        )
    ]


def services(
    session: Session, provider_id: int, payer_id: int, payer_code: str, as_of: date, pricer: Pricer | None
) -> list[Service]:
    """Visits by this provider for this payer in the service window, priced when a pricer is given."""
    start = as_of - timedelta(days=config.SERVICE_WINDOW_DAYS)
    out = []
    for v in session.scalars(
        select(m.Visit).where(
            m.Visit.provider_id == provider_id, m.Visit.payer_id == payer_id,
            m.Visit.service_date > start, m.Visit.service_date <= as_of,
        )
    ):
        amount = Decimal(0)
        if pricer is not None:
            value, basis = pricer.payer_expected(payer_code, v.cpt, "", v.service_date, v.units)
            amount = Decimal(0) if basis == UNPRICED else value
        out.append(Service(v.service_date, amount))
    return out


class Book:
    """Everything the sweeper needs, read once: enrollment history, service dates and screenings."""

    def __init__(self, session: Session):
        self.providers = {p.id: p.npi for p in session.scalars(select(m.Provider))}
        self.payers = {p.id: p.payer_id_code for p in session.scalars(select(m.Payer))}
        self.enrollments: dict[tuple[int, int], list[Enroll]] = defaultdict(list)
        for e in session.scalars(select(m.Enrollment)):
            self.enrollments[(e.provider_id, e.payer_id)].append(
                Enroll(e.status, e.submitted_on, e.effective_on, e.expires_on, e.status_on)
            )
        self.service_dates: dict[tuple[int, int], list[date]] = defaultdict(list)
        for provider_id, payer_id, when in session.execute(
            select(m.Visit.provider_id, m.Visit.payer_id, m.Visit.service_date)
        ):
            self.service_dates[(provider_id, payer_id)].append(when)
        self.screenings: dict[int, list[tuple[date, str]]] = defaultdict(list)
        for s in session.scalars(select(m.ProviderScreening)):
            self.screenings[s.provider_id].append((s.screened_on, s.result))
        self.pairs = sorted(set(self.enrollments) | set(self.service_dates))
        self.screened = sorted(set(self.screenings) | {p for p, _ in self.pairs})

    def unpriced_services(self, pair: tuple[int, int]) -> list[Service]:
        return [Service(d, Decimal(0)) for d in self.service_dates.get(pair, [])]

    def latest_screening(self, provider_id: int, as_of: date) -> tuple[str | None, date | None]:
        known = [r for r in self.screenings.get(provider_id, []) if r[0] <= as_of]
        if not known:
            return None, None
        when, result = max(known)
        return result, when
