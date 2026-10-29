"""A3 Documentation completeness agent. Shadow mode only: it chases people, it never edits a note or a charge.

Each `visit.doc_check` event is one visit with a gap as of that day. The agent restates the gaps from the note and
charge data known that day (rules.check, plain code), values the visit, and proposes one task or review for a named
owner. Notes are structured elements only: no clinical judgment is made and no code is ever suggested.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a3_documentation import rules
from krisnnai.agents.a15_lite.pricing import BILLED_FALLBACK, ClaimPricer
from krisnnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnnai.engine.card import build_card
from krisnnai.engine.models import ModelResult

AGENT_ID = "a3_documentation"
EVENT_TYPE = "visit.doc_check"
MISSING_NOTE_TASK = "a3_missing_note_task"
SIGNATURE_TASK = "a3_signature_task"
NOTE_QUERY_TASK = "a3_note_query_task"
CHARGE_REVIEW = "a3_charge_review"
ACTION_TYPES = (MISSING_NOTE_TASK, SIGNATURE_TASK, NOTE_QUERY_TASK, CHARGE_REVIEW)
ACTION_BY_GAP = {
    rules.NO_CHARGE: CHARGE_REVIEW,
    rules.NO_NOTE: MISSING_NOTE_TASK,
    rules.UNSIGNED: SIGNATURE_TASK,
    rules.MISSING_ELEMENTS: NOTE_QUERY_TASK,
    rules.MISSING_MINUTES: NOTE_QUERY_TASK,
}
OWNER = {
    CHARGE_REVIEW: "biller",
    MISSING_NOTE_TASK: "provider",
    SIGNATURE_TASK: "provider",
    NOTE_QUERY_TASK: "provider",
}
NEXT_STEPS = {
    CHARGE_REVIEW: ["Confirm the documented service was not billed", "Enter the charge (a person does this in the PM)"],
    MISSING_NOTE_TASK: ["Ask the provider to complete the note", "Hold the charge until the note exists"],
    SIGNATURE_TASK: ["Ask the provider to sign the note", "Escalate through the practice manager if it stays open"],
    NOTE_QUERY_TASK: ["Send the provider the question below", "The provider decides what the note should say"],
}
FOLLOW_UP_DAYS = 3  # how long the owner has before the card is overdue; TBD at spec review


class A3DocumentationAgent(Agent):
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
        ref = json.loads(event.payload)["visit"]
        day = event.known_at.date()
        visit = session.scalars(select(m.Visit).where(m.Visit.visit_ref == ref)).one()
        payer = session.get(m.Payer, visit.payer_id)
        row = session.scalars(select(m.VisitNote).where(m.VisitNote.visit_ref == ref)).first()
        note = (
            rules.Note(row.note_date, row.signed_date, row.minutes, tuple(e for e in row.elements.split(",") if e))
            if row is not None
            else None
        )
        charge_dates = list(session.scalars(select(m.Charge.entered_date).where(m.Charge.visit_ref == ref)))
        billed = session.scalar(
            select(m.Claim.id)
            .join(m.ClaimLine, m.ClaimLine.claim_id == m.Claim.id)
            .join(m.Event, m.Event.id == m.Claim.event_id)
            .where(
                m.Claim.payer_id == visit.payer_id,
                m.Claim.patient_ref_id == visit.patient_ref_id,
                m.Claim.service_date == visit.service_date,
                m.ClaimLine.cpt == visit.cpt,
                m.Event.known_at <= event.known_at,
            )
            .limit(1)
        ) is not None
        gaps = rules.check(visit.service_date, visit.cpt, note, charge_dates, billed, day)
        line = SimpleNamespace(
            cpt=visit.cpt, modifier_1="", units=visit.units, charge=Decimal(0), service_date=visit.service_date
        )
        amount, basis = self._pricer.price(session, day, payer.payer_id_code, [line], visit.service_date)
        source_ids = [x for x in (visit.source_file_id, row.source_file_id if row is not None else None) if x]
        return Context(
            data={
                "visit": ref, "payer": payer.payer_id_code, "cpt": visit.cpt,
                "service_date": visit.service_date.isoformat(),
                "as_of": day.isoformat(), "has_note": note is not None and note.note_date <= day, "billed": billed,
                "charges_known": sum(1 for d in charge_dates if d <= day),
                "gaps": [{"kind": g.kind, "detail": g.detail, "actionable": g.actionable} for g in gaps],
                "amount": str(amount), "pricing_basis": basis,
            },
            lineage={"event_ids": [event.id], "source_file_ids": sorted(set(source_ids))},
        )

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        d = ctx.data
        kinds = {g["kind"] for g in d["gaps"]}
        return [
            RuleResult("note_exists", d["has_note"], "a note is on file"),
            RuleResult("note_signed", rules.UNSIGNED not in kinds and d["has_note"], "the note is signed"),
            RuleResult("elements_complete", not kinds & {rules.MISSING_ELEMENTS, rules.MISSING_MINUTES}, "elements"),
            RuleResult("charge_entered", d["charges_known"] > 0 or d["billed"], "a charge or a claim exists"),
            RuleResult("amount_priced", d["pricing_basis"] != BILLED_FALLBACK, d["pricing_basis"]),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        for g in ctx.data["gaps"]:
            if g["kind"] in (rules.MISSING_ELEMENTS, rules.MISSING_MINUTES):
                # element names only: no patient data, no diagnosis, no code
                return (
                    "Write one short, neutral question asking the provider whether the visit note should also "
                    f"include: {g['detail']}. Do not suggest an answer, a diagnosis or a billing code."
                )
        return None

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        actionable = [g for g in d["gaps"] if g["actionable"]]
        lag = next((g["detail"] for g in d["gaps"] if g["kind"] == rules.CHARGE_LAG), "")
        if not actionable:
            return Proposal(NO_ACTION, {"visit": d["visit"], "resolved": True, "charge_lag": lag})
        top = actionable[0]
        action = ACTION_BY_GAP[top["kind"]]
        owner = OWNER[action]
        amount = Decimal(d["amount"])
        deadline = date.fromisoformat(d["as_of"]) + timedelta(days=FOLLOW_UP_DAYS)
        why = [f"{g['kind'].replace('_', ' ')}: {g['detail']}" for g in actionable]
        why.append(f"{amount} of expected payment depends on this visit being documented and charged")
        steps = list(NEXT_STEPS[action])
        if model is not None and action == NOTE_QUERY_TASK:
            steps.append(model.text)
        card = build_card(
            f"Documentation: visit {d['visit']} ({d['cpt']}), {top['kind'].replace('_', ' ')}",
            why, amount, amount, deadline, owner, steps,
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "visit": d["visit"], "payer": d["payer"], "cpt": d["cpt"], "service_date": d["service_date"],
            "owner": owner, "gaps": [{"kind": g["kind"], "detail": g["detail"]} for g in actionable],
            "amount": str(amount), "pricing_basis": d["pricing_basis"], "charge_lag": lag,
            "deadline": deadline.isoformat(), "query_draft": model.text if model else None, "card": card,
        }  # fmt: skip
        confidence = Decimal("0.95") if d["pricing_basis"] != BILLED_FALLBACK else Decimal("0.70")
        return Proposal(action, payload, amount, confidence, f"the {top['kind']} gap for {d['visit']} is closed")

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
