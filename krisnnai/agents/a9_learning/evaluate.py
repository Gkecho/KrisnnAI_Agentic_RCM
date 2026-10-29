"""Two read-only reports on A9's work: the forward test of each rule, and attribution of denials to upstream flags.

Forward test: for claims filed after a rule was proposed, how often does "payer + CPT" really end in that CARC
(precision), and what share of the payer's denials with that CARC would it have flagged (recall). Attribution: for each
denial, which upstream agent had already flagged the problem before the claim went out (A1 coverage, A3 documentation,
A5 pre-release checks), or none. Key matching, not proof of cause.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a9_learning.clusters import outcomes
from krisnnai.agents.a15_lite.expected import money
from krisnnai.agents.a15_lite.pricing import ClaimPricer
from krisnnai.engine import NO_ACTION
from krisnnai.model import tenant_session

PCT = Decimal("0.0001")


def _price(pricer: ClaimPricer, s, day: date, payer: str, lines) -> Decimal:
    amount, _ = pricer.price(s, day, payer, lines, None, Decimal(0))
    return amount


def forward(engine: Engine, tenant_id: int, as_of: date) -> list[dict]:
    pricer = ClaimPricer()
    out = []
    with tenant_session(engine, tenant_id) as s:
        rules = list(s.scalars(select(m.LearnedRule).order_by(m.LearnedRule.id)))
        if not rules:
            return []
        payer_code = {p.id: p.payer_id_code for p in s.scalars(select(m.Payer))}
        items = [o for o in outcomes(s, as_of) if o.adjudicated]
        lines: dict[int, list] = defaultdict(list)
        for ln in s.scalars(select(m.ClaimLine)):
            lines[ln.claim_id].append(ln)
        for r in rules:
            code = payer_code.get(r.payer_id, "")
            window = [o for o in items if o.filed_on > r.proposed_on]
            flagged = [o for o in window if o.payer == code and r.cpt in o.cpts]
            hits = [o for o in flagged if r.carc in o.carcs]
            all_denied = [o for o in window if o.payer == code and r.carc in o.carcs]
            held = sum((_price(pricer, s, as_of, code, lines[o.claim_id]) for o in hits), Decimal(0))
            out.append({
                "rule_key": r.rule_key, "status": r.status, "proposed_on": r.proposed_on.isoformat(),
                "flagged": len(flagged), "hits": len(hits), "all_denials": len(all_denied),
                "precision": str((Decimal(len(hits)) / len(flagged)).quantize(PCT)) if flagged else None,
                "recall": str((Decimal(len(hits)) / len(all_denied)).quantize(PCT)) if all_denied else None,
                "dollars_held": str(money(held)),
            })  # fmt: skip
    return out


def attribution(engine: Engine, tenant_id: int, as_of: date) -> dict:
    pricer = ClaimPricer()
    with tenant_session(engine, tenant_id) as s:
        flagged: dict[str, set[str]] = {"a1": set(), "a2": set(), "a3": set(), "a5": set()}
        field = {"a1_clearance": ("a1", "appt"), "a2_authorization": ("a2", "appt"),
                 "a3_documentation": ("a3", "visit"), "a5_prevention": ("a5", "claim")}  # fmt: skip
        for agent, action, payload in s.execute(
            select(m.DecisionRecord.agent_id, m.DecisionRecord.action_type, m.DecisionRecord.action_payload)
            .where(m.DecisionRecord.agent_id.in_(field))
        ):
            if action != NO_ACTION:
                key, name = field[agent]
                flagged[key].add(json.loads(payload).get(name))
        visits: dict[tuple, list[str]] = defaultdict(list)
        for v in s.scalars(select(m.Visit)):
            visits[(v.payer_id, v.patient_ref_id, v.service_date, v.cpt)].append(v.visit_ref)
        appts: dict[tuple, list[str]] = defaultdict(list)
        for a in s.scalars(select(m.Appointment)):
            appts[(a.payer_id, a.patient_ref_id, a.appt_date, a.cpt)].append(a.appt_ref)
        claims = {c.id: c for c in s.scalars(select(m.Claim))}
        lines: dict[int, list] = defaultdict(list)
        for ln in s.scalars(select(m.ClaimLine)):
            lines[ln.claim_id].append(ln)
        payer_code = {p.id: p.payer_id_code for p in s.scalars(select(m.Payer))}
        agg: dict[str, dict] = defaultdict(lambda: {"denials": 0, "dollars": Decimal(0)})
        denied = [o for o in outcomes(s, as_of) if o.carcs]
        for o in denied:
            c = claims[o.claim_id]
            sources: set[str] = set()
            if o.sid in flagged["a5"]:
                sources.add("a5")
            for ln in lines[o.claim_id]:
                key = (c.payer_id, c.patient_ref_id, c.service_date, ln.cpt)
                if any(v in flagged["a3"] for v in visits.get(key, [])):
                    sources.add("a3")
                refs = appts.get(key, [])
                if any(a in flagged["a1"] for a in refs):
                    sources.add("a1")
                if any(a in flagged["a2"] for a in refs):
                    sources.add("a2")
            amount = _price(pricer, s, as_of, payer_code.get(c.payer_id, ""), lines[o.claim_id])
            for src in sorted(sources) or ["none"]:
                agg[src]["denials"] += 1
                agg[src]["dollars"] += amount
    return {
        "total_denials": len(denied),
        "by_source": {
            k: {"denials": v["denials"], "dollars": str(money(v["dollars"]))} for k, v in sorted(agg.items())
        },
        "note": "a denial flagged by several agents counts once under each; none = no upstream agent flagged it",
    }


def format_forward(items: list[dict]) -> str:
    out = [f"A9 forward test: {len(items)} rules"]
    for r in items:
        out.append(
            f"  {r['rule_key']:36s}{r['status']:10s} flagged {r['flagged']:4d} hits {r['hits']:4d} "
            f"precision {r['precision']} recall {r['recall']} held {r['dollars_held']}"
        )
    return "\n".join(out)


def format_attribution(a: dict) -> str:
    out = [f"A9 attribution: {a['total_denials']} denials"]
    out += [f"  {k:6s}{v['denials']:6d} denials {v['dollars']:>12}" for k, v in a["by_source"].items()]
    out.append(a["note"])
    return "\n".join(out)
