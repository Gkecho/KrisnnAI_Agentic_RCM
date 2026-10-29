"""The decision inbox, text version: A7's latest card per claim, ranked by priority.

The same records feed a screen later; nothing here is specific to a terminal. A claim that has had several follow-ups
shows only its most recent card. A claim is left out once the payer has answered it (as of `as_of`, default: everything
known), because a card raised earlier is then stale.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a7_ar.agent import AGENT_ID
from krisnnai.agents.a7_ar.sweep import EVENT_TYPE
from krisnnai.engine import NO_ACTION
from krisnnai.model import tenant_session


def inbox(engine: Engine, tenant_id: int, top: int | None = None, as_of: date | None = None) -> list[dict]:
    latest: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        remits = (
            select(m.Remit.claim_id)
            .join(m.Event, m.Event.id == m.Remit.event_id)
            .where(m.Remit.claim_id.is_not(None))
        )
        if as_of is not None:
            remits = remits.where(m.Event.known_at <= datetime.combine(as_of, time.max))
        answered = set(s.scalars(remits))
        rows = s.execute(
            select(m.DecisionRecord, m.Event.known_at)
            .join(m.Event, m.Event.id == m.DecisionRecord.event_id)
            .where(m.DecisionRecord.agent_id == AGENT_ID)
            .order_by(m.Event.known_at, m.DecisionRecord.id)
        ).all()
        trigger_rows = s.execute(select(m.Event.id, m.Event.payload).where(m.Event.event_type == EVENT_TYPE))
        claim_ids = {e_id: json.loads(payload)["claim_id"] for e_id, payload in trigger_rows}
        for rec, known in rows:
            claim = json.loads(rec.action_payload)["claim"]
            latest[claim] = (rec, known)  # later rows replace earlier ones
        cards = []
        for rec, known in latest.values():
            if rec.action_type == NO_ACTION or claim_ids.get(rec.event_id) in answered:
                continue
            p = json.loads(rec.action_payload)
            cards.append(
                {
                    "claim": p["claim"], "payer": p["payer"], "action": rec.action_type, "issue": p["issue"],
                    "bucket": p["aging_bucket"], "age_days": p["age_days"], "amount": Decimal(p["amount"]),
                    "priority": Decimal(p["priority"]), "owner": p["owner"], "deadline": p["card"]["deadline"],
                    "as_of": known.date().isoformat(), "record_id": rec.id, "card": p["card"],
                }
            )  # fmt: skip
    cards.sort(key=lambda c: (-c["priority"], c["claim"]))
    return cards[:top] if top else cards


def format_inbox(cards: list[dict], tenant_id: int) -> str:
    total = sum((c["amount"] for c in cards), Decimal(0))
    buckets = Counter(c["bucket"] for c in cards)
    out = [
        f"A7 inbox - tenant {tenant_id}: {len(cards)} claims to work, {total} unpaid",
        "aging  " + "  ".join(f"{b}: {buckets.get(b, 0)}" for b in ("0-30", "31-60", "61-90", "90+")),
        f"{'#':>3s} {'priority':>9s} {'amount':>9s} {'age':>4s}  {'payer':10s}{'claim':14s}{'owner':9s}{'due':11s}"
        "action",
    ]
    for i, c in enumerate(cards, start=1):
        out.append(
            f"{i:3d} {c['priority']:9.2f} {c['amount']:9.2f} {c['age_days']:4d}  {c['payer']:10s}{c['claim']:14s}"
            f"{c['owner']:9s}{c['deadline']:11s}{c['action']}"
        )
    return "\n".join(out)
