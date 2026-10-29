"""A6 claim submission and response agent, response side. Shadow mode only.

It reads the 999 and 277CA acknowledgements, decides whether a rejection is technical (a person approves a prepared
packet for resubmission) or needs business judgement (a task for the owner), and shows the likely cause. It never
edits a code, a modifier or a diagnosis (rule 4) and never sends anything (rule 3): the only action that could ever
reach the clearinghouse adapter is a human-approved resubmission of an unchanged packet, and that stays off until the
tenant's policy turns it on. The release side (submitting claims A5 has cleared) waits for a release signal that
does not exist yet.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.agents.a5_prevention import config as a5_config
from krisnnai.agents.a5_prevention import rules as a5_rules
from krisnnai.agents.a5_prevention.agent import A5PreventionAgent
from krisnnai.agents.a6_submission import config, packet
from krisnnai.agents.a15_lite.expected import money
from krisnnai.agents.a15_lite.pricing import BILLED_FALLBACK, ClaimPricer
from krisnnai.engine import Agent, Context, Proposal, RuleResult
from krisnnai.engine.card import build_card
from krisnnai.engine.models import ModelResult

AGENT_ID = "a6_submission"
TRIGGER_277 = "277CA.claim_status"
TRIGGER_999 = "999.ack"

# The only things A6 can propose. Both are tasks or reviews for a human: no submit, write-off, refund or code change.
RESUBMIT_REVIEW = "a6_resubmit_review"
REJECTION_TASK = "a6_rejection_task"
ACTION_TYPES = (RESUBMIT_REVIEW, REJECTION_TASK)

REJECTED_277 = ("A3", "A4")  # returned as unprocessable, claim not found
REJECTED_999 = ("R", "E")  # rejected, accepted with errors
MAX_ANALYSED = 25  # claims examined in detail per acknowledgement (a 999 can cover hundreds)

NEXT_STEPS = {
    RESUBMIT_REVIEW: [
        "Check that the prepared packet matches the claim in the PM system",
        "Approve resubmission through the clearinghouse (a person approves; the agent never sends on its own)",
        "Confirm the next 999 / 277CA accepts it",
    ],
    REJECTION_TASK: [
        "Read the rejection reason and the likely causes",
        "Fix the cause in the PM system (a person edits; the agent never changes codes)",
        "Resubmit the claim once it is fixed",
    ],
}


def trigger_source(event: m.Event) -> str | None:
    """'999' or '277CA' when this event is a rejection A6 handles, else None. Decided from the payload alone."""
    payload = json.loads(event.payload)
    if event.event_type == TRIGGER_277 and payload.get("status_category") in REJECTED_277:
        return "277CA"
    if event.event_type == TRIGGER_999 and payload.get("transaction_status") in REJECTED_999:
        return "999"
    return None


class A6SubmissionAgent(Agent):
    agent_id = AGENT_ID
    version = "0.1"
    trigger_types = (TRIGGER_277, TRIGGER_999)

    def __init__(self):
        self._pricer = ClaimPricer()
        self._a5 = A5PreventionAgent()

    # ---------------------------------------------------------------------------------------- 1 trigger
    def wants(self, event: m.Event) -> bool:
        return trigger_source(event) is not None

    # --------------------------------------------------------------------------------- 2 context pack
    def context_pack(self, session: Session, event: m.Event, as_of: datetime) -> Context:
        source = trigger_source(event)
        if source == "277CA":
            ack = session.scalars(select(m.Ack277Ca).where(m.Ack277Ca.event_id == event.id)).one()
            category, code, codes = ack.status_category, ack.status_code, ""
            claims = self._claims_by_sid(session, ack.claim_submitter_id, as_of)
            payer_claim_number = ack.payer_claim_number
        else:
            ack = session.scalars(select(m.Ack999).where(m.Ack999.event_id == event.id)).one()
            category, code, codes = ack.transaction_status, None, ack.error_codes or ""
            claims = self._claims_in_transaction(session, ack.acked_gs06, ack.acked_st02, as_of)
            payer_claim_number = None
        route = config.find_route(config.load_routes(session), source, category, code)
        reason = {
            "source": source, "status_category": category, "status_code": code or "", "error_codes": codes,
            "category": route.category if route else "unrouted",
            "description": route.description if route else "No routing row for this status",
        }  # fmt: skip
        rules = a5_config.load(session)
        packets, causes, deadlines, charge, priced = [], [], [], Decimal(0), []
        packets_ok = True
        payer_codes: set[str] = set()
        for claim in claims:
            payer = session.get(m.Payer, claim.payer_id)
            payer_codes.add(payer.payer_id_code)
            filing_days = rules.filing_days.get(claim.payer_id, a5_config.DEFAULT_FILING_DAYS)
            if claim.service_date:
                deadlines.append(claim.service_date + timedelta(days=filing_days))
            charge += claim.total_charge
            if len(packets) >= MAX_ANALYSED:
                continue
            lines = list(session.scalars(select(m.ClaimLine).where(m.ClaimLine.claim_id == claim.id)))
            dx = list(session.scalars(select(m.ClaimDx).where(m.ClaimDx.claim_id == claim.id)))
            pk = packet.build_packet(claim, lines, dx, payer.payer_id_code, reason, payer_claim_number)
            packets_ok = packets_ok and packet.unchanged(pk, claim, lines, dx)
            packets.append(pk)
            if source == "277CA":
                priced.append(self._pricer.price(session, as_of.date(), payer.payer_id_code, lines,
                                                 claim.service_date, claim.total_charge))  # fmt: skip
            snapshot = self._a5.context_pack(session, session.get(m.Event, claim.event_id), as_of)
            for r in a5_rules.run_all(snapshot.data):
                if not r.result and len(causes) < 10:
                    causes.append({"claim": claim.claim_submitter_id, "rule": r.rule_id, "detail": r.detail})
        if source == "277CA" and priced:
            amount, basis = priced[0]
        else:
            amount, basis = money(charge), "billed_charge"
        deadline = min(deadlines) if deadlines else None
        data = {
            "source": source, "reason": reason, "kind": route.kind if route else "business",
            "owner": route.owner if route else "billing", "unrouted": route is None,
            "claims": [c.claim_submitter_id for c in claims], "claims_total": len(claims),
            "analysed": len(packets), "payers": sorted(payer_codes), "amount": str(amount), "pricing_basis": basis,
            "filing_deadline": deadline.isoformat() if deadline else "",
            "filing_days_left": (deadline - as_of.date()).days if deadline else None,
            "packets": packets, "packets_unchanged": packets_ok, "likely_causes": causes,
            "as_of": as_of.date().isoformat(),
        }  # fmt: skip
        file_ids = [ack.source_file_id] + [c.source_file_id for c in claims[:MAX_ANALYSED]]
        return Context(data=data, lineage={"event_ids": [event.id], "source_file_ids": sorted(set(file_ids))})

    @staticmethod
    def _claims_by_sid(session: Session, sid: str, as_of: datetime) -> list[m.Claim]:
        """The claim an acknowledgement names: the newest version of that submitter id known by `as_of`."""
        stmt = (
            select(m.Claim)
            .join(m.Event, m.Event.id == m.Claim.event_id)
            .where(m.Claim.claim_submitter_id == sid, m.Event.known_at <= as_of)
            .order_by(m.Event.known_at.desc(), m.Claim.id.desc())
        )
        found = session.scalars(stmt).first()
        return [found] if found else []

    @staticmethod
    def _claims_in_transaction(session: Session, gs06: str, st02: str, as_of: datetime) -> list[m.Claim]:
        """Claims whose 837 event carries the acknowledged group and transaction set control numbers."""
        stmt = (
            select(m.Claim)
            .join(m.Event, m.Event.id == m.Claim.event_id)
            .where(m.Event.gs06 == gs06, m.Event.st02 == st02, m.Event.known_at <= as_of)
            .order_by(m.Claim.id)
        )
        return list(session.scalars(stmt))

    @staticmethod
    def _left_text(left: int | None) -> str:
        return "no service date" if left is None else f"{left}d"

    # --------------------------------------------------------------------------- 3 deterministic checks
    def deterministic_checks(self, ctx: Context) -> list[RuleResult]:
        d = ctx.data
        left = d["filing_days_left"]
        return [
            RuleResult("rejection_routed", not d["unrouted"], d["reason"]["category"]),
            RuleResult("claim_matched", d["claims_total"] > 0, f"{d['claims_total']} claim(s)"),
            RuleResult("packet_unchanged", d["packets_unchanged"], "codes, diagnoses, units, charges copied verbatim"),
            RuleResult("within_filing_limit", left is None or left >= 0, self._left_text(left)),
            RuleResult("amount_priced", d["pricing_basis"] != BILLED_FALLBACK, d["pricing_basis"]),
        ]  # fmt: skip

    # ------------------------------------------------------------------ 5 confidence and materiality
    def assess(self, ctx: Context, checks: list[RuleResult], model: ModelResult | None) -> Proposal:
        d = ctx.data
        amount = Decimal(d["amount"])
        technical = d["kind"] == "technical" and d["claims_total"] > 0 and d["packets_unchanged"]
        action = RESUBMIT_REVIEW if technical else REJECTION_TASK
        left = d["filing_days_left"]
        urgency = Decimal(1) + (1 if left is not None and left <= config.FILING_RISK_DAYS else 0)
        priority = money(amount * urgency)
        as_of = date.fromisoformat(d["as_of"])
        fix_by = as_of + timedelta(days=config.FIX_DAYS)
        deadline = min(fix_by, date.fromisoformat(d["filing_deadline"])) if d["filing_deadline"] else fix_by
        r = d["reason"]
        why = [
            f"{r['source']} {r['status_category']} {r['status_code']}: {r['description']}".replace("  ", " "),
            f"{d['claims_total']} claim(s) affected, {d['amount']} ({d['pricing_basis']})",
            "Technical: the claim data is fine, the file or format was wrong" if technical else "Needs a person",
        ]  # fmt: skip
        if r["error_codes"]:
            why.append(f"Errors reported: {r['error_codes']}")
        why += [f"Likely cause, claim {c['claim']}: {c['rule']} ({c['detail']})" for c in d["likely_causes"][:3]]
        if left is not None and left <= config.FILING_RISK_DAYS:
            why.append(f"Only {left} days left before the filing limit ({d['filing_deadline']})")
        owner = d["owner"]
        card = build_card(
            f"Rejected ({r['source']} {r['status_category']}): {d['claims_total']} claim(s), {d['amount']}",
            why, priority, amount, deadline, owner, NEXT_STEPS[action],
            [{"rule": c.rule_id, "result": c.result, "detail": c.detail} for c in checks],
        )  # fmt: skip
        payload = {
            "source": d["source"], "status_category": r["status_category"], "status_code": r["status_code"],
            "category": r["category"], "kind": d["kind"], "owner": owner, "unrouted": d["unrouted"],
            "description": r["description"], "error_codes": r["error_codes"], "claims": d["claims"],
            "claims_total": d["claims_total"], "analysed": d["analysed"], "payers": d["payers"],
            "amount": d["amount"], "pricing_basis": d["pricing_basis"], "filing_deadline": d["filing_deadline"],
            "filing_days_left": left, "fix_by": fix_by.isoformat(), "urgency": str(urgency), "priority": str(priority),
            "likely_causes": d["likely_causes"], "packets": d["packets"] if technical else [], "card": card,
        }  # fmt: skip
        confidence = Decimal("0.50") if d["unrouted"] else Decimal("0.95")
        return Proposal(
            action, payload, amount, confidence,
            f"the rejected claim(s) are accepted by the next 999 / 277CA, or the {owner} task is closed, by {fix_by}",
        )  # fmt: skip
