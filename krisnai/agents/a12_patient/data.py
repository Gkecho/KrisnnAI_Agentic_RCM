"""Loads patient shares (835), statements and patient payments into the plain shapes the rules use."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a12_patient.rules import Payment, Statement


@dataclass
class Account:
    claim: str
    payer: str
    owed: Decimal
    confirmed_on: date
    pr_codes: dict[str, Decimal] = field(default_factory=dict)  # PR reason code -> amount, for the explanation
    statements: list[Statement] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)


def load_accounts(session: Session, claim: str | None = None) -> dict[str, Account]:
    """One account per claim with a confirmed patient share: the latest non-reversed, non-denied remit wins."""
    payer_code = {p.id: p.payer_id_code for p in session.scalars(select(m.Payer))}
    pay_payer = {p.id: p.payer_id for p in session.scalars(select(m.Payment))}
    known = {e.id: e.known_at.date() for e in session.scalars(select(m.Event).where(m.Event.event_type == "835.remit"))}
    stmt = select(m.Remit).where(m.Remit.claim_status_code.not_in(("22", "4")))
    if claim is not None:
        stmt = stmt.where(m.Remit.claim_submitter_id == claim)
    best: dict[str, m.Remit] = {}
    for r in session.scalars(stmt):
        if r.event_id not in known:
            continue
        cur = best.get(r.claim_submitter_id)
        if cur is None or known[r.event_id] >= known[cur.event_id]:
            best[r.claim_submitter_id] = r
    ids = {r.id for r in best.values()}
    codes: dict[int, dict[str, Decimal]] = defaultdict(dict)
    for a in session.scalars(select(m.Adjustment).where(m.Adjustment.group_code == "PR")):
        if a.remit_id in ids:
            codes[a.remit_id][a.reason_code] = codes[a.remit_id].get(a.reason_code, Decimal(0)) + a.amount
    out: dict[str, Account] = {}
    for sid, r in best.items():
        out[sid] = Account(sid, payer_code.get(pay_payer.get(r.payment_id), ""), r.patient_responsibility,
                           known[r.event_id], codes.get(r.id, {}))  # fmt: skip
    wanted = set(out)
    s_stmt = select(m.PatientStatement)
    p_stmt = select(m.PatientPayment)
    if claim is not None:
        s_stmt = s_stmt.where(m.PatientStatement.claim_submitter_id == claim)
        p_stmt = p_stmt.where(m.PatientPayment.claim_submitter_id == claim)
    for st in session.scalars(s_stmt):
        if st.claim_submitter_id in wanted:
            out[st.claim_submitter_id].statements.append(Statement(st.sent_on, st.status))
    for pp in session.scalars(p_stmt):
        if pp.claim_submitter_id in wanted:
            out[pp.claim_submitter_id].payments.append(Payment(pp.paid_on, pp.amount))
    return out
