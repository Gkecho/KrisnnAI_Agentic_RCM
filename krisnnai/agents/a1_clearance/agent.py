"""A1 Pre-visit financial clearance agent. Shadow mode only: it asks people to check, it never calls a payer.

At each checkpoint (3 days and 1 day before a booked visit) it restates the coverage picture from the eligibility
answers known that day (rules.check, plain code), estimates what the patient will owe, and proposes one task or review
for the front desk. Referral and prior-authorization requirements are not checked here (that is A2's data).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a1_clearance import rules
from krisnnai.agents.a15_lite.pricing import ClaimPricer
from krisnnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnnai.engine.card import build_card
from krisnnai.engine.models import ModelResult

AGENT_ID = "a1_clearance"
EVENT_TYPE = "appointment.clearance_due"
CHECK_TASK = "a1_eligibility_check_task"
EXCEPTION_REVIEW = "a1_coverage_exception_review"
COB_REVIEW = "a1_cob_review"
ACTION_TYPES = (CHECK_TASK, EXCEPTION_REVIEW, COB_REVIEW)
ACTION_BY_GAP = {
    rules.INACTIVE: EXCEPTION_REVIEW,
    rules.COB: COB_REVIEW,
    rules.NO_CHECK: CHECK_TASK,
    rules.STALE: CHECK_TASK,
}
NEXT_STEPS = {
    EXCEPTION_REVIEW: [
        "Confirm the coverage with the patient or the payer",
        "Update the coverage on file, or arrange another payment route before the visit",
        "The practice manager approves any exception to seeing the patient without active coverage",
    ],
    COB_REVIEW: [
        "Confirm which payer is primary with the patient",
        "Update the order of coverage on file before the visit",
    ],
    CHECK_TASK: ["Run a fresh eligibility check for this appointment", "Record the answer in the PM"],
}


class A1ClearanceAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = (EVENT_TYPE,)

    def __init__(self) -> None:
        self._pricer = ClaimPricer()

    # ---------------------------------------------------------------------------------------- 1 trigger
    def wants(self, event: m.Event) -> bool:
        return event.event_type == EVENT_TYPE

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        payload = json.loads(event.payload)
        day = event.known_at.date()
        appt = session.scalars(select(m.Appointment).where(m.Appointment.appt_ref == payload["appt"])).one()
        payer = session.get(m.Payer, appt.payer_id)
        rows = list(
            session.scalars(
                select(m.EligibilityResponse).where(
                    m.EligibilityResponse.patient_ref_id == appt.patient_ref_id,
                    m.EligibilityResponse.payer_id == appt.payer_id,
                    m.EligibilityResponse.checked_on <= day,
                    # an answer is for a date of service: one produced for another visit does not clear this one
                    or_(
                        m.EligibilityResponse.service_date == appt.appt_date,
                        m.EligibilityResponse.service_date.is_(None),
                    ),
                )
            )
        )
        resp = rules.latest(
            [
                rules.Response(r.checked_on, r.active, r.plan_begin, r.plan_end, r.other_payer, r.copay,
                               r.coinsurance, r.deductible_remaining)
                for r in rows
            ],
            day,
        )  # fmt: skip
        gaps = rules.check(appt.appt_date, resp, day)
        allowed, basis = self._pricer.pricer(session, day).allowed(
            payer.payer_id_code, appt.cpt, "", appt.appt_date, Decimal(1)
        )
        est = None
        if resp is not None and allowed is not None:
            est = rules.estimate(resp.copay, resp.coinsurance, resp.deductible_remaining, allowed)
        return Context(
            data={
                "appt": appt.appt_ref, "payer": payer.payer_id_code, "cpt": appt.cpt,
                "appt_date": appt.appt_date.isoformat(), "checkpoint_days": payload["checkpoint_days"],
                "as_of": day.isoformat(), "checked_on": resp.checked_on.isoformat() if resp else None,
                "gaps": [{"kind": g.kind, "detail": g.detail} for g in gaps],
                "allowed": str(allowed) if allowed is not None else None, "pricing_basis": basis,
                "patient_estimate": str(est) if est is not None else None,
            },
            lineage={"event_ids": [event.id], "source_file_ids": [appt.source_file_id]},
        )  # fmt: skip

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        kinds = {g["kind"] for g in ctx.data["gaps"]}
        return [
            RuleResult("eligibility_on_file", rules.NO_CHECK not in kinds, "an eligibility answer is known"),
            RuleResult("coverage_active", rules.INACTIVE not in kinds, "coverage is active on the visit date"),
            RuleResult("no_other_primary", rules.COB not in kinds, "no other payer is primary"),
            RuleResult("answer_fresh", rules.STALE not in kinds, "the answer is recent enough"),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        return None  # nothing here needs a model: the checks and the estimate are arithmetic

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        if not d["gaps"]:
            return Proposal(NO_ACTION, {
                "appt": d["appt"], "cleared": True, "patient_estimate": d["patient_estimate"],
                "appt_date": d["appt_date"], "checkpoint_days": d["checkpoint_days"],
            })  # fmt: skip
        top = d["gaps"][0]
        action = ACTION_BY_GAP[top["kind"]]
        amount = Decimal(d["allowed"]) if d["allowed"] is not None else Decimal(0)
        deadline = date.fromisoformat(d["appt_date"])
        why = [f"{g['kind'].replace('_', ' ')}: {g['detail']}" for g in d["gaps"]]
        why.append(f"visit on {d['appt_date']}, {d['checkpoint_days']} day(s) away")
        if d["patient_estimate"] is not None:
            why.append(f"patient estimate {d['patient_estimate']} (from the last answer)")
        card = build_card(
            f"Clearance: appointment {d['appt']} ({d['cpt']}), {top['kind'].replace('_', ' ')}",
            why, amount, amount, deadline, "front_desk", NEXT_STEPS[action],
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "appt": d["appt"], "payer": d["payer"], "cpt": d["cpt"], "appt_date": d["appt_date"],
            "checkpoint_days": d["checkpoint_days"], "owner": "front_desk", "gaps": d["gaps"],
            "patient_estimate": d["patient_estimate"], "allowed": d["allowed"], "pricing_basis": d["pricing_basis"],
            "deadline": deadline.isoformat(), "card": card,
        }  # fmt: skip
        confidence = Decimal("0.95") if d["checked_on"] else Decimal("0.80")
        return Proposal(action, payload, amount, confidence, f"the {top['kind']} gap for {d['appt']} is closed")

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
