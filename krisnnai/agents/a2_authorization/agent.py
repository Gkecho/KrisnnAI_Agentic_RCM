"""A2 Authorization intelligence agent. Shadow mode only: it asks people to request or fix an authorization.

At each checkpoint (7 and 2 days before a booked visit that needs prior authorization) it restates the authorization
picture from the requests and decisions known that day (rules.check, plain code) and proposes one task or review.
There is no portal call and no submission: the status comes from the authorization feed.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a2_authorization import rules
from krisnnai.agents.a2_authorization.sweep import required_pairs
from krisnnai.agents.a15_lite.pricing import ClaimPricer
from krisnnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnnai.engine.card import build_card
from krisnnai.engine.models import ModelResult

AGENT_ID = "a2_authorization"
EVENT_TYPE = "appointment.auth_check"
REQUEST_TASK = "a2_auth_request_task"
EXCEPTION_REVIEW = "a2_auth_exception_review"
ACTION_TYPES = (REQUEST_TASK, EXCEPTION_REVIEW)
ACTION_BY_GAP = {
    rules.NO_AUTH: REQUEST_TASK,
    rules.PENDING_LATE: REQUEST_TASK,
    rules.DENIED: EXCEPTION_REVIEW,
    rules.EXPIRED: EXCEPTION_REVIEW,
    rules.UNITS: EXCEPTION_REVIEW,
}
NEXT_STEPS = {
    REQUEST_TASK: [
        "Request the authorization from the payer, or chase the pending request",
        "Record the reference number and the approved units in the PM",
    ],
    EXCEPTION_REVIEW: [
        "Decide: reschedule, appeal or request a new authorization, or proceed at the practice's risk",
        "The practice manager approves proceeding without a valid authorization",
    ],
}


class A2AuthorizationAgent(Agent):
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
                select(m.Authorization).where(
                    m.Authorization.payer_id == appt.payer_id,
                    m.Authorization.patient_ref_id == appt.patient_ref_id,
                    m.Authorization.cpt == appt.cpt,
                    m.Authorization.requested_on <= day,
                    # one requested for another booked visit is not this visit's authorization
                    or_(
                        m.Authorization.appointment_ref == appt.appt_ref,
                        m.Authorization.appointment_ref.is_(None),
                    ),
                )
            )
        )
        auths = [
            rules.Auth(r.status, r.requested_on, r.decided_on, r.start_date, r.end_date, r.units_approved,
                       r.units_used, r.units_as_of)
            for r in rows
        ]  # fmt: skip
        chosen = rules.pick(auths, appt.appt_date, day)
        required = (appt.payer_id, appt.cpt) in required_pairs(session)
        gaps = rules.check(appt.appt_date, required, chosen, day)
        allowed, basis = self._pricer.pricer(session, day).allowed(
            payer.payer_id_code, appt.cpt, "", appt.appt_date, Decimal(1)
        )
        return Context(
            data={
                "appt": appt.appt_ref, "payer": payer.payer_id_code, "cpt": appt.cpt,
                "appt_date": appt.appt_date.isoformat(), "checkpoint_days": payload["checkpoint_days"],
                "as_of": day.isoformat(), "required": required, "has_request": chosen is not None,
                "gaps": [{"kind": g.kind, "detail": g.detail} for g in gaps],
                "allowed": str(allowed) if allowed is not None else None, "pricing_basis": basis,
            },
            lineage={"event_ids": [event.id], "source_file_ids": [appt.source_file_id]},
        )  # fmt: skip

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        kinds = {g["kind"] for g in ctx.data["gaps"]}
        return [
            RuleResult("authorization_required", ctx.data["required"], "payer + CPT is in auth_requirement"),
            RuleResult("request_on_file", rules.NO_AUTH not in kinds, "an authorization request exists"),
            RuleResult("approved", rules.DENIED not in kinds and rules.PENDING_LATE not in kinds,
                       "the request is approved or not yet overdue"),
            RuleResult("valid_on_visit_date", rules.EXPIRED not in kinds, "the visit is inside the approved window"),
            RuleResult("units_left", rules.UNITS not in kinds, "units remain"),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        return None  # status and dates are arithmetic; a clinical completeness check needs notes and an approved model

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        if not d["gaps"]:
            return Proposal(NO_ACTION, {"appt": d["appt"], "covered": True, "required": d["required"],
                                        "appt_date": d["appt_date"],
                                        "checkpoint_days": d["checkpoint_days"]})  # fmt: skip
        top = d["gaps"][0]
        action = ACTION_BY_GAP[top["kind"]]
        amount = Decimal(d["allowed"]) if d["allowed"] is not None else Decimal(0)
        deadline = date.fromisoformat(d["appt_date"])
        why = [f"{g['kind'].replace('_', ' ')}: {g['detail']}" for g in d["gaps"]]
        why.append(f"visit on {d['appt_date']}, {d['checkpoint_days']} day(s) from this check")
        card = build_card(
            f"Authorization: appointment {d['appt']} ({d['cpt']}), {top['kind'].replace('_', ' ')}",
            why, amount, amount, deadline, "front_desk", NEXT_STEPS[action],
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "appt": d["appt"], "payer": d["payer"], "cpt": d["cpt"], "appt_date": d["appt_date"],
            "checkpoint_days": d["checkpoint_days"], "owner": "front_desk", "gaps": d["gaps"],
            "allowed": d["allowed"], "pricing_basis": d["pricing_basis"], "deadline": deadline.isoformat(),
            "card": card,
        }  # fmt: skip
        return Proposal(action, payload, amount, Decimal("0.90"), f"the {top['kind']} gap for {d['appt']} is closed")

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
