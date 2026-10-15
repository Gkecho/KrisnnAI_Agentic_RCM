"""A11 Cash reconciliation agent. Shadow mode only: it asks people to chase a deposit or post a payment.

Each `payment.reconcile_due` event is one payer payment with an open gap; each `deposit.unidentified` event is one bank
deposit no payment explains. The agent restates the picture from the deposits and postings known that day (rules, plain
code) and proposes one task or review with the dollars. It never posts, never touches the bank, never writes back.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a11_cash import rules
from krisnai.agents.a11_cash.ledger import payment_view
from krisnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnai.engine.card import build_card
from krisnai.engine.models import ModelResult

AGENT_ID = "a11_cash"
PAYMENT_EVENT = "payment.reconcile_due"
DEPOSIT_EVENT = "deposit.unidentified"
DEPOSIT_TASK = "a11_deposit_investigation_task"
POSTING_TASK = "a11_posting_task"
UNAPPLIED_REVIEW = "a11_unapplied_review"
UNIDENTIFIED_REVIEW = "a11_unidentified_deposit_review"
ACTION_TYPES = (DEPOSIT_TASK, POSTING_TASK, UNAPPLIED_REVIEW, UNIDENTIFIED_REVIEW)
ACTION_BY_GAP = {
    rules.DEPOSIT_MISSING: DEPOSIT_TASK,
    rules.DUPLICATE_DEPOSIT: DEPOSIT_TASK,
    rules.DEPOSIT_VARIANCE: DEPOSIT_TASK,
    rules.NOT_POSTED: POSTING_TASK,
    rules.PARTIAL_POSTING: UNAPPLIED_REVIEW,
}
OWNER = {DEPOSIT_TASK: "finance", POSTING_TASK: "payment_poster", UNAPPLIED_REVIEW: "finance",
         UNIDENTIFIED_REVIEW: "finance"}  # fmt: skip
NEXT_STEPS = {
    DEPOSIT_TASK: [
        "Check the bank file and the payer for this payment",
        "Record the outcome; do not post until it is explained",
    ],
    POSTING_TASK: ["Post the payment to the claims it covers", "A person posts: this agent never writes to the PM"],
    UNAPPLIED_REVIEW: ["Find where the unposted amount belongs", "Apply it or hold it as unapplied cash with a reason"],
    UNIDENTIFIED_REVIEW: [
        "Identify the payer and the remittance this money belongs to",
        "Ask the bank or payer if unknown",
    ],
}
FOLLOW_UP_DAYS = 3


class A11CashAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = (PAYMENT_EVENT, DEPOSIT_EVENT)

    # ---------------------------------------------------------------------------------------- 1 trigger
    def wants(self, event: m.Event) -> bool:
        return event.event_type in self.trigger_types

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        payload = json.loads(event.payload)
        day = event.known_at.date()
        if event.event_type == DEPOSIT_EVENT:
            row = session.scalars(
                select(m.BankDeposit).where(m.BankDeposit.deposit_ref == payload["deposit_ref"])
            ).one()
            return Context(
                data={"kind": "deposit", "deposit_ref": row.deposit_ref, "amount": str(row.amount),
                      "deposited_on": row.deposit_date.isoformat(), "as_of": day.isoformat(), "gaps": []},
                lineage={"event_ids": [event.id], "source_file_ids": [row.source_file_id]},
            )  # fmt: skip
        found = payment_view(session, payload["trace"], payload["payer"])
        if found is None:
            return Context(data={"kind": "payment", "trace": payload["trace"], "payer": payload["payer"],
                                 "as_of": day.isoformat(), "missing": True, "gaps": []},
                           lineage={"event_ids": [event.id], "source_file_ids": []})  # fmt: skip
        view, deposits, postings, rivals = found
        gaps = rules.reconcile(view.payment, view.claims_paid, deposits, postings, day, rivals)
        return Context(
            data={
                "kind": "payment", "trace": view.payment.trace, "payer": view.payment.payer,
                "amount": str(view.payment.amount), "paid_on": view.payment.paid_on.isoformat(),
                "as_of": day.isoformat(),
                "gaps": [{"kind": g.kind, "amount": str(g.amount), "detail": g.detail, "actionable": g.actionable}
                         for g in gaps],  # fmt: skip
            },
            lineage={"event_ids": [event.id], "source_file_ids": []},
        )

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        d = ctx.data
        if d["kind"] == "deposit":
            return [RuleResult("deposit_explained", False, f"no payment matches {d['amount']} on {d['deposited_on']}")]
        kinds = {g["kind"] for g in d["gaps"]}
        return [
            RuleResult("deposit_present", rules.DEPOSIT_MISSING not in kinds, "a deposit matches the payment"),
            RuleResult("deposit_exact", not kinds & {rules.DEPOSIT_VARIANCE, rules.DUPLICATE_DEPOSIT}, "amount"),
            RuleResult("fully_posted", not kinds & {rules.NOT_POSTED, rules.PARTIAL_POSTING}, "claims are posted"),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        return None  # reconciliation is arithmetic; nothing here needs a model

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        deadline = date.fromisoformat(d["as_of"]) + timedelta(days=FOLLOW_UP_DAYS)
        if d["kind"] == "deposit":
            amount = Decimal(d["amount"])
            action = UNIDENTIFIED_REVIEW
            title = f"Unidentified deposit {d['deposit_ref']}: {amount}"
            why = [f"{amount} deposited {d['deposited_on']} matches no payment on file"]
            payload = {"deposit_ref": d["deposit_ref"], "amount": d["amount"], "kind": "deposit"}
        else:
            actionable = [g for g in d.get("gaps", []) if g["actionable"]]
            if not actionable:
                return Proposal(NO_ACTION, {"trace": d.get("trace"), "reconciled": True, "kind": "payment"})
            top = actionable[0]
            action = ACTION_BY_GAP[top["kind"]]
            amount = sum((Decimal(g["amount"]) for g in actionable if ACTION_BY_GAP[g["kind"]] == action), Decimal(0))
            amount = abs(amount)
            title = f"Cash: {d['payer']} payment {d['trace']}, {top['kind'].replace('_', ' ')}"
            why = [f"{g['kind'].replace('_', ' ')} ({g['amount']}): {g['detail']}" for g in actionable]
            payload = {"trace": d["trace"], "payer": d["payer"], "kind": "payment", "paid_on": d["paid_on"],
                       "payment_amount": d["amount"], "gaps": [{"kind": g["kind"], "amount": g["amount"]}
                                                               for g in actionable]}  # fmt: skip
        owner = OWNER[action]
        card = build_card(
            title, why, amount, amount, deadline, owner, NEXT_STEPS[action],
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload.update({"owner": owner, "amount": str(amount), "deadline": deadline.isoformat(), "card": card})
        return Proposal(action, payload, amount, Decimal("0.90"), f"the {action} for {title} is closed")

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
