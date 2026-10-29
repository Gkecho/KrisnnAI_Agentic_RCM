"""A9 results after a replay: the proposed rules and where each stands."""

from __future__ import annotations

import json
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a9_learning.agent import AGENT_ID, RULE_REVIEW
from krisnnai.model import tenant_session


def proposals(engine: Engine, tenant_id: int) -> list[dict]:
    """The latest proposal per rule key, with the manager's decision (proposed until someone decides)."""
    latest: dict[str, dict] = {}
    with tenant_session(engine, tenant_id) as s:
        for rec in s.scalars(
            select(m.DecisionRecord)
            .where(m.DecisionRecord.agent_id == AGENT_ID, m.DecisionRecord.action_type == RULE_REVIEW)
            .order_by(m.DecisionRecord.id)
        ):
            p = json.loads(rec.action_payload)
            latest[p["rule_key"]] = p
        status = {r.rule_key: r for r in s.scalars(select(m.LearnedRule))}
        executed = sum(
            1 for r in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID))
            if r.outcome == "executed"
        )  # fmt: skip
    out = []
    for key, p in sorted(latest.items(), key=lambda kv: -Decimal(kv[1]["dollars"])):
        row = status.get(key)
        out.append({
            "rule_key": key, "payer": p["payer"], "cpt": p["cpt"], "carc": p["carc"], "n_denials": p["n_denials"],
            "n_adjudicated": p["n_adjudicated"], "rate": p["rate"], "recall": p["recall"],
            "flagged_by_a5": p["flagged_by_a5"], "dollars": p["dollars"], "proposed_on": p["proposed_on"],
            "status": row.status if row else "proposed", "approved_by": row.approved_by if row else None,
            "executed": executed,
        })  # fmt: skip
    return out


def format_summary(items: list[dict], tenant_id: int) -> str:
    out = [f"A9 replay - tenant {tenant_id}: {len(items)} proposed rules"]
    for r in items:
        out.append(
            f"  {r['rule_key']:36s}{r['status']:10s} {r['n_denials']:4d} of {r['n_adjudicated']:4d} denied "
            f"({Decimal(r['rate']):.0%}), recall {Decimal(r['recall']):.0%}, A5 had flagged {r['flagged_by_a5']}, "
            f"{r['dollars']} denied"
        )
    return "\n".join(out)
