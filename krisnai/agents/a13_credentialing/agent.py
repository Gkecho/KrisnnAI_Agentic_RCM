"""A13 Credentialing & enrollment agent. Shadow mode only: it asks people to renew, chase or review.

Each event is one provider + payer enrollment or one provider's screening with an open gap. The agent restates the gaps
from the statuses known that day (rules, plain code), prices the services at risk, and proposes one task or review. It
never holds a claim, never stops scheduling, never contacts a payer: a compliance owner decides.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a13_credentialing import rules
from krisnai.agents.a13_credentialing.data import enroll_rows, services
from krisnai.agents.a15_lite.pricing import ClaimPricer
from krisnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnai.engine.card import build_card
from krisnai.engine.models import ModelResult

AGENT_ID = "a13_credentialing"
ENROLLMENT_EVENT = "enrollment.check"
SCREENING_EVENT = "provider.screening_check"
ENROLLMENT_TASK = "a13_enrollment_task"
EXCEPTION_REVIEW = "a13_enrollment_exception_review"
ACTION_TYPES = (ENROLLMENT_TASK, EXCEPTION_REVIEW)
ACTION_BY_GAP = {
    rules.EXCLUDED: EXCEPTION_REVIEW,
    rules.BILLING_WITHOUT: EXCEPTION_REVIEW,
    rules.EXPIRED: EXCEPTION_REVIEW,
    rules.EXPIRING: ENROLLMENT_TASK,
    rules.PENDING_LONG: ENROLLMENT_TASK,
    rules.STALE_SCREEN: ENROLLMENT_TASK,
}
OWNER = {ENROLLMENT_TASK: "credentialing", EXCEPTION_REVIEW: "compliance_owner"}
NEXT_STEPS = {
    ENROLLMENT_TASK: [
        "Start the renewal, chase the pending application, or run the screening",
        "Record the new date or result in the credentialing system",
    ],
    EXCEPTION_REVIEW: [
        "Decide whether to hold claims, stop scheduling this provider with this payer, or escalate",
        "A named compliance owner decides; this agent holds and stops nothing",
    ],
}
FOLLOW_UP_DAYS = 7


class A13CredentialingAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = (ENROLLMENT_EVENT, SCREENING_EVENT)

    def __init__(self) -> None:
        self._pricer = ClaimPricer()

    # ---------------------------------------------------------------------------------------- 1 trigger
    def wants(self, event: m.Event) -> bool:
        return event.event_type in self.trigger_types

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        p = json.loads(event.payload)
        day = event.known_at.date()
        provider = session.scalars(select(m.Provider).where(m.Provider.npi == p["npi"])).first()
        base = {"kind": p["kind"], "key": p["key"], "npi": p["npi"], "as_of": day.isoformat()}
        if provider is None:
            return Context(data={**base, "gaps": [], "missing": True},
                           lineage={"event_ids": [event.id], "source_file_ids": []})  # fmt: skip
        if p["kind"] == "screening":
            known = list(
                session.scalars(
                    select(m.ProviderScreening).where(
                        m.ProviderScreening.provider_id == provider.id, m.ProviderScreening.screened_on <= day
                    )
                )
            )
            last = max(known, key=lambda r: r.screened_on) if known else None
            gaps = rules.check_screening(last.result if last else None, last.screened_on if last else None, day)
            lineage = [last.source_file_id] if last else []
        else:
            payer = session.scalars(select(m.Payer).where(m.Payer.payer_id_code == p["payer"])).first()
            pricer = self._pricer.pricer(session, day)
            svc = services(session, provider.id, payer.id, payer.payer_id_code, day, pricer)
            current = rules.latest_known(enroll_rows(session, provider.id, payer.id), day)
            gaps = rules.check_enrollment(current, svc, day)
            base["payer"] = p["payer"]
            lineage = [provider.source_file_id]
        return Context(
            data={**base, "gaps": [{"kind": g.kind, "amount": str(g.amount), "detail": g.detail} for g in gaps]},
            lineage={"event_ids": [event.id], "source_file_ids": lineage},
        )

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        kinds = {g["kind"] for g in ctx.data["gaps"]}
        if ctx.data["kind"] == "screening":
            return [
                RuleResult("not_excluded", rules.EXCLUDED not in kinds, "the latest screening is clear"),
                RuleResult("screening_current", rules.STALE_SCREEN not in kinds, "screened recently"),
            ]
        return [
            RuleResult("enrolled_for_services", not kinds & {rules.BILLING_WITHOUT, rules.EXPIRED}, "active"),
            RuleResult("not_expiring", rules.EXPIRING not in kinds, "no expiry within the warning window"),
            RuleResult("not_pending_long", rules.PENDING_LONG not in kinds, "no application stuck pending"),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        return None  # dates and statuses are arithmetic; nothing here needs a model

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        if not d["gaps"]:
            return Proposal(NO_ACTION, {"key": d["key"], "kind": d["kind"], "clear": True})
        top = min(d["gaps"], key=lambda g: rules.PRIORITY.index(g["kind"]))
        action = ACTION_BY_GAP[top["kind"]]
        owner = OWNER[action]
        amount = sum((Decimal(g["amount"]) for g in d["gaps"]), Decimal(0))
        deadline = date.fromisoformat(d["as_of"]) + timedelta(days=FOLLOW_UP_DAYS)
        who = f"{d['npi']} with {d['payer']}" if d["kind"] == "enrollment" else f"{d['npi']} (screening)"
        why = [f"{g['kind'].replace('_', ' ')}: {g['detail']}" for g in d["gaps"]]
        if amount > 0:
            why.append(f"{amount} of expected payment depends on this enrollment")
        card = build_card(
            f"Credentialing: provider {who}, {top['kind'].replace('_', ' ')}",
            why, amount, amount, deadline, owner, NEXT_STEPS[action],
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "key": d["key"], "kind": d["kind"], "npi": d["npi"], "payer": d.get("payer"), "owner": owner,
            "gaps": d["gaps"], "amount": str(amount), "deadline": deadline.isoformat(), "card": card,
        }  # fmt: skip
        return Proposal(action, payload, amount, Decimal("0.90"), f"the {top['kind']} gap for {who} is closed")

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
