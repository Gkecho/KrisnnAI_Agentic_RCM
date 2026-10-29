"""A5 Claim prevention agent. Shadow mode only: it flags defects before release and proposes a task for a human.

It never edits a code, a modifier or a claim (rule 4) and never submits (rule 3). Which proposals the engine may act on
is the tenant's policy; the default for every action type is shadow.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a5_prevention import config, rules
from krisnnai.agents.rejections import rejection_sets
from krisnnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult
from krisnnai.engine.card import build_card
from krisnnai.engine.models import ModelResult

AGENT_ID = "a5_prevention"
TRIGGER = "837P.claim"

# The only things A5 can propose. Both are tasks for a named human.
FIX_TASK = "a5_fix_task"
HOLD_REVIEW = "a5_hold_review"
ACTION_TYPES = (FIX_TASK, HOLD_REVIEW)

# A failed rule that means "do not release until a person looks": the claim would be denied or lost as it stands.
HOLD_RULES = ("duplicate_claim", "timely_filing", "ncci_pair")
RELEASE_FIX_DAYS = 2  # target days to fix a flagged claim before it is released; TBD at spec review
OWNER = {
    "required_fields": "billing",
    "duplicate_claim": "billing",
    "timely_filing": "billing",
    "ncci_pair": "coding",
    "mue_units": "coding",
    "learned_pattern": "billing",
}


def _iso(d: date | None) -> str:
    return d.isoformat() if d else ""


class A5PreventionAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = (TRIGGER,)

    def __init__(self):
        self._rejections: dict[tuple[int, datetime], tuple] = {}  # bounced claims by tenant + as-of, reused in a run

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        claim = session.scalars(select(m.Claim).where(m.Claim.event_id == event.id)).one()
        lines = list(
            session.scalars(
                select(m.ClaimLine).where(m.ClaimLine.claim_id == claim.id).order_by(m.ClaimLine.line_number)
            )
        )
        dx = list(session.scalars(select(m.ClaimDx).where(m.ClaimDx.claim_id == claim.id)))
        payer = session.get(m.Payer, claim.payer_id)
        data = config.load(session)
        cpts = {ln.cpt for ln in lines}
        codes = sorted(ln.cpt for ln in lines)
        # point in time (rule 9): only claims whose events were known by this event's time, and filed earlier
        known = select(m.Event.id).where(m.Event.known_at <= as_of, m.Event.id < event.id)
        others = session.scalars(
            select(m.Claim).where(
                m.Claim.event_id.in_(known),
                m.Claim.patient_ref_id == claim.patient_ref_id,
                m.Claim.payer_id == claim.payer_id,
                m.Claim.service_date == claim.service_date,
            )
        )
        key = (session.info["tenant_id"], as_of)
        if key not in self._rejections:  # a bounced claim never reached adjudication, so it cannot be a duplicate
            self._rejections[key] = rejection_sets(session, as_of)
        returned, rejected_files = self._rejections[key]
        duplicates = []
        for o in others:
            their = sorted(session.scalars(select(m.ClaimLine.cpt).where(m.ClaimLine.claim_id == o.id)))
            ev = session.get(m.Event, o.event_id)
            if o.claim_submitter_id in returned or (ev.gs06, ev.st02) in rejected_files:
                continue
            if their == codes and o.frequency_code == claim.frequency_code == "1":
                duplicates.append(o.claim_submitter_id)
        snapshot = {
            "claim": claim.claim_submitter_id,
            "payer": payer.payer_id_code,
            "total_charge": str(claim.total_charge),
            "service_date": _iso(claim.service_date),
            "as_of": as_of.date().isoformat(),
            "diagnoses": [d.dx_code for d in dx],
            "lines": [
                {
                    "line_number": ln.line_number,
                    "cpt": ln.cpt,
                    "modifiers": [x for x in (ln.modifier_1, ln.modifier_2, ln.modifier_3, ln.modifier_4) if x],
                    "units": str(ln.units),
                    "diagnosis_pointer": ln.diagnosis_pointer or "",
                    "service_date": _iso(ln.service_date or claim.service_date),
                }
                for ln in lines
            ],
            "duplicates": sorted(duplicates),
            "filing_days": data.filing_days.get(claim.payer_id, config.DEFAULT_FILING_DAYS),
            "filing_days_from_table": claim.payer_id in data.filing_days,
            "ncci": {"|".join(sorted(k)): v for k, v in data.ncci.items() if k <= cpts},
            "mue": {c: data.mue[c] for c in sorted(cpts) if c in data.mue},
            "not_evaluated": list(rules.NOT_EVALUATED),
        }
        hits = [
            {"rule_key": key, "cpt": cpt, "carc": carc}
            for cpt, (key, carc) in sorted(data.learned.get(claim.payer_id, {}).items())
            if cpt in cpts
        ]
        if data.learned:  # present only once a manager approved a learned rule; before that A5 is unchanged
            snapshot["learned"] = hits
        return Context(data=snapshot, lineage={"event_ids": [event.id], "source_file_ids": [claim.source_file_id]})

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        return rules.run_all(ctx.data)

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        failed = [c for c in checks if not c.result]
        if not failed:
            return Proposal(NO_ACTION, {"claim": d["claim"], "not_evaluated": d["not_evaluated"]})
        hold = any(c.rule_id in HOLD_RULES for c in failed)
        owner = "coding" if all(OWNER[c.rule_id] == "coding" for c in failed) else "billing"
        amount = Decimal(d["total_charge"])
        names = ", ".join(c.rule_id for c in failed)
        card = build_card(
            f"{'Hold' if hold else 'Fix'} claim {d['claim']} before release: {names}",
            [f"{c.rule_id}: {c.detail}" for c in failed] + ["Checked before release; nothing has been sent"],
            amount, amount, date.fromisoformat(d["as_of"]) + timedelta(days=RELEASE_FIX_DAYS), owner,
            ["Fix the named defect in the PM system (a person edits; the agent never changes codes)",
             "Re-check the claim, then release it"],
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "claim": d["claim"],
            "payer": d["payer"],
            "action": "hold_for_review" if hold else "fix_before_release",
            "owner": owner,
            "failed_rules": [{"rule": c.rule_id, "detail": c.detail, "owner": OWNER[c.rule_id]} for c in failed],
            "amount_at_risk": d["total_charge"],
            "not_evaluated": d["not_evaluated"],
            "card": card,
        }
        return Proposal(
            HOLD_REVIEW if hold else FIX_TASK,
            payload,
            Decimal(d["total_charge"]),
            Decimal("0.95"),
            f"a {owner} task for claim {d['claim']} is closed and the rules pass on re-check",
        )
