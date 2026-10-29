"""A11 results: open gaps, unapplied cash, reconciliation variance, and the days-to-deposit / days-to-post KPIs."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a11_cash import rules
from krisnnai.agents.a11_cash.agent import AGENT_ID
from krisnnai.agents.a11_cash.ledger import Ledger
from krisnnai.engine import NO_ACTION
from krisnnai.model import tenant_session


def latest(engine: Engine, tenant_id: int) -> dict[str, tuple[str, dict]]:
    """key (payment trace or deposit ref) -> (action, payload) of its latest decision."""
    out: dict[str, tuple] = {}
    with tenant_session(engine, tenant_id) as s:
        known = {e.id: e.known_at for e in s.scalars(select(m.Event))}
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            key = p.get("trace") or p.get("deposit_ref")
            at = known[rec.event_id]
            if key not in out or at >= out[key][0]:
                out[key] = (at, rec.action_type, p)
    return {k: (a, p) for k, (_, a, p) in out.items()}


def kpis(engine: Engine, tenant_id: int, as_of: date) -> dict:
    """Days from payment to first deposit and to posting, from the ledger, as of a date."""
    deposit_days, post_days, late_dep, late_post = [], [], [], []
    with tenant_session(engine, tenant_id) as s:
        ledger = Ledger(s)
        for v in ledger.payments:
            p = v.payment
            if p.amount <= 0 or p.paid_on > as_of:
                continue
            matched = rules.match_deposits(p, ledger.candidates(p), as_of, ledger.rivals(p))
            if matched:
                lag = (min(d.deposited_on for d in matched) - p.paid_on).days
                deposit_days.append(lag)
                if lag > rules.config.DEPOSIT_LATE_DAYS:
                    late_dep.append(p.trace)
            by_claim: dict[str, date] = {}
            for post in ledger.postings_for(p):
                if post.posted_on <= as_of and (post.claim not in by_claim or post.posted_on < by_claim[post.claim]):
                    by_claim[post.claim] = post.posted_on
            for claim, when in by_claim.items():
                lag = (when - p.paid_on).days
                post_days.append(lag)
                if lag > rules.config.POST_LATE_DAYS:
                    late_post.append(f"{p.trace}|{claim}")

    def stats(values):
        return {"n": len(values), "mean": round(mean(values), 2) if values else None,
                "median": median(values) if values else None}  # fmt: skip

    return {"days_to_deposit": stats(deposit_days), "days_to_post": stats(post_days),
            "late_deposits": sorted(late_dep), "late_postings": sorted(late_post)}  # fmt: skip


def summarize(engine: Engine, tenant_id: int, as_of: date | None = None) -> dict:
    final = latest(engine, tenant_id)
    by_action: dict[str, int] = defaultdict(int)
    by_gap: dict[str, dict] = defaultdict(lambda: {"count": 0, "amount": Decimal(0)})
    for action, p in final.values():
        by_action[action] += 1
        for g in p.get("gaps", []):
            by_gap[g["kind"]]["count"] += 1
            by_gap[g["kind"]]["amount"] += abs(Decimal(g["amount"]))
        if p.get("kind") == "deposit" and action != NO_ACTION:
            by_gap["unidentified_deposit"]["count"] += 1
            by_gap["unidentified_deposit"]["amount"] += Decimal(p["amount"])
    def total(kinds):
        return sum((by_gap[k]["amount"] for k in kinds if k in by_gap), Decimal(0))

    out = {
        "tenant_id": tenant_id, "by_action": dict(by_action), "by_gap": dict(by_gap),
        "unapplied_cash": total((rules.NOT_POSTED, rules.PARTIAL_POSTING)),
        "variance": total((rules.DEPOSIT_VARIANCE, rules.DUPLICATE_DEPOSIT, rules.DEPOSIT_MISSING)),
    }  # fmt: skip
    if as_of is not None:
        out["kpis"] = kpis(engine, tenant_id, as_of)
    return out


def format_summary(s: dict) -> str:
    out = [
        f"A11 replay - tenant {s['tenant_id']}: unapplied cash {s['unapplied_cash']}, "
        f"reconciliation variance {s['variance']}"
    ]
    out += [f"  action {a:36s}{n:6d}" for a, n in sorted(s["by_action"].items())]
    out += [f"  gap    {g:36s}{v['count']:6d} {v['amount']:>12}" for g, v in sorted(s["by_gap"].items())]
    k = s.get("kpis")
    if k:
        out.append(
            f"days to deposit: mean {k['days_to_deposit']['mean']}, median {k['days_to_deposit']['median']}, "
            f"{len(k['late_deposits'])} late; days to post: mean {k['days_to_post']['mean']}, "
            f"median {k['days_to_post']['median']}, {len(k['late_postings'])} late"
        )
    return "\n".join(out)
