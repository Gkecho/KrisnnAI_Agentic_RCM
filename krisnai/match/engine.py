"""Claim <-> remit <-> payment matching (M3). Deterministic rules, first hit wins, tenant-scoped.

Order of work:
  1. 277CA -> claim by CLM01 echo (gives the payer claim number a claim can be found by).
  2. remit -> claim: CLP01 = CLM01, then CLP07 = payer claim number, then patient + DOS + billed amount.
  3. remit line -> claim line inside the matched claim: exact (CPT, modifiers, DOS, units), then CPT + modifiers.
  4. remit -> payment check: BPR02 = sum of CLP04 less PLB.

Only rows whose link is still null are touched, so a second run changes nothing (rule 7). Pass `as_of` to
use only rows whose event was known by then (rule 9). A rule that finds several different claims never
guesses: the row stays unmatched with reason `ambiguous`.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.match import rules
from krisnai.match.report import MatchReport, money_sum
from krisnai.model import tenant_session


def _known(stmt, event_id_col, as_of: datetime | None):
    if as_of is not None:
        stmt = stmt.join(m.Event, m.Event.id == event_id_col).where(m.Event.known_at <= as_of)
    return stmt


def run_matching(engine: Engine, tenant_id: int, as_of: datetime | None = None) -> MatchReport:
    report = MatchReport(tenant_id, as_of.isoformat() if as_of else None)
    with tenant_session(engine, tenant_id) as s:
        try:
            claims = _load_claims(s, as_of)
            _match_acks(s, as_of, claims, report)
            visible = _match_remits(s, as_of, claims, report)
            _match_lines(s, visible, report)
            _check_payments(s, as_of, report)
            s.commit()
        except Exception:
            s.rollback()
            raise
    return report


class _Claims:
    """In-memory indexes over the claims visible to this run."""

    def __init__(self, keys: list[rules.ClaimKey]):
        self.by_id = {k.id: k for k in keys}
        self.by_submitter: dict[tuple[int, str], list[rules.ClaimKey]] = defaultdict(list)
        self.by_any_payer: dict[str, list[rules.ClaimKey]] = defaultdict(list)
        self.by_pcn: dict[tuple[int, str], dict[int, rules.ClaimKey]] = defaultdict(dict)
        self.by_patient_dos: dict[tuple[int, int, object], list[rules.ClaimKey]] = defaultdict(list)
        for k in keys:
            self.by_submitter[(k.payer_id, k.submitter_id)].append(k)
            self.by_any_payer[k.submitter_id].append(k)
            self.by_patient_dos[(k.payer_id, k.patient_ref_id, k.service_date)].append(k)
            if k.pcn:
                self.by_pcn[(k.payer_id, k.pcn)][k.id] = k

    def add_pcn(self, claim_id: int, pcn: str) -> None:
        k = self.by_id.get(claim_id)
        if k is not None:
            self.by_pcn[(k.payer_id, pcn)][k.id] = k


def _load_claims(s, as_of) -> _Claims:
    stmt = _known(select(m.Claim), m.Claim.event_id, as_of)
    keys = [
        rules.ClaimKey(c.id, c.payer_id, c.claim_submitter_id, c.patient_ref_id, c.service_date,
                       c.total_charge, c.submitted_on, c.payer_claim_control_number)
        for c in s.scalars(stmt)
    ]  # fmt: skip
    return _Claims(keys)


def _match_acks(s, as_of, claims: _Claims, report: MatchReport) -> None:
    lvl = report.acks
    for ack in s.scalars(_known(select(m.Ack277Ca), m.Ack277Ca.event_id, as_of)):
        lvl.total += 1
        if ack.claim_id is None:
            claim, reason = rules.pick(claims.by_any_payer.get(ack.claim_submitter_id, []))
            if claim is None:
                lvl.unmatched_reasons[reason] += 1
                continue
            ack.claim_id = claim.id
            lvl.newly_matched += 1
        lvl.matched += 1
        lvl.by_method[rules.CLP01] += 1
        if ack.payer_claim_number:
            claims.add_pcn(ack.claim_id, ack.payer_claim_number)


def _match_remits(s, as_of, claims: _Claims, report: MatchReport) -> dict[int, int | None]:
    """Return {remit id: claim id} for the remits visible as of `as_of`."""
    lvl = report.remits
    visible: dict[int, int | None] = {}
    stmt = _known(select(m.Remit, m.Payment.payer_id).join(m.Payment, m.Payment.id == m.Remit.payment_id),
                  m.Remit.event_id, as_of)  # fmt: skip
    for remit, payer_id in s.execute(stmt).all():
        lvl.total += 1
        visible[remit.id] = remit.claim_id
        if remit.claim_id is not None:
            lvl.matched += 1
            lvl.by_method[remit.match_method or "unknown"] += 1
            continue
        claim, method, reason = _match_one_remit(remit, payer_id, claims)
        if claim is None:
            lvl.unmatched_reasons[reason] += 1
            continue
        remit.claim_id = claim.id
        visible[remit.id] = claim.id
        remit.match_method = method
        lvl.matched += 1
        lvl.newly_matched += 1
        lvl.by_method[method] += 1
    return visible


def _match_one_remit(remit, payer_id: int, claims: _Claims):
    """Return (claim, method, None) or (None, None, reason). Reason priority: ambiguous > payer > amount > none."""
    reasons: set[str] = set()

    cands = claims.by_submitter.get((payer_id, remit.claim_submitter_id), [])
    claim, why = rules.pick(cands)
    if claim:
        return claim, rules.CLP01, None
    if why == rules.AMBIGUOUS:
        reasons.add(why)
    elif claims.by_any_payer.get(remit.claim_submitter_id):
        reasons.add(rules.PAYER_MISMATCH)

    if remit.payer_claim_control_number:
        cands = list(claims.by_pcn.get((payer_id, remit.payer_claim_control_number), {}).values())
        claim, why = rules.pick(cands)
        if claim:
            return claim, rules.CLP07, None
        if why == rules.AMBIGUOUS:
            reasons.add(why)

    if remit.patient_ref_id is not None and remit.service_date is not None:
        same_day = claims.by_patient_dos.get((payer_id, remit.patient_ref_id, remit.service_date), [])
        cands = [c for c in same_day if c.total_charge == remit.total_charge]
        claim, why = rules.pick(cands)
        if claim:
            return claim, rules.PATIENT_DOS_AMOUNT, None
        if why == rules.AMBIGUOUS:
            reasons.add(why)
        elif same_day:
            reasons.add(rules.AMOUNT_MISMATCH)

    for reason in (rules.AMBIGUOUS, rules.PAYER_MISMATCH, rules.AMOUNT_MISMATCH):
        if reason in reasons:
            return None, None, reason
    return None, None, rules.NO_CANDIDATE


def _line_key(row) -> rules.LineKey:
    return rules.LineKey(row.id, row.cpt, rules.modifiers(row.modifier_1, row.modifier_2, row.modifier_3,
                         row.modifier_4), row.service_date, row.units)  # fmt: skip


def _match_lines(s, claim_of_remit: dict[int, int | None], report: MatchReport) -> None:
    lvl = report.lines
    claim_lines: dict[int, list[rules.LineKey]] = defaultdict(list)
    for cl in s.scalars(select(m.ClaimLine).order_by(m.ClaimLine.claim_id, m.ClaimLine.line_number)):
        claim_lines[cl.claim_id].append(_line_key(cl))

    for rl in s.scalars(select(m.RemitLine).order_by(m.RemitLine.remit_id, m.RemitLine.line_number)):
        if rl.remit_id not in claim_of_remit:
            continue
        lvl.total += 1
        if rl.claim_line_id is not None:
            lvl.matched += 1
            lvl.by_method[rl.match_method or "unknown"] += 1
            continue
        claim_id = claim_of_remit[rl.remit_id]
        if claim_id is None:
            lvl.unmatched_reasons[rules.NO_CLAIM] += 1
            continue
        key = _line_key(rl)
        pool = claim_lines.get(claim_id, [])
        method, found = rules.LINE_EXACT, rules.line_exact(key, pool)
        if not found:
            method, found = rules.LINE_CPT_MOD, rules.line_cpt_mod(key, pool)
        if len(found) != 1:
            lvl.unmatched_reasons[rules.AMBIGUOUS if found else rules.NO_CANDIDATE] += 1
            continue
        rl.claim_line_id = found[0].id
        rl.match_method = method
        lvl.matched += 1
        lvl.newly_matched += 1
        lvl.by_method[method] += 1


def _check_payments(s, as_of, report: MatchReport) -> None:
    chk = report.payments
    paid: dict[int, object] = defaultdict(list)
    for r in s.scalars(select(m.Remit)):
        paid[r.payment_id].append(r.total_paid)
    plb: dict[int, object] = defaultdict(list)
    for p in s.scalars(select(m.PlbAdjustment)):
        plb[p.payment_id].append(p.amount)
    for pay in s.scalars(_known(select(m.Payment), m.Payment.event_id, as_of)):
        chk.payments += 1
        remit_total = money_sum(paid.get(pay.id, [])) - money_sum(plb.get(pay.id, []))
        if remit_total == pay.payment_amount and pay.trace_number:
            chk.reconciled += 1
        else:
            chk.mismatched.append({"payment_id": pay.id, "trace_number": pay.trace_number,
                                   "payment_amount": str(pay.payment_amount),
                                   "remit_total": str(remit_total)})  # fmt: skip
