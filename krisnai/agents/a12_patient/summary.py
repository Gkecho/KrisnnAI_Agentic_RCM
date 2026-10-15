"""A12 results: open patient balances by item and aging stage, collections rate and days in patient A/R."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.agents.a12_patient.agent import AGENT_ID
from krisnai.agents.a12_patient.data import load_accounts
from krisnai.engine import NO_ACTION
from krisnai.model import tenant_session


def latest(engine: Engine, tenant_id: int) -> dict[str, tuple[str, dict]]:
    """claim -> (action, payload) of its latest decision."""
    out: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            at = known[rec.event_id]
            if p["claim"] not in out or at >= out[p["claim"]][0]:
                out[p["claim"]] = (at, rec.action_type, p)
    return {k: (a, p) for k, (_, a, p) in out.items()}


def collections(engine: Engine, tenant_id: int, as_of: date) -> dict:
    """Patient share confirmed and collected by `as_of`, and the average age of what is still open."""
    owed = paid = Decimal(0)
    open_ages: list[tuple[Decimal, int]] = []
    with tenant_session(engine, tenant_id) as s:
        for a in load_accounts(s).values():
            if a.confirmed_on > as_of or a.owed <= 0:
                continue
            got = sum((p.amount for p in a.payments if p.paid_on <= as_of), Decimal(0))
            owed += a.owed
            paid += min(got, a.owed)
            if got < a.owed:
                open_ages.append((a.owed - got, (as_of - a.confirmed_on).days))
    open_total = sum((amt for amt, _ in open_ages), Decimal(0))
    weighted = sum((amt * age for amt, age in open_ages), Decimal(0))
    return {"owed": owed, "collected": paid, "open": open_total,
            "collection_rate": (paid / owed) if owed else None,
            "average_open_age_days": float(weighted / open_total) if open_total else None}  # fmt: skip


def summarize(engine: Engine, tenant_id: int, as_of: date | None = None) -> dict:
    final = latest(engine, tenant_id)
    by_kind: dict[str, dict] = defaultdict(lambda: {"count": 0, "amount": Decimal(0)})
    by_stage: dict[str, Decimal] = defaultdict(Decimal)
    executed = 0
    for action, p in final.values():
        if action == NO_ACTION:
            continue
        by_kind[p["kind"]]["count"] += 1
        by_kind[p["kind"]]["amount"] += Decimal(p["amount"])
        if p["kind"] == "balance_aging":
            by_stage[str(p["stage"])] += Decimal(p["amount"])
    out = {"tenant_id": tenant_id, "by_kind": dict(by_kind), "by_stage": dict(by_stage), "executed": executed}
    if as_of is not None:
        out["collections"] = collections(engine, tenant_id, as_of)
    return out


def format_summary(s: dict) -> str:
    out = [f"A12 replay - tenant {s['tenant_id']} (staff-facing worklist; nothing is sent to patients)"]
    out += [f"  {k:20s}{v['count']:6d} accounts {v['amount']:>12}" for k, v in sorted(s["by_kind"].items())]
    out += [f"  aging stage {st:>3s} days {amt:>12}" for st, amt in sorted(s["by_stage"].items())]
    c = s.get("collections")
    if c:
        rate = "n/a" if c["collection_rate"] is None else f"{c['collection_rate']:.1%}"
        age = "n/a" if c["average_open_age_days"] is None else f"{c['average_open_age_days']:.0f}"
        out.append(f"patient share {c['owed']}, collected {c['collected']} ({rate}); open {c['open']}, "
                   f"average age {age} days")  # fmt: skip
    return "\n".join(out)
