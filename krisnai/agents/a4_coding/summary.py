"""A4 results: audit variance (billed level vs documented level), over and under, by provider and by code."""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.agents.a4_coding import rules
from krisnai.agents.a4_coding.agent import AGENT_ID
from krisnai.model import tenant_session


def variance(engine: Engine, tenant_id: int) -> dict:
    """Audit variance over the levelled E/M lines a coder-style check could judge (signed, baseline documented)."""
    judged = 0
    kinds: dict[str, dict] = defaultdict(lambda: {"lines": 0, "dollars": Decimal(0)})
    by_provider: dict[str, dict] = defaultdict(lambda: {"over": 0, "under": 0})
    by_code: dict[str, dict] = defaultdict(lambda: {"over": 0, "under": 0})
    with tenant_session(engine, tenant_id) as s:
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            p = json.loads(rec.action_payload)
            judged += p.get("lines_judged", 0)
            for f in p.get("findings", []):
                side = "over" if f["kind"] == rules.UNSUPPORTED else "under"
                kinds[f["kind"]]["lines"] += 1
                kinds[f["kind"]]["dollars"] += Decimal(f["difference"] or "0")
                by_provider[f["provider"] or "unknown"][side] += 1
                by_code[f["billed"]][side] += 1
    flagged = sum(v["lines"] for v in kinds.values())
    return {
        "tenant_id": tenant_id, "lines_judged": judged, "lines_flagged": flagged,
        "variance_rate": (flagged / judged) if judged else None, "by_kind": dict(kinds),
        "by_provider": dict(by_provider), "by_code": dict(by_code),
    }  # fmt: skip


def format_variance(v: dict) -> str:
    rate = "n/a" if v["variance_rate"] is None else f"{v['variance_rate']:.1%}"
    out = [
        f"A4 audit variance - tenant {v['tenant_id']}: {v['lines_flagged']} of {v['lines_judged']} judged E/M lines "
        f"differ from the documented level ({rate}). Suggestions only; a coder decides."
    ]
    out += [f"  {k:24s}{x['lines']:6d} lines {x['dollars']:>12}" for k, x in sorted(v["by_kind"].items())]
    for p, x in sorted(v["by_provider"].items()):
        out.append(f"  provider {p:12s} over {x['over']:4d} under {x['under']:4d}")
    return "\n".join(out)
