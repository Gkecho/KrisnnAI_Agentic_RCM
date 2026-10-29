"""A7 AR next-best-action agent. Shadow mode only: it decides which unpaid claim to chase and how, as a human card.

It never resubmits, writes off, refunds or changes a code (rules 3 and 4); every action it proposes is a task or
a review.
Which of those the engine may act on is the tenant's policy; the default for all of them is shadow.

Claims that already have an answer from the payer (paid, denied, partly paid) are not A7's: denials belong to A8,
underpayments to A10, patient balances to A12. A7 only works claims with no payer answer yet.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a5_prevention import config as a5_config
from krisnnai.agents.a7_ar import timing
from krisnnai.agents.a7_ar.sweep import EVENT_TYPE
from krisnnai.agents.a15_lite.expected import money
from krisnnai.agents.a15_lite.pricing import ClaimPricer
from krisnnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult
from krisnnai.engine.card import build_card
from krisnnai.engine.models import ModelResult

AGENT_ID = "a7_ar"

# The only things A7 can propose. All are tasks or reviews for a human: no resubmission, write-off or refund here.
STATUS_CHECK = "a7_status_check_task"
RESUBMIT_REVIEW = "a7_resubmit_review"
ESCALATE_REVIEW = "a7_escalate_review"
ACTION_TYPES = (STATUS_CHECK, RESUBMIT_REVIEW, ESCALATE_REVIEW)

# Placeholders for sign-off (spec fields 7 and 17).
ESCALATE_AFTER_DAYS = 90  # an unanswered claim this old goes to the A/R lead
FILING_RISK_DAYS = 60  # within this many days of the filing limit, urgency goes up
FOLLOW_UP_DAYS = 7  # a status check is due this many days after it is raised
BUCKETS = ((30, "0-30"), (60, "31-60"), (90, "61-90"))

NEXT_STEPS = {
    STATUS_CHECK: [
        "Check the payer's status (portal, phone or 276/277)",
        "Write the answer in the account notes",
        "If the payer is waiting for records, send them",
    ],
    RESUBMIT_REVIEW: [
        "Read the 277CA reason the payer or clearinghouse gave",
        "Have the owner fix the named defect (a person edits; the agent never changes codes)",
        "Resubmit through the clearinghouse after approval",
    ],
    ESCALATE_REVIEW: [
        "A/R lead reviews why there has been no answer",
        "Choose: escalate with the payer, start an appeal path, or open a write-off review (a person decides)",
    ],
}


def aging_bucket(age_days: int) -> str:
    for limit, label in BUCKETS:
        if age_days <= limit:
            return label
    return "90+"


class A7ArAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = (EVENT_TYPE,)

    def __init__(self):
        self._pricer = ClaimPricer()  # one A15 snapshot per tenant + as-of date, reused across events
        self._timing: dict[tuple[int, int, datetime], tuple] = {}  # payer history by tenant + payer + as-of

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        trigger = json.loads(event.payload)
        claim = session.get(m.Claim, trigger["claim_id"])
        payer = session.get(m.Payer, claim.payer_id)
        line_query = select(m.ClaimLine).where(m.ClaimLine.claim_id == claim.id).order_by(m.ClaimLine.line_number)
        lines = list(session.scalars(line_query))
        # point in time (rule 9): only what was known by `as_of`
        answered = (
            session.scalar(
                select(m.Remit.id)
                .join(m.Event, m.Event.id == m.Remit.event_id)
                .where(m.Remit.claim_id == claim.id, m.Event.known_at <= as_of)
            )
            is not None
        )
        ack = session.execute(
            select(m.Ack277Ca.status_category, m.Ack277Ca.status_code)
            .join(m.Event, m.Event.id == m.Ack277Ca.event_id)
            .where(m.Ack277Ca.claim_id == claim.id, m.Event.known_at <= as_of)
            .order_by(m.Event.known_at.desc(), m.Ack277Ca.id.desc())
        ).first()
        age = (as_of.date() - claim.submitted_on).days if claim.submitted_on else 0
        key = (session.info["tenant_id"], claim.payer_id, as_of)
        if key not in self._timing:
            self._timing[key] = (
                *timing.expected_days(session, claim.payer_id, as_of),
                *timing.paid_on_their_own(session, claim.payer_id, as_of),
            )
        expected, expected_basis, paid, n = self._timing[key]
        rules = a5_config.load(session)
        filing_days = rules.filing_days.get(claim.payer_id, a5_config.DEFAULT_FILING_DAYS)
        filing_deadline = claim.service_date + timedelta(days=filing_days) if claim.service_date else None
        amount, pricing_basis = self._dollars(session, event, payer, claim, lines)
        data = {
            "claim": claim.claim_submitter_id,
            "payer": payer.payer_id_code,
            "answered": answered,
            "ack_category": ack[0] if ack else "",
            "ack_code": (ack[1] or "") if ack else "",
            "submitted_on": claim.submitted_on.isoformat() if claim.submitted_on else "",
            "age_days": age,
            "expected_days": expected,
            "expected_basis": expected_basis,
            "history_paid": paid,
            "history_n": n,
            "amount": str(amount),
            "pricing_basis": pricing_basis,
            "filing_deadline": filing_deadline.isoformat() if filing_deadline else "",
            "filing_days_left": (filing_deadline - as_of.date()).days if filing_deadline else None,
            "as_of": as_of.date().isoformat(),
            "round": trigger.get("round", 1),
        }
        return Context(data=data, lineage={"event_ids": [event.id], "source_file_ids": [claim.source_file_id]})

    def _dollars(self, session: Session, event, payer, claim, lines) -> tuple[Decimal, str]:
        """Payer payment expected for the claim (A15 pricing as of the event date), else the billed charge."""
        return self._pricer.price(
            session, event.known_at.date(), payer.payer_id_code, lines, claim.service_date, claim.total_charge
        )

    @staticmethod
    def _age_text(d: dict) -> str:
        return f"{d['age_days']}d old, payer usually pays in {d['expected_days']}d"

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        d = ctx.data
        return [
            RuleResult("claim_open", not d["answered"], "answered" if d["answered"] else "no payer answer known yet"),
            RuleResult("past_expected_date", d["age_days"] >= d["expected_days"], self._age_text(d)),
            RuleResult("acknowledged", bool(d["ack_category"]), d["ack_category"] or "no 277CA on file"),
            RuleResult("amount_priced", d["pricing_basis"] != "billed_fallback", d["pricing_basis"]),
            RuleResult("history_sufficient", d["expected_basis"].startswith("history"), d["expected_basis"]),
        ]  # fmt: skip

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        if d["answered"]:
            return Proposal(NO_ACTION, {"claim": d["claim"], "reason": "the payer has answered; not an A7 claim"})
        amount, age = Decimal(d["amount"]), d["age_days"]
        p = timing.p_paid(d["history_paid"], d["history_n"])
        past = max(0, age - d["expected_days"])
        urgency = 1 + min(Decimal(2), Decimal(past) / Decimal(max(1, d["expected_days"])))
        left = d["filing_days_left"]
        filing_risk = left is not None and left <= FILING_RISK_DAYS
        if filing_risk:
            urgency += 1
        priority = money(amount * (1 - p) * urgency)
        returned = d["ack_category"] in ("A3", "A4")
        if returned:
            action, issue, owner = RESUBMIT_REVIEW, "returned_by_277ca", "billing"
        elif age >= ESCALATE_AFTER_DAYS:
            action, issue, owner = ESCALATE_REVIEW, "no_response_old", "ar_lead"
        else:
            action, issue, owner = STATUS_CHECK, "no_response", "billing"
        as_of = date.fromisoformat(d["as_of"])
        follow_up_by = as_of + timedelta(days=FOLLOW_UP_DAYS)
        state = f"The 277CA returned the claim ({d['ack_category']} {d['ack_code']})".strip()
        why = [
            f"Submitted {age} days ago; {d['payer']} usually pays in {d['expected_days']} days ({d['expected_basis']})",
            state if returned else "The payer has not answered",
            f"Chance it pays without action {p.quantize(Decimal('0.01'))} "
            f"(history paid {d['history_paid']} of {d['history_n']})",
        ]
        if filing_risk:
            why.append(f"Only {left} days left before the filing limit ({d['filing_deadline']})")
        deadline = min(follow_up_by, date.fromisoformat(d["filing_deadline"])) if d["filing_deadline"] else follow_up_by
        card = build_card(
            f"Chase {d['payer']} claim {d['claim']}: {d['amount']} unpaid {age} days",
            why, priority, money(amount * (1 - p)), deadline, owner, NEXT_STEPS[action],
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "claim": d["claim"], "payer": d["payer"], "issue": issue, "owner": owner, "age_days": age,
            "aging_bucket": aging_bucket(age), "expected_days": d["expected_days"],
            "expected_basis": d["expected_basis"], "p_paid": str(p.quantize(Decimal("0.0001"))),
            "amount": str(amount), "pricing_basis": d["pricing_basis"],
            "urgency": str(urgency.quantize(Decimal("0.01"))), "priority": str(priority),
            "filing_deadline": d["filing_deadline"], "filing_days_left": left,
            "follow_up_by": follow_up_by.isoformat(), "round": d["round"], "card": card,
        }  # fmt: skip
        confidence = Decimal("0.90") if d["expected_basis"].startswith("history") else Decimal("0.60")
        return Proposal(
            action, payload, amount, confidence,
            f"claim {d['claim']} has a payer answer, or a documented status, by {follow_up_by}",
        )  # fmt: skip
