"""A8 Denial & appeal agent. Shadow mode only: it routes and values denials, it never fixes, appeals or writes off.

Every action it proposes is a task or a review for a named human (rule 4). Which of those the engine may actually run
is the tenant's policy; the default for all of them is shadow.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a8_denial import history, routing
from krisnai.agents.a15_lite.expected import money
from krisnai.agents.a15_lite.pricing import ClaimPricer
from krisnai.engine import Agent, Context, Proposal, RuleResult, Verification
from krisnai.engine.models import ModelResult

AGENT_ID = "a8_denial"

# The only things A8 can propose. All are tasks or reviews for a human: no write-off, refund or code change exists here.
FIX_TASK = "a8_fix_task"
APPEAL_TASK = "a8_appeal_task"
WRITE_OFF_REVIEW = "a8_write_off_review"
TAKEBACK_REVIEW = "a8_takeback_review"
RECOUPMENT_REVIEW = "a8_recoupment_review"
ACTION_TYPES = (FIX_TASK, APPEAL_TASK, WRITE_OFF_REVIEW, TAKEBACK_REVIEW, RECOUPMENT_REVIEW)
ACTION_BY_DISPOSITION = {"correctable": FIX_TASK, "appealable": APPEAL_TASK, "write_off_review": WRITE_OFF_REVIEW}

DENIAL, DENIAL_LINE, TAKEBACK, RECOUPMENT = "denial", "denial_line", "takeback", "recoupment"
RECOUPMENT_REASONS = ("WO", "72")  # PLB reasons treated as a recoupment: overpayment recovery, authorized return
CONTRACTUAL = "45"


def _line_is_denied(line: dict) -> bool:
    paid = Decimal(line.get("paid", "0"))
    odd = [a for a in line.get("adjustments", []) if a["group_code"] != "PR" and a["reason_code"] != CONTRACTUAL]
    return paid == 0 and bool(odd)


def trigger_kind(event: m.Event, recoupment_reasons=RECOUPMENT_REASONS) -> str | None:
    """What this event is for A8, or None. Decided from the stored payload alone."""
    payload = json.loads(event.payload)
    if event.event_type == "835.payment":
        hit = any(p["reason_code"] in recoupment_reasons for p in payload.get("plb", []))
        return RECOUPMENT if hit else None
    if event.event_type == "835.remit":
        status = payload.get("status_code")
        if status == "22":
            return TAKEBACK
        if status == "4":
            return DENIAL
        if any(_line_is_denied(ln) for ln in payload.get("lines", [])):
            return DENIAL_LINE
    return None


class A8DenialAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = ("835.remit", "835.payment")

    def __init__(self, recoupment_reasons: tuple[str, ...] = RECOUPMENT_REASONS):
        self.recoupment_reasons = recoupment_reasons
        self._pricer = ClaimPricer()  # one A15 snapshot per tenant + as-of date, reused across events

    # ---------------------------------------------------------------------------------------- 1 trigger
    def wants(self, event: m.Event) -> bool:
        return trigger_kind(event, self.recoupment_reasons) is not None

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        kind = trigger_kind(event, self.recoupment_reasons)
        if kind == RECOUPMENT:
            return self._recoupment_context(session, event)
        return self._remit_context(session, event, as_of, kind)

    def _recoupment_context(self, session: Session, event: m.Event) -> Context:
        pay = session.scalars(select(m.Payment).where(m.Payment.event_id == event.id)).one()
        plb = [
            p
            for p in session.scalars(select(m.PlbAdjustment).where(m.PlbAdjustment.payment_id == pay.id))
            if p.reason_code in self.recoupment_reasons
        ]
        payer = session.get(m.Payer, pay.payer_id)
        days, from_table = routing.appeal_window(session, pay.payer_id)
        amount = sum((abs(p.amount) for p in plb), Decimal(0))
        return Context(
            data={
                "trigger": RECOUPMENT,
                "payer": payer.payer_id_code,
                "payer_id": pay.payer_id,
                "carcs": [p.reason_code for p in plb],
                "cpts": [],
                "claim": "",
                "category": "recoupment",
                "owner": "billing",
                "disposition": "recoupment_review",
                "unrouted": False,
                "payment_date": pay.payment_date.isoformat(),
                "amount_at_risk": str(money(amount)),
                "pricing_basis": "plb_amount",
                "window_days": days,
                "window_from_table": from_table,
                "trace_number": pay.trace_number,
            },
            lineage={"event_ids": [event.id], "source_file_ids": [pay.source_file_id]},
        )

    def _remit_context(self, session: Session, event: m.Event, as_of: datetime, kind: str) -> Context:
        remit = session.scalars(select(m.Remit).where(m.Remit.event_id == event.id)).one()
        pay = session.get(m.Payment, remit.payment_id)
        payer = session.get(m.Payer, pay.payer_id)
        claim = session.get(m.Claim, remit.claim_id) if remit.claim_id is not None else None
        lines = list(
            session.scalars(
                select(m.RemitLine).where(m.RemitLine.remit_id == remit.id).order_by(m.RemitLine.line_number)
            )
        )
        adjustments = list(session.scalars(select(m.Adjustment).where(m.Adjustment.remit_id == remit.id)))
        by_line: dict[int | None, list[m.Adjustment]] = {}
        for a in adjustments:
            by_line.setdefault(a.remit_line_id, []).append(a)

        def odd(items):
            return [a for a in items if a.group_code != "PR" and a.reason_code != CONTRACTUAL]

        if kind == TAKEBACK:
            denied = lines
            reasons = Counter({a.reason_code: abs(a.amount) for a in odd(adjustments)})
            amount, basis = abs(remit.total_paid), "reversed_payment"
        else:
            denied = lines if kind == DENIAL else [ln for ln in lines if ln.paid == 0 and odd(by_line.get(ln.id, []))]
            reasons = Counter()
            for ln in denied:
                for a in odd(by_line.get(ln.id, [])):
                    reasons[a.reason_code] += abs(a.amount)
            if not reasons:  # claim-level CAS carries the reason
                for a in odd(by_line.get(None, [])):
                    reasons[a.reason_code] += abs(a.amount)
            amount, basis = self._dollars(session, event, pay, payer, remit, denied)
        carcs = [c for c, _ in reasons.most_common()]
        routes = routing.load_routes(session)
        route = routes.get(carcs[0]) if carcs else None
        if kind == TAKEBACK:
            category, owner, disposition = "takeback", "billing", "takeback_review"
        elif route is not None:
            category, owner, disposition = route.category, route.owner, route.disposition
        else:
            category, owner, disposition = "unrouted", "billing", "write_off_review"
        days, from_table = routing.appeal_window(session, pay.payer_id)
        wins, n = history.outcomes(session, pay.payer_id, carcs[0], as_of) if carcs and kind != TAKEBACK else (0, 0)
        return Context(
            data={
                "trigger": kind,
                "payer": payer.payer_id_code,
                "payer_id": pay.payer_id,
                "carcs": carcs,
                "cpts": sorted({ln.cpt for ln in denied}),
                "claim": claim.claim_submitter_id if claim else "",
                "category": category,
                "owner": owner,
                "disposition": disposition,
                "unrouted": route is None and kind != TAKEBACK,
                "description": route.description if route else "",
                "payment_date": pay.payment_date.isoformat(),
                "amount_at_risk": str(amount),
                "pricing_basis": basis,
                "window_days": days,
                "window_from_table": from_table,
                "history_wins": wins,
                "history_n": n,
                "claim_matched": claim is not None,
            },
            lineage={"event_ids": [event.id], "source_file_ids": [remit.source_file_id]},
        )

    def _dollars(self, session: Session, event, pay, payer, remit, lines) -> tuple[Decimal, str]:
        """Payer payment expected for the denied lines (A15 pricing as of the event date), else the billed charge."""
        return self._pricer.price(session, event.known_at.date(), payer.payer_id_code, lines, remit.service_date)

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        d = ctx.data
        deadline = date.fromisoformat(d["payment_date"]) + timedelta(days=d["window_days"])
        return [
            RuleResult("claim_matched", d.get("claim_matched", True), "remit is linked to a claim"),
            RuleResult("routing_found", not d["unrouted"], f"CARC {d['carcs'][:1]} has a row in carc_route"),
            RuleResult("appeal_window_from_table", d["window_from_table"], f"{d['window_days']} days"),
            RuleResult("deadline_open", deadline >= date.fromisoformat(d["payment_date"]), f"deadline {deadline}"),
            RuleResult("amount_priced", d["pricing_basis"] not in ("billed_fallback",), d["pricing_basis"]),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        d = ctx.data
        if d["disposition"] != "appealable":
            return None
        # payer code, CARC, CPT codes, amount and dates only: no names, member ids or birth dates
        return (
            f"Draft a short appeal letter to payer {d['payer']} for denial reason {d['carcs'][0]} "
            f"({d['description']}). "
            f"Services: {', '.join(d['cpts'])}. Amount: {d['amount_at_risk']}. Paid on {d['payment_date']}."
        )

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        at_risk = Decimal(d["amount_at_risk"])
        deadline = date.fromisoformat(d["payment_date"]) + timedelta(days=d["window_days"])
        wins, n = d.get("history_wins", 0), d.get("history_n", 0)
        prob = history.win_probability(wins, n) if d["trigger"] in (DENIAL, DENIAL_LINE) else Decimal(1)
        if d["disposition"] == "takeback_review":
            action = TAKEBACK_REVIEW
        elif d["trigger"] == RECOUPMENT:
            action = RECOUPMENT_REVIEW
        else:
            action = ACTION_BY_DISPOSITION[d["disposition"]]
        payload = {
            "trigger": d["trigger"],
            "payer": d["payer"],
            "claim": d["claim"],
            "category": d["category"],
            "owner": d["owner"],
            "disposition": d["disposition"],
            "carcs": d["carcs"],
            "cpts": d["cpts"],
            "deadline": deadline.isoformat(),
            "amount_at_risk": str(at_risk),
            "pricing_basis": d["pricing_basis"],
            "win_probability": str(prob.quantize(Decimal("0.0001"))),
            "win_basis": f"history wins={wins} n={n}" if d["trigger"] in (DENIAL, DENIAL_LINE) else "not applicable",
            "expected_recovery": str(money(at_risk * prob)),
            "unrouted": d["unrouted"],
            "appeal_draft": model.text if model else None,
        }
        confidence = Decimal("0.95") if not d["unrouted"] else Decimal("0.50")
        return Proposal(
            action,
            payload,
            at_risk,
            confidence,
            f"a {d['owner']} task for this {d['trigger']} exists and is closed before {deadline}",
        )

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
