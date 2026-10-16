"""The cross-agent decision inbox: every agent's open card as of a date, ranked.

Reads the decision records of A5, A6, A7 and A8 that were known by `as_of`, keeps the latest card per claim, and drops
any item that is no longer open. "Open" differs by agent (a prevention flag is stale once the payer answers; a denial
is stale once a later payment arrives), so each rule is written out below. Priority scales differ by agent (A7 and A6
weight dollars by urgency, A8 uses expected recovery, A5 uses the charge at risk); calibrating them is a sign-off item.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.engine import NO_ACTION
from krisnai.model import tenant_session

AGENTS = (
    "a5_prevention", "a6_submission", "a7_ar", "a8_denial", "a10_underpay", "a3_documentation", "a1_clearance",
    "a9_learning", "a2_authorization", "a11_cash", "a13_credentialing", "a12_patient", "a4_coding",
    "a15_investigator",
)  # fmt: skip
QUEUE_TYPE = {"a8_denial": "Denial", "a6_submission": "Rejection", "a10_underpay": "Underpaid"}  # worklist pill by agent
FILING_RISK_DAYS = 60  # an A7 item this close to the payer's filing limit is shown as "Filing risk" (matches A7's urgency window)
CLAIM_AGENTS = {"a5_prevention", "a6_submission", "a7_ar", "a8_denial", "a10_underpay", "a4_coding"}  # cards about one claim
AGE_BUCKETS = ((7, "0-7"), (14, "8-14"), (30, "15-30"))  # days since the card was raised
DUE_SOON_DAYS = 7  # an item due within this many days counts as deadline-critical; TBD at spec review


def age_bucket(age_days: int) -> str:
    for limit, label in AGE_BUCKETS:
        if age_days <= limit:
            return label
    return "30+"


def queue_type(agent_id: str, filing_days_left: int | None) -> str | None:
    """The biller worklist pill: Denial / Rejection / Underpaid by agent; A7 is Filing risk near the limit, else No response."""
    if agent_id == "a7_ar":
        return "Filing risk" if filing_days_left is not None and filing_days_left <= FILING_RISK_DAYS else "No response"
    return QUEUE_TYPE.get(agent_id)


def _claim_facts(engine: Engine, tenant_id: int, end: datetime) -> dict[str, tuple[str, str, Decimal]]:
    """claim submitter id -> (payer name, payer id code, billed) of the latest claim version known by `end`."""
    out: dict[str, tuple[str, str, Decimal]] = {}
    with tenant_session(engine, tenant_id) as s:
        for sid, name, code, billed in s.execute(
            select(m.Claim.claim_submitter_id, m.Payer.name, m.Payer.payer_id_code, m.Claim.total_charge)
            .join(m.Event, m.Event.id == m.Claim.event_id)
            .join(m.Payer, m.Payer.id == m.Claim.payer_id)
            .where(m.Event.known_at <= end)
            .order_by(m.Event.known_at, m.Claim.id)
        ):
            out[sid] = (name, code, billed)
    return out


def _claims_of(agent_id: str, p: dict) -> list[str]:
    if agent_id == "a6_submission":
        return list(p["claims"])
    if agent_id == "a3_documentation":  # a visit, not a claim
        return [p["visit"]] if p.get("visit") else []
    if agent_id in ("a1_clearance", "a2_authorization"):  # an appointment, not a claim
        return [p["appt"]] if p.get("appt") else []
    if agent_id == "a13_credentialing":  # a provider (and payer), not a claim
        return [p["key"]] if p.get("key") else []
    if agent_id == "a11_cash":  # a payment (or a bank deposit), not a claim
        key = p.get("trace") or p.get("deposit_ref")
        return [key] if key else []
    if agent_id == "a9_learning":  # a proposed rule, not a claim
        return [p["rule_key"]] if p.get("rule_key") else []
    if agent_id == "a15_investigator":  # a payer (and CPT) slice, not a claim
        return [p["slice"]] if p.get("slice") else []
    return [p["claim"]] if p.get("claim") else []


def open_cards(engine: Engine, tenant_id: int, as_of: date) -> list[dict]:
    end = datetime.combine(as_of, time.max)
    with tenant_session(engine, tenant_id) as s:
        rows = s.execute(
            select(m.DecisionRecord, m.Event.known_at)
            .join(m.Event, m.Event.id == m.DecisionRecord.event_id)
            .where(m.DecisionRecord.agent_id.in_(AGENTS), m.Event.known_at <= end)
            .order_by(m.Event.known_at, m.DecisionRecord.id)
        ).all()
        decided = set(s.scalars(select(m.LearnedRule.rule_key).where(m.LearnedRule.status != "proposed")))
        remits: dict[str, list[tuple[datetime, Decimal, str]]] = {}
        for sid, known, paid, status in s.execute(
            select(m.Remit.claim_submitter_id, m.Event.known_at, m.Remit.total_paid, m.Remit.claim_status_code)
            .join(m.Event, m.Event.id == m.Remit.event_id)
            .where(m.Event.known_at <= end)
        ):
            remits.setdefault(sid, []).append((known, paid, status))
        filed: dict[str, list[datetime]] = {}
        for sid, known in s.execute(
            select(m.Claim.claim_submitter_id, m.Event.known_at)
            .join(m.Event, m.Event.id == m.Claim.event_id)
            .where(m.Event.known_at <= end)
        ):
            filed.setdefault(sid, []).append(known)

    latest: dict[tuple[str, str], tuple] = {}
    for rec, known in rows:
        if rec.action_type == NO_ACTION:
            latest.pop((rec.agent_id, _key(rec, json.loads(rec.action_payload))), None)
            continue
        p = json.loads(rec.action_payload)
        if "card" not in p:
            continue
        latest[(rec.agent_id, _key(rec, p))] = (rec, known, p)

    facts = _claim_facts(engine, tenant_id, end)
    cards = []
    for (agent_id, _), (rec, known, p) in latest.items():
        if not _is_open(agent_id, known, p, remits, filed, as_of, decided):
            continue
        card = p["card"]
        deadline = date.fromisoformat(card["deadline"])
        age = (as_of - known.date()).days
        claim_ids = _claims_of(agent_id, p)
        fact = facts.get(claim_ids[0]) if len(claim_ids) == 1 and agent_id in CLAIM_AGENTS else None
        filing_left = p.get("filing_days_left") if agent_id == "a7_ar" else None
        cards.append(
            {
                "agent": agent_id, "action_type": rec.action_type, "claim": ",".join(_claims_of(agent_id, p)),
                "record_id": rec.id, "title": card["title"], "owner": card["owner"],
                "priority": Decimal(card["priority"]), "expected_value": Decimal(card["expected_value"]),
                "deadline": deadline.isoformat(), "overdue": deadline < as_of,
                "due_soon": deadline <= as_of + timedelta(days=DUE_SOON_DAYS),
                "raised_on": known.date().isoformat(), "age_days": age, "age_bucket": age_bucket(age), "card": card,
                "payer": fact[0] if fact else "", "payer_code": fact[1] if fact else "",
                "billed": fact[2] if fact else None, "queue_type": queue_type(agent_id, filing_left),
                "confidence": rec.confidence, "filing_days_left": filing_left,
            }
        )  # fmt: skip
    cards.sort(key=lambda c: (-c["priority"], c["agent"], c["claim"]))
    return cards


def _key(rec: m.DecisionRecord, p: dict) -> str:
    claims = _claims_of(rec.agent_id, p)
    if rec.agent_id == "a6_submission" and len(claims) != 1:
        return f"event{rec.event_id}"  # a 999 covering many claims is one item
    return claims[0] if claims else f"record{rec.id}"


def _is_open(
    agent_id: str, raised: datetime, p: dict, remits: dict, filed: dict, as_of: date, decided: set[str]
) -> bool:
    if agent_id == "a9_learning":  # open until a named person approves or rejects the rule
        return p["rule_key"] not in decided
    if agent_id in ("a1_clearance", "a2_authorization"):  # matters until the visit; then A15, A8 and A10 take over
        return date.fromisoformat(p["appt_date"]) >= as_of
    if agent_id == "a15_investigator":  # open until a later sweep finds the slice back within baseline (no_action)
        return True
    claims = _claims_of(agent_id, p)
    if not claims:  # a recoupment has no claim: it stays until a person closes it
        return True
    if agent_id in ("a5_prevention", "a7_ar"):  # the payer has not answered yet
        return not any(c in remits for c in claims)
    if agent_id == "a6_submission":  # unanswered and not re-filed since the rejection
        return any(c not in remits and not any(t > raised for t in filed.get(c, [])) for c in claims)
    paid_later = any(
        known > raised and paid > 0 and status != "22" for known, paid, status in remits.get(claims[0], [])
    )
    return not paid_later  # a8: a later payment closes it
