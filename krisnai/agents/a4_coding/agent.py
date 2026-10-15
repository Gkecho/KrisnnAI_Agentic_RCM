"""A4 Coding & charge integrity copilot. Shadow mode only, and it suggests nothing it can apply.

For each claim it compares the billed E/M level with the highest level the signed note's named elements support
(rules.check, plain code) and raises one review for a coder with the evidence and the dollar difference. It never
changes a code, a modifier or a diagnosis, never holds a claim, never contacts a provider. A certified coder decides.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a4_coding import config, rules
from krisnai.agents.a15_lite.expected import UNPRICED
from krisnai.agents.a15_lite.pricing import ClaimPricer
from krisnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnai.engine.card import build_card
from krisnai.engine.models import ModelResult

AGENT_ID = "a4_coding"
EVENT_TYPE = "837P.claim"
CODING_REVIEW = "a4_coding_review"
ACTION_TYPES = (CODING_REVIEW,)
NEXT_STEPS = [
    "A coder reads the note and the claim line",
    "The coder decides whether the billed level stands; the agent changes nothing",
    "Record the outcome so the audit variance is measured",
]
REVIEW_DAYS = 3


class A4CodingAgent(Agent):
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
        claim = session.scalars(select(m.Claim).where(m.Claim.event_id == event.id)).one()
        payer = session.get(m.Payer, claim.payer_id)
        day = event.known_at.date()
        lines = list(
            session.scalars(
                select(m.ClaimLine).where(m.ClaimLine.claim_id == claim.id).order_by(m.ClaimLine.line_number)
            )
        )
        pricer = self._pricer.pricer(session, day)
        out, checked, source_files = [], 0, {claim.source_file_id}
        for ln in lines:
            if ln.cpt not in config.FAMILY_OF:
                continue
            dos = ln.service_date or claim.service_date
            visit = session.scalars(
                select(m.Visit).where(
                    m.Visit.payer_id == claim.payer_id, m.Visit.patient_ref_id == claim.patient_ref_id,
                    m.Visit.service_date == dos, m.Visit.cpt == ln.cpt,
                )
            ).first()
            note = (
                session.scalars(select(m.VisitNote).where(m.VisitNote.visit_ref == visit.visit_ref)).first()
                if visit is not None else None
            )
            signed = note is not None and note.signed_date is not None and note.signed_date <= day
            elements = {e for e in note.elements.split(",") if e} if note is not None else None
            finding, reason = rules.check(ln.cpt, elements, signed)
            if reason == "judged":
                checked += 1
            if finding is None:
                continue
            units = ln.units or Decimal(1)
            # the contract (allowed) amounts: a coding difference is about the level, not the patient's share
            billed_amt, b = pricer.allowed(payer.payer_id_code, finding.billed, "", dos, units)
            doc_amt, d = pricer.allowed(payer.payer_id_code, finding.documented, "", dos, units)
            priced = billed_amt is not None and doc_amt is not None and UNPRICED not in (b, d)
            provider = session.get(m.Provider, visit.provider_id).npi if visit is not None else ""
            out.append({
                "line_number": ln.line_number, "kind": finding.kind, "billed": finding.billed,
                "documented": finding.documented, "missing": list(finding.missing), "provider": provider,
                "difference": str(abs(billed_amt - doc_amt)) if priced else None,
            })  # fmt: skip
            source_files.add(note.source_file_id)
        return Context(
            data={"claim": claim.claim_submitter_id, "payer": payer.payer_id_code, "as_of": day.isoformat(),
                  "lines_judged": checked, "findings": out},  # fmt: skip
            lineage={"event_ids": [event.id], "source_file_ids": sorted(source_files)},
        )

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        kinds = {f["kind"] for f in ctx.data["findings"]}
        return [
            RuleResult("level_supported", rules.UNSUPPORTED not in kinds, "billed levels are documented"),
            RuleResult("not_under_coded", rules.COULD_BE_HIGHER not in kinds, "notes do not support a higher level"),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        return None  # no model reads notes here: level support is a comparison of named elements

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        findings = d["findings"]
        if not findings:
            return Proposal(NO_ACTION, {"claim": d["claim"], "lines_judged": d["lines_judged"], "findings": []})
        findings = sorted(findings, key=lambda f: (f["kind"] != rules.UNSUPPORTED, f["line_number"]))
        diff = sum((Decimal(f["difference"]) for f in findings if f["difference"]), Decimal(0))
        compliance = any(f["kind"] == rules.UNSUPPORTED for f in findings)
        deadline = date.fromisoformat(d["as_of"]) + timedelta(days=REVIEW_DAYS)
        why = [
            f"line {f['line_number']}: billed {f['billed']}, the note documents the elements for {f['documented']}"
            + (f"; missing {', '.join(f['missing'])}" if f["missing"] else "")
            for f in findings
        ]
        if compliance:
            why.append("Compliance risk: a billed level is not supported by the documented elements")
        why.append(config.SUGGESTION_ONLY)
        card = build_card(
            f"Coding review: claim {d['claim']}, {'over' if compliance else 'under'}-coding signal, {diff}",
            why, diff, Decimal(0) if compliance else diff, deadline, "coder", NEXT_STEPS,
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "claim": d["claim"], "payer": d["payer"], "owner": "coder",
            "risk": "compliance" if compliance else "revenue",
            "lines_judged": d["lines_judged"], "findings": findings, "difference": str(diff),
            "suggestion_only": config.SUGGESTION_ONLY, "deadline": deadline.isoformat(), "card": card,
        }  # fmt: skip
        return Proposal(CODING_REVIEW, payload, diff, Decimal("0.80"), f"a coder has reviewed claim {d['claim']}")

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
