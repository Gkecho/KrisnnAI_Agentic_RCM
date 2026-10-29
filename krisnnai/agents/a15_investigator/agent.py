"""A15 Revenue assurance investigator. Shadow mode only: one review for the revenue assurance lead per flagged slice.

Each event is one payer (or payer and CPT) whose realisation against contract fell. The sweeper already measured
the fall and explained it from the leaks A15-lite detects and from the upstream agents' earlier flags; this agent
restates that for a person and proposes one review. It recovers nothing, changes nothing, contacts no one.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a15_investigator.causes import NOT_SEEN, UNEXPLAINED
from krisnnai.agents.a15_investigator.sweep import EVENT_TYPE
from krisnnai.engine import NO_ACTION, Agent, Context, Proposal, RuleResult, Verification
from krisnnai.engine.card import build_card
from krisnnai.engine.models import ModelResult

AGENT_ID = "a15_investigator"
INVESTIGATION_REVIEW = "a15_investigation_review"
ACTION_TYPES = (INVESTIGATION_REVIEW,)
OWNER = "revenue_assurance_lead"
NEXT_STEPS = [
    "Read the cause table: which leak type holds most of the shortfall",
    "Send each cause to its owner (appeal, underpayment dispute, front-end fix); this agent sends nothing",
    "Confirm the realisation recovers on the next sweep",
]
REVIEW_DAYS = 7
SUGGESTION = "Attribution by key match to detected leaks, not proof of cause; nothing has been recovered or changed."
NOT_RECOVERABLE = {"denial:timely_filing", UNEXPLAINED}


class A15InvestigatorAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = (EVENT_TYPE,)

    # ---------------------------------------------------------------------------------------- 1 trigger
    def wants(self, event: m.Event) -> bool:
        return event.event_type == EVENT_TYPE

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        p = json.loads(event.payload)
        return Context(
            data={**p, "as_of": event.known_at.date().isoformat()},
            lineage={"event_ids": [event.id], "source_file_ids": [event.source_file_id]},
        )

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        d = ctx.data
        if not d["flagged"]:
            return [RuleResult("realisation_recovered", True, "the slice is back within its baseline")]
        return [
            RuleResult("realisation_fell", False,
                       f"{d['baseline']} -> {d['recent']} of contract, {d['impact']} at stake"),
            RuleResult("explained", d["top_cause"] != UNEXPLAINED, f"largest cause: {d['top_cause']}"),
        ]

    # -------------------------------------------------------------------------------- 4 model reasoning
    def model_prompt(self, ctx: Context, checks: list[RuleResult]) -> str | None:
        return None  # the cause table is arithmetic over detected leaks; no model is needed

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        if not d["flagged"]:
            return Proposal(NO_ACTION, {"slice": d["key"], "payer": d["payer"], "cpt": d["cpt"], "flagged": False})
        impact = Decimal(d["impact"])
        recoverable = sum(
            (Decimal(c["dollars"]) for c in d["causes"] if c["cause"] not in NOT_RECOVERABLE), Decimal(0)
        )
        recoverable = min(recoverable, impact)
        deadline = date.fromisoformat(d["as_of"]) + timedelta(days=REVIEW_DAYS)
        what = d["payer"] + (f" CPT {d['cpt']}" if d["cpt"] else "")
        why = [
            f"{what}: paid {Decimal(d['recent']):.1%} of contract in the last {d['recent_days']} days, "
            f"{Decimal(d['baseline']):.1%} in the {d['baseline_days']} days before ({d['lines_recent']} lines)",
        ]
        why += [f"{c['cause']}: {c['dollars']} over {c['lines']} lines" for c in d["causes"]]
        seen = {a: v for a, v in d["upstream"].items() if a != NOT_SEEN}
        if seen:
            why.append("Flagged upstream before billing: " + ", ".join(f"{a} {v}" for a, v in seen.items()))
        if NOT_SEEN in d["upstream"]:
            why.append(f"Not flagged by any upstream agent: {d['upstream'][NOT_SEEN]}")
        why.append(SUGGESTION)
        card = build_card(
            f"Revenue variance: {what}, {Decimal(d['drop']) * 100:.1f} points below baseline, {impact}",
            why, impact, recoverable, deadline, OWNER, NEXT_STEPS,
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "slice": d["key"], "payer": d["payer"], "cpt": d["cpt"], "owner": OWNER, "flagged": True,
            "baseline": d["baseline"], "recent": d["recent"], "drop": d["drop"], "impact": d["impact"],
            "shortfall": d["shortfall"], "causes": d["causes"], "upstream": d["upstream"],
            "top_cause": d["top_cause"], "deadline": deadline.isoformat(), "suggestion_only": SUGGESTION, "card": card,
        }  # fmt: skip
        return Proposal(
            INVESTIGATION_REVIEW, payload, impact, Decimal("0.70"), f"{d['key']} realisation is back within baseline"
        )

    # ------------------------------------------------------------------------------- 8 verify and learn
    def verify(self, proposal: Proposal, execution_result: str) -> Verification:
        return Verification(proposal.verification_condition, "not_run")
