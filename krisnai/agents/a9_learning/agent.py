"""A9 Denial prevention learning agent. Shadow mode only: it proposes a rule, a manager decides, nothing changes itself.

Each `denial.pattern_found` event is one recurring defect: a payer keeps denying claims that carry one CPT with one
CARC. The agent re-clusters as of the event date, checks whether A5 already flagged those claims before release,
replays the candidate rule over the history it has seen (in-sample precision, recall, dollars) and proposes one review
for the practice manager. The candidate becomes a rule only through `krisnai a9 approve`, with a named approver.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a9_learning.clusters import clusters_from, in_window, outcomes
from krisnai.agents.a9_learning import config
from krisnai.agents.a15_lite.expected import money
from krisnai.agents.a15_lite.pricing import ClaimPricer
from krisnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnai.engine.card import build_card
from krisnai.engine.models import ModelResult

AGENT_ID = "a9_learning"
EVENT_TYPE = "denial.pattern_found"
RULE_REVIEW = "a9_rule_proposal_review"
ACTION_TYPES = (RULE_REVIEW,)
REVIEW_DAYS = 14  # how long the manager has to decide; TBD at spec review
NEXT_STEPS = [
    "Read the pattern and the sample claims",
    "Approve it (krisnai a9 approve --rule KEY --by NAME) so A5 starts flagging matching claims, or reject it",
    "Nothing changes until a named person approves",
]


class A9LearningAgent(Agent):
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
        items = in_window(outcomes(session, day), day)
        found = {c.key: c for c in clusters_from(items)}
        c = found.get(payload["rule_key"])
        base = {"rule_key": payload["rule_key"], "payer": payload["payer"], "cpt": payload["cpt"],
                "carc": payload["carc"], "as_of": day.isoformat(), "qualifies": c is not None}  # fmt: skip
        if c is None:
            return Context(data=base, lineage={"event_ids": [event.id], "source_file_ids": []})
        by_id = {o.claim_id: o for o in items}
        sids = sorted(by_id[i].sid for i in c.denied_claims)
        flagged = 0
        if sids:
            recs = s_flagged(session, set(sids), event.known_at)
            flagged = len(recs)
        total_denied = sum(1 for o in items if o.payer == c.payer and c.carc in o.carcs)
        lines = list(session.scalars(select(m.ClaimLine).where(m.ClaimLine.claim_id.in_(c.denied_claims))))
        dollars = Decimal(0)
        for claim_id in c.denied_claims:
            amount, _ = self._pricer.price(
                session, day, c.payer, [ln for ln in lines if ln.claim_id == claim_id], None, Decimal(0)
            )
            dollars += amount
        base.update({
            "n_denials": c.n_denials, "n_adjudicated": c.n_adjudicated, "rate": str(c.rate.quantize(Decimal("0.0001"))),
            "recall": str((Decimal(c.n_denials) / Decimal(total_denied)).quantize(Decimal("0.0001"))),
            "flagged_by_a5": flagged, "dollars": str(money(dollars)), "sample_claims": sids[: config.SAMPLE_CLAIMS],
            "first_denial": min(c.denied_dates).isoformat() if c.denied_dates else None,
            "last_denial": max(c.denied_dates).isoformat() if c.denied_dates else None,
        })  # fmt: skip
        return Context(
            data=base,
            lineage={"event_ids": [event.id], "source_file_ids": sorted({ln.source_file_id for ln in lines})},
        )

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        d = ctx.data
        if not d["qualifies"]:
            return [RuleResult("cluster_qualifies", False, "no longer meets the denial count and rate thresholds")]
        share = Decimal(d["flagged_by_a5"]) / Decimal(d["n_denials"])
        return [
            RuleResult("cluster_qualifies", True, f"{d['n_denials']} denials at {d['rate']} of {d['n_adjudicated']}"),
            RuleResult("not_already_flagged", share < config.ALREADY_FLAGGED, f"A5 flagged {d['flagged_by_a5']}"),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        return None  # the proposal is a rule and its measured effect: nothing here needs a model

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        if not all(c.result for c in checks):
            return Proposal(NO_ACTION, {"rule_key": d["rule_key"], "reason": next(c.rule_id for c in checks
                                                                                  if not c.result)})  # fmt: skip
        dollars = Decimal(d["dollars"])
        deadline = date.fromisoformat(d["as_of"]) + timedelta(days=REVIEW_DAYS)
        why = [
            f"{d['payer']} denied {d['n_denials']} of {d['n_adjudicated']} claims carrying {d['cpt']} "
            f"with CARC {d['carc']} ({Decimal(d['rate']):.0%}); the rule would have caught "
            f"{Decimal(d['recall']):.0%} of that payer's CARC {d['carc']} denials",
            f"{dollars} of expected payment was denied; A5 flagged {d['flagged_by_a5']} of these claims before release",
            "Tested on history only (in-sample); a forward test runs after approval",
        ]
        card = build_card(
            f"Proposed rule: {d['payer']} + {d['cpt']} is denied with CARC {d['carc']}",
            why, dollars, dollars, deadline, "practice_manager", NEXT_STEPS,
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "rule_key": d["rule_key"], "payer": d["payer"], "cpt": d["cpt"], "carc": d["carc"],
            "owner": "practice_manager", "n_denials": d["n_denials"], "n_adjudicated": d["n_adjudicated"],
            "rate": d["rate"], "recall": d["recall"], "flagged_by_a5": d["flagged_by_a5"], "dollars": d["dollars"],
            "sample_claims": d["sample_claims"], "first_denial": d["first_denial"], "last_denial": d["last_denial"],
            "proposed_on": d["as_of"], "deadline": deadline.isoformat(), "card": card,
        }  # fmt: skip
        return Proposal(
            RULE_REVIEW, payload, dollars, Decimal("0.70"), f"rule {d['rule_key']} is approved or rejected by a person"
        )

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")


def s_flagged(session: Session, sids: set[str], known_at: datetime) -> set[str]:
    """Claim ids (submitter ids) among `sids` that A5 flagged before release (a non-empty A5 decision known by then)."""
    out: set[str] = set()
    rows = session.execute(
        select(m.DecisionRecord.action_type, m.DecisionRecord.action_payload)
        .join(m.Event, m.Event.id == m.DecisionRecord.event_id)
        .where(m.DecisionRecord.agent_id == "a5_prevention", m.Event.known_at <= known_at)
    )
    for action, payload in rows:
        if action != NO_ACTION:
            sid = json.loads(payload).get("claim")
            if sid in sids:
                out.add(sid)
    return out
