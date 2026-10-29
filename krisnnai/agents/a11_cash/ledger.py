"""Loads payments, remits, bank deposits and postings into the plain shapes the reconciliation rules use.

`Ledger` reads everything once for the sweeper; `payment_view` reads one payment for the agent. Both give the rules
the same inputs, so a sweep and a replay agree.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a11_cash import config
from krisnnai.agents.a11_cash.rules import Deposit, Payment, Posting


@dataclass
class PaymentView:
    payment: Payment
    known_on: date  # the day the 835 became known
    claims_paid: dict[str, Decimal] = field(default_factory=dict)


def _deposit(row: m.BankDeposit, payer_code: dict[int, str]) -> Deposit:
    payer = payer_code.get(row.payer_id) if row.payer_id is not None else None
    return Deposit(row.deposit_ref, row.deposit_date, row.amount, payer, row.trace_ref)


class Ledger:
    def __init__(self, session: Session):
        payer_code = {p.id: p.payer_id_code for p in session.scalars(select(m.Payer))}
        known = {
            e.id: e.known_at.date()
            for e in session.scalars(select(m.Event).where(m.Event.event_type == "835.payment"))
        }
        paid: dict[int, dict[str, Decimal]] = defaultdict(dict)
        for r in session.scalars(select(m.Remit)):
            if r.claim_status_code != "22":
                got = paid[r.payment_id]
                got[r.claim_submitter_id] = got.get(r.claim_submitter_id, Decimal(0)) + r.total_paid
        self.payments: list[PaymentView] = []
        for p in session.scalars(select(m.Payment).order_by(m.Payment.id)):
            self.payments.append(PaymentView(
                Payment(p.trace_number, payer_code[p.payer_id], p.payment_amount, p.payment_date),
                known.get(p.event_id, p.payment_date), paid.get(p.id, {}),
            ))  # fmt: skip
        self.deposits = [_deposit(d, payer_code) for d in session.scalars(select(m.BankDeposit))]
        self.by_trace: dict[str, list[Deposit]] = defaultdict(list)
        self.untraced: dict[Decimal, list[Deposit]] = defaultdict(list)
        for d in self.deposits:
            if d.trace:
                self.by_trace[d.trace].append(d)
            else:
                self.untraced[d.amount].append(d)
        self.postings: dict[str, list[Posting]] = defaultdict(list)
        for row in session.scalars(select(m.Posting)):
            self.postings[row.payment_trace].append(Posting(row.claim_submitter_id, row.posted_on, row.posted_amount))
        self.traces = {v.payment.trace for v in self.payments}
        self._by_amount: dict[Decimal, list[Payment]] = defaultdict(list)
        self._by_payer_amount: dict[tuple[str, Decimal], list[Payment]] = defaultdict(list)
        for v in self.payments:
            self._by_amount[v.payment.amount].append(v.payment)
            self._by_payer_amount[(v.payment.payer, v.payment.amount)].append(v.payment)

    def candidates(self, p: Payment) -> list[Deposit]:
        return list(self.by_trace.get(p.trace, [])) + list(self.untraced.get(p.amount, []))

    def rivals(self, p: Payment) -> tuple[Payment, ...]:
        """Other payments from the same payer for the same amount whose deposits carry no trace of their own."""
        return tuple(
            x for x in self._by_payer_amount.get((p.payer, p.amount), [])
            if x.trace != p.trace and x.trace not in self.by_trace
        )  # fmt: skip

    def postings_for(self, p: Payment) -> list[Posting]:
        return self.postings.get(p.trace, [])

    def is_unidentified(self, d: Deposit) -> bool:
        """True when no payment explains this deposit (by trace, else by payer + amount inside the window)."""
        if d.trace and d.trace in self.traces:
            return False
        if d.trace:
            return True
        for p in self._by_amount.get(d.amount, []):
            if d.payer in (None, p.payer) and 0 <= (d.deposited_on - p.paid_on).days <= config.MATCH_WINDOW_DAYS:
                return False
        return True


def payment_view(
    session: Session, trace: str, payer: str
) -> tuple[PaymentView, list[Deposit], list[Posting], tuple[Payment, ...]] | None:
    """One payment with the deposits and postings that could belong to it, and its rivals (same payer and amount
    whose deposit carries no trace). The rules then date-filter and assign."""
    payer_row = session.scalars(select(m.Payer).where(m.Payer.payer_id_code == payer)).first()
    if payer_row is None:
        return None
    pay = session.scalars(
        select(m.Payment).where(m.Payment.trace_number == trace, m.Payment.payer_id == payer_row.id)
    ).first()
    if pay is None:
        return None
    event = session.get(m.Event, pay.event_id)
    paid: dict[str, Decimal] = {}
    for r in session.scalars(select(m.Remit).where(m.Remit.payment_id == pay.id)):
        if r.claim_status_code != "22":
            paid[r.claim_submitter_id] = paid.get(r.claim_submitter_id, Decimal(0)) + r.total_paid
    view = PaymentView(Payment(trace, payer, pay.payment_amount, pay.payment_date), event.known_at.date(), paid)
    payer_code = {payer_row.id: payer}
    rows = list(
        session.scalars(
            select(m.BankDeposit).where(
                (m.BankDeposit.trace_ref == trace)
                | (m.BankDeposit.trace_ref.is_(None) & (m.BankDeposit.amount == pay.payment_amount))
            )
        )
    )
    deposits = [_deposit(d, payer_code) for d in rows]
    # a deposit that names another payer is filtered by the rules (payer in (None, payer))
    for d in rows:
        if d.payer_id is not None and d.payer_id != payer_row.id:
            deposits = [x for x in deposits if x.ref != d.deposit_ref]
    postings = [
        Posting(p.claim_submitter_id, p.posted_on, p.posted_amount)
        for p in session.scalars(select(m.Posting).where(m.Posting.payment_trace == trace))
    ]
    rival_rows = list(
        session.scalars(
            select(m.Payment).where(
                m.Payment.payer_id == payer_row.id, m.Payment.payment_amount == pay.payment_amount,
                m.Payment.trace_number != trace,
            )
        )
    )
    traced = set(
        session.scalars(
            select(m.BankDeposit.trace_ref).where(m.BankDeposit.trace_ref.in_([r.trace_number for r in rival_rows]))
        )
    ) if rival_rows else set()
    rivals = tuple(
        Payment(r.trace_number, payer, r.payment_amount, r.payment_date)
        for r in rival_rows if r.trace_number not in traced
    )  # fmt: skip
    return view, deposits, postings, rivals
