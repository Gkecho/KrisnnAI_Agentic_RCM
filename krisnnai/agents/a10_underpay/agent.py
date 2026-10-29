"""A10 Contract & underpayment agent. Shadow mode only: it prepares disputes for finance, it never sends or writes off.

For each payment it asks one question: did the payer pay what the contract says? Contract = the fee schedule
(allowed amount x units), less the patient share already taken off the line. A line short by more than the floor is
flagged with a likely cause and the dollars. Denials and reversals belong to A8 and are ignored here.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a8_denial import routing
from krisnnai.agents.a10_underpay import config
from krisnnai.agents.a15_lite.expected import FALLBACK, FEE, money
from krisnnai.agents.a15_lite.pricing import ClaimPricer
from krisnnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnnai.engine.card import build_card
from krisnnai.engine.models import ModelResult

AGENT_ID = "a10_underpay"
DISPUTE_REVIEW = "a10_dispute_review"
CONTRACT_CHECK_TASK = "a10_contract_check_task"
ACTION_TYPES = (DISPUTE_REVIEW, CONTRACT_CHECK_TASK)
NEXT_STEPS = {
    DISPUTE_REVIEW: [
        "Finance confirms the contract rate for these lines",
        "Review the draft dispute; nothing is sent without a named approval",
        "File the dispute before the deadline",
    ],
    CONTRACT_CHECK_TASK: [
        "Find the contract rate for this payer and code (no fee-schedule row exists)",
        "Add it to the fee schedule, then this claim can be disputed on the contract",
    ],
}


def _paid_remit(event: m.Event) -> bool:
    """True for a processed (not reversed) claim payment with at least one paid line."""
    if event.event_type != "835.remit":
        return False
    p = json.loads(event.payload)
    if p.get("status_code") == "22":
        return False
    return any(Decimal(str(ln.get("paid", "0"))) > 0 for ln in p.get("lines", []))


def cause_of(adjustments: list[tuple[str, str, Decimal]]) -> tuple[str, bool]:
    """(cause, recognised) from the (group, carc, amount) adjustments on the short line, ignoring patient share."""
    odd = [(abs(a), rc) for g, rc, a in adjustments if g != "PR" and rc != "45"]
    if not odd:
        return config.CONTRACT_PRICING, True
    carc = max(odd)[1]
    if carc in config.CAUSE_BY_CARC:
        return config.CAUSE_BY_CARC[carc], True
    return config.DATA_CODING, False


class A10UnderpaymentAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = ("835.remit",)

    def __init__(self) -> None:
        self._pricer = ClaimPricer()  # one A15 snapshot per tenant + day, reused across events

    # ---------------------------------------------------------------------------------------- 1 trigger
    def wants(self, event: m.Event) -> bool:
        return _paid_remit(event)

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        remit = session.scalars(select(m.Remit).where(m.Remit.event_id == event.id)).one()
        pay = session.get(m.Payment, remit.payment_id)
        payer = session.get(m.Payer, pay.payer_id)
        claim = session.get(m.Claim, remit.claim_id) if remit.claim_id is not None else None
        lines = list(
            session.scalars(
                select(m.RemitLine).where(m.RemitLine.remit_id == remit.id).order_by(m.RemitLine.line_number)
            )
        )
        by_line: dict[int, list[tuple[str, str, Decimal]]] = {}
        for a in session.scalars(select(m.Adjustment).where(m.Adjustment.remit_id == remit.id)):
            if a.remit_line_id is not None:
                by_line.setdefault(a.remit_line_id, []).append((a.group_code, a.reason_code, a.amount))

        pricer = self._pricer.pricer(session, event.known_at.date())
        out, unpriced = [], 0
        for ln in lines:
            if ln.paid <= 0:
                continue
            units = ln.units or Decimal(1)
            allowed, basis = pricer.allowed(
                payer.payer_id_code, ln.cpt, ln.modifier_1 or "", ln.service_date or remit.service_date, units
            )
            if allowed is None:
                unpriced += 1
                continue
            adj = by_line.get(ln.id, [])
            share = sum((a for g, _, a in adj if g == "PR"), Decimal(0))
            gap = money(allowed - (ln.paid + share))
            floor = config.FEE_FLOOR if basis == FEE else money(allowed * config.FALLBACK_FLOOR)
            cause, known = cause_of(adj)
            out.append({
                "line_number": ln.line_number, "cpt": ln.cpt, "units": str(units), "allowed": str(allowed),
                "paid": str(ln.paid), "patient_share": str(share), "gap": str(gap), "basis": basis,
                "short": gap >= floor and gap > 0, "cause": cause, "cause_recognised": known,
            })  # fmt: skip
        days, from_table = routing.appeal_window(session, pay.payer_id)
        return Context(
            data={
                "payer": payer.payer_id_code,
                "claim": claim.claim_submitter_id if claim else remit.claim_submitter_id,
                "claim_matched": claim is not None,
                "payment_date": pay.payment_date.isoformat(),
                "known_on": event.known_at.date().isoformat(),
                "lines": out,
                "unpriced_lines": unpriced,
                "window_days": days,
                "window_from_table": from_table,
            },
            lineage={"event_ids": [event.id], "source_file_ids": [remit.source_file_id]},
        )

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        d = ctx.data
        short = [ln for ln in d["lines"] if ln["short"]]
        deadline = date.fromisoformat(d["payment_date"]) + timedelta(days=d["window_days"])
        return [
            RuleResult("claim_matched", d["claim_matched"], "remit is linked to a claim"),
            RuleResult("short_paid", bool(short), f"{len(short)} line(s) paid below the contract"),
            RuleResult("contract_priced", all(ln["basis"] == FEE for ln in short), "fee-schedule row per short line"),
            RuleResult("appeal_window_open", deadline >= date.fromisoformat(d["known_on"]), f"deadline {deadline}"),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        short = [ln for ln in ctx.data["lines"] if ln["short"]]
        if not short or any(ln["basis"] != FEE for ln in short):
            return None
        # payer code, CPT codes, dollars and dates only: no names, member ids or birth dates
        items = "; ".join(f"{ln['cpt']} paid {ln['paid']} against contract {ln['allowed']}" for ln in short)
        return (
            f"Draft a short payment dispute letter to payer {ctx.data['payer']} for an underpayment on "
            f"{ctx.data['payment_date']}: {items}."
        )

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        short = [ln for ln in d["lines"] if ln["short"]]
        if not short:
            return Proposal(NO_ACTION, {"claim": d["claim"], "lines_checked": len(d["lines"])})
        total = money(sum((Decimal(ln["gap"]) for ln in short), Decimal(0)))
        contract = all(ln["basis"] == FEE for ln in short)
        action = DISPUTE_REVIEW if contract else CONTRACT_CHECK_TASK
        causes = sorted({ln["cause"] for ln in short})
        deadline = date.fromisoformat(d["payment_date"]) + timedelta(days=d["window_days"])
        basis = "fee schedule" if contract else FALLBACK
        why = [
            f"Paid {len(short)} line(s) below the contract: {total} short ({basis})",
            f"Likely cause: {', '.join(causes)}",
            f"Appeal deadline {deadline.isoformat()}",
        ]
        card = build_card(
            f"Underpayment: {d['payer']} claim {d['claim'] or 'n/a'}, {total} short",
            why, total, money(total if contract else Decimal(0)), deadline, "finance", NEXT_STEPS[action],
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        recognised = all(ln["cause_recognised"] for ln in short)
        confidence = Decimal("0.90") if contract and recognised else Decimal("0.60") if contract else Decimal("0.50")
        payload = {
            "payer": d["payer"], "claim": d["claim"], "owner": "finance", "causes": causes,
            "deadline": deadline.isoformat(), "total_gap": str(total), "pricing_basis": FEE if contract else FALLBACK,
            "lines": short, "payment_date": d["payment_date"], "dispute_draft": model.text if model else None,
            "card": card,
        }  # fmt: skip
        return Proposal(action, payload, total, confidence, f"a finance review for this claim exists before {deadline}")

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
