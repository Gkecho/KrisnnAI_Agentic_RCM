"""A12 Patient financial engagement agent. Shadow mode, staff-facing: it builds a worklist, it never contacts a patient.

Each `patient.balance_check` event is one claim's patient share with an open item. The agent restates the item from
the statements and payments known that day (rules, plain code) and proposes one task or review for patient billing
staff, with a plain-language explanation they can read or adapt. There is no outbound channel in this agent: no
statement, text, call, portal link or payment request leaves the system.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a12_patient import config, rules
from krisnai.agents.a12_patient.data import load_accounts
from krisnai.agents.a12_patient.explain import explain
from krisnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnai.engine.card import build_card
from krisnai.engine.models import ModelResult

AGENT_ID = "a12_patient"
EVENT_TYPE = "patient.balance_check"
STATEMENT_TASK = "a12_statement_task"
FOLLOWUP_TASK = "a12_followup_task"
DISPUTE_REVIEW = "a12_dispute_review"
CREDIT_REVIEW = "a12_credit_review"
SMALL_BALANCE_REVIEW = "a12_small_balance_review"
ACTION_TYPES = (STATEMENT_TASK, FOLLOWUP_TASK, DISPUTE_REVIEW, CREDIT_REVIEW, SMALL_BALANCE_REVIEW)
ACTION_BY_GAP = {
    rules.NO_STATEMENT: STATEMENT_TASK,
    rules.AGING: FOLLOWUP_TASK,
    rules.DISPUTE_HOLD: DISPUTE_REVIEW,
    rules.CREDIT: CREDIT_REVIEW,
    rules.SMALL: SMALL_BALANCE_REVIEW,
}
NEXT_STEPS = {
    STATEMENT_TASK: ["Send the patient their statement through the practice's own process", "Record the date sent"],
    FOLLOWUP_TASK: [
        "Follow up with the patient through the practice's own process, within its contact rules",
        "Offer the practice's payment options; record what the patient says",
    ],
    DISPUTE_REVIEW: [
        "Pause outreach on this account",
        "Check the payer's remittance codes and the coverage on file",
        "Correct the account if the payer's share was wrong",
    ],
    CREDIT_REVIEW: [
        "Confirm the credit against the payer's remittance and any other open balance",
        "A person decides on applying or refunding it; this agent never refunds",
    ],
    SMALL_BALANCE_REVIEW: [
        "A person decides whether to collect or adjust this small balance under the practice's policy",
        "This agent never writes off a balance",
    ],
}
STAFF_NOTE = "Staff-facing: nothing is sent to the patient by this agent."
FOLLOW_UP_DAYS = 7


class A12PatientAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = (EVENT_TYPE,)

    # ---------------------------------------------------------------------------------------- 1 trigger
    def wants(self, event: m.Event) -> bool:
        return event.event_type == EVENT_TYPE

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        claim = json.loads(event.payload)["claim"]
        day = event.known_at.date()
        base = {"claim": claim, "as_of": day.isoformat(), "gaps": []}
        account = load_accounts(session, claim).get(claim)
        if account is None or account.confirmed_on > day:
            return Context(data={**base, "missing": True}, lineage={"event_ids": [event.id], "source_file_ids": []})
        gaps = rules.check(account.owed, account.confirmed_on, account.statements, account.payments, day)
        paid = sum((p.amount for p in account.payments if p.paid_on <= day), Decimal(0))
        base.update({
            "payer": account.payer, "owed": str(account.owed), "paid": str(paid),
            "confirmed_on": account.confirmed_on.isoformat(),
            "explanation": explain(account.owed, account.pr_codes, paid),
            "gaps": [{"kind": g.kind, "amount": str(g.amount), "stage": g.stage, "detail": g.detail} for g in gaps],
        })  # fmt: skip
        return Context(data=base, lineage={"event_ids": [event.id], "source_file_ids": []})

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        kinds = {g["kind"] for g in ctx.data["gaps"]}
        return [
            RuleResult("not_disputed", rules.DISPUTE_HOLD not in kinds, "the account is not on hold"),
            RuleResult("no_credit", rules.CREDIT not in kinds, "no overpayment"),
            RuleResult("statement_sent", rules.NO_STATEMENT not in kinds, "a statement has gone out"),
            RuleResult("not_aging", rules.AGING not in kinds, "the balance is not past 30 days open"),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        return None  # the explanation is a template from the remittance codes; nothing here needs a model

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        if not d["gaps"]:
            return Proposal(NO_ACTION, {"claim": d["claim"], "clear": True})
        gap = d["gaps"][0]
        action = ACTION_BY_GAP[gap["kind"]]
        amount = Decimal(gap["amount"])
        weight = config.STAGE_WEIGHT.get(gap["stage"], Decimal(1)) if gap["stage"] else Decimal(1)
        priority = amount * weight
        deadline = date.fromisoformat(d["as_of"]) + timedelta(days=FOLLOW_UP_DAYS)
        why = [gap["detail"], d["explanation"], STAFF_NOTE]
        card = build_card(
            f"Patient balance: claim {d['claim']}, {gap['kind'].replace('_', ' ')}, {amount}",
            why, priority, amount if gap["kind"] in (rules.NO_STATEMENT, rules.AGING) else Decimal(0), deadline,
            "patient_billing", NEXT_STEPS[action],
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "claim": d["claim"], "payer": d["payer"], "owner": "patient_billing", "kind": gap["kind"],
            "stage": gap["stage"], "amount": gap["amount"], "owed": d["owed"], "paid": d["paid"],
            "explanation": d["explanation"], "staff_facing": True, "deadline": deadline.isoformat(), "card": card,
        }  # fmt: skip
        return Proposal(action, payload, amount, Decimal("0.90"), f"the {gap['kind']} item for {d['claim']} is closed")

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
