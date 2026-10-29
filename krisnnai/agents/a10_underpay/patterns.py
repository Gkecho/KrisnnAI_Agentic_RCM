"""Payer-wide patterns in short payments: one dispute per pattern instead of one per claim.

Read-only view over A10's decision records, plus a count of all paid lines for the same payer and CPT so a pattern can
say how much of that payer's business it touches. A gap that is the same percentage of the contract on every line
looks like a rate change or a stale fee-schedule row.
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.agents.a10_underpay import config
from krisnnai.agents.a10_underpay.agent import AGENT_ID
from krisnnai.agents.a15_lite.expected import FEE, money
from krisnnai.model import tenant_session

PCT = Decimal("0.0001")


def _bucket(pct: Decimal) -> int:
    return int((pct / config.BUCKET_WIDTH).quantize(Decimal(1)))


def patterns(engine: Engine, tenant_id: int) -> list[dict]:
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    with tenant_session(engine, tenant_id) as s:
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            for ln in p.get("lines", []):
                if ln["basis"] != FEE:
                    continue
                row = {**ln, "claim": p["claim"], "paid_on": p["payment_date"]}
                groups[(p["payer"], ln["cpt"], ln["cause"])].append(row)
        paid_lines = {
            (code, cpt): n
            for code, cpt, n in s.execute(
                select(m.Payer.payer_id_code, m.RemitLine.cpt, func.count())
                .join(m.Remit, m.Remit.id == m.RemitLine.remit_id)
                .join(m.Payment, m.Payment.id == m.Remit.payment_id)
                .join(m.Payer, m.Payer.id == m.Payment.payer_id)
                .where(m.RemitLine.paid > 0)
                .group_by(m.Payer.payer_id_code, m.RemitLine.cpt)
            )
        }
    out = []
    for (payer, cpt, cause), rows in groups.items():
        if len(rows) < config.MIN_PATTERN_LINES:
            continue
        usable = [(r, Decimal(r["gap"]) / Decimal(r["allowed"])) for r in rows if Decimal(r["allowed"]) > 0]
        # the commonest gap % (to the nearest point) and its neighbours: one-off short payments on the same code
        # are not part of the pattern, so a payer-wide rate change is not hidden by them
        buckets: dict[int, int] = defaultdict(int)
        for _, pct in usable:
            buckets[_bucket(pct)] += 1
        centre = max(sorted(buckets), key=lambda b: (buckets[b] + buckets.get(b - 1, 0) + buckets.get(b + 1, 0), -b))
        inside = [(r, pct) for r, pct in usable if abs(_bucket(pct) - centre) <= 1]
        if len(inside) < config.MIN_PATTERN_LINES or Decimal(len(inside)) / len(usable) < config.DOMINANT_SHARE:
            continue
        total_lines = paid_lines.get((payer, cpt), len(rows))
        pcts = [pct for _, pct in inside]
        out.append({
            "payer": payer, "cpt": cpt, "cause": cause, "lines": len(inside),
            "claims": len({r["claim"] for r, _ in inside}), "other_short_lines": len(usable) - len(inside),
            "total_gap": str(money(sum((Decimal(r["gap"]) for r, _ in inside), Decimal(0)))),
            "median_gap_pct": str(Decimal(median(pcts)).quantize(PCT)),
            "first_paid": min(r["paid_on"] for r, _ in inside), "last_paid": max(r["paid_on"] for r, _ in inside),
            "paid_lines_for_code": total_lines,
            "share_of_paid_lines": str((Decimal(len(inside)) / Decimal(total_lines)).quantize(PCT)),
        })  # fmt: skip
    out.sort(key=lambda r: (-Decimal(r["total_gap"]), r["payer"], r["cpt"]))
    return out


def format_patterns(items: list[dict], tenant_id: int) -> str:
    out = [f"A10 patterns - tenant {tenant_id}: {len(items)} payer-wide patterns (one dispute each)"]
    if items:
        head = f"{'payer':14s}{'cpt':7s}{'cause':18s}{'lines':>6s}{'claims':>7s}{'total':>10s}"
        out.append(head + f"{'gap%':>8s}{'of paid':>9s}  likely")
    for r in items:
        likely = "rate change or stale fee row"
        if r["other_short_lines"]:
            likely += f" (+{r['other_short_lines']} one-offs)"
        out.append(
            f"{r['payer']:14s}{r['cpt']:7s}{r['cause']:18s}{r['lines']:6d}{r['claims']:7d}{r['total_gap']:>10s}"
            f"{Decimal(r['median_gap_pct']) * 100:7.1f}%{Decimal(r['share_of_paid_lines']) * 100:8.0f}%  {likely}"
        )
    return "\n".join(out)
