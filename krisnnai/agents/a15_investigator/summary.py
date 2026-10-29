"""A15 results: the flagged slices as of the latest decision on each, with their top cause."""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a15_investigator.agent import AGENT_ID
from krisnnai.engine import NO_ACTION
from krisnnai.model import tenant_session


def latest(engine: Engine, tenant_id: int) -> dict[str, tuple[str, dict]]:
    """slice key -> (action, payload) of its latest decision."""
    out: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            key = p.get("slice") or p.get("key")
            at = known[rec.event_id]
            if key not in out or at >= out[key][0]:
                out[key] = (at, rec.action_type, p)
    return {k: (a, p) for k, (_, a, p) in out.items()}


def summarize(engine: Engine, tenant_id: int) -> dict:
    final = latest(engine, tenant_id)
    by_cause: dict[str, dict] = defaultdict(lambda: {"slices": 0, "amount": Decimal(0)})
    by_action: dict[str, int] = defaultdict(int)
    open_slices, impact = [], Decimal(0)
    for key, (action, p) in sorted(final.items()):
        by_action[action] += 1
        if action == NO_ACTION:
            continue
        impact += Decimal(p["impact"])
        open_slices.append({"slice": key, "impact": Decimal(p["impact"]), "top_cause": p["top_cause"]})
        for c in p["causes"]:
            by_cause[c["cause"]]["slices"] += 1
            by_cause[c["cause"]]["amount"] += Decimal(c["dollars"])
    return {"tenant_id": tenant_id, "by_action": dict(by_action), "by_cause": dict(by_cause), "impact": impact,
            "slices": sorted(open_slices, key=lambda x: (-x["impact"], x["slice"]))}  # fmt: skip


def format_summary(s: dict) -> str:
    out = [f"A15 replay - tenant {s['tenant_id']}: {len(s['slices'])} slices below baseline, {s['impact']} at stake"]
    out += [f"  action {a:30s}{n:6d}" for a, n in sorted(s["by_action"].items())]
    out += [f"  cause  {c:30s}{v['slices']:6d} {v['amount']:>12}" for c, v in sorted(s["by_cause"].items())]
    out += [f"  slice  {x['slice']:30s}{x['impact']:>12}  {x['top_cause']}" for x in s["slices"]]
    return "\n".join(out)
