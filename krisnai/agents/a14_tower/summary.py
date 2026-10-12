"""Summary of A14 decision records after a replay: how many days were checked and which signals fired."""

from __future__ import annotations

import json
from collections import Counter

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.agents.a14_tower.agent import AGENT_ID
from krisnai.engine import NO_ACTION
from krisnai.model import tenant_session


def summarize(engine: Engine, tenant_id: int) -> dict:
    by_action: Counter = Counter()
    by_signal: Counter = Counter()
    executed = 0
    with tenant_session(engine, tenant_id) as s:
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == AGENT_ID)):
            by_action[rec.action_type] += 1
            executed += 1 if rec.outcome == "executed" else 0
            if rec.action_type != NO_ACTION:
                for sig in json.loads(rec.action_payload)["signals"]:
                    by_signal[sig["signal"]] += 1
    return {"tenant_id": tenant_id, "days": sum(by_action.values()), "executed": executed,
            "by_action": dict(by_action), "by_signal": dict(by_signal)}  # fmt: skip


def format_summary(summary: dict) -> str:
    out = [
        f"A14 replay - tenant {summary['tenant_id']}: {summary['days']} days checked, "
        f"{summary['executed']} executed"
    ]
    out += [f"  {action:24s}{n:6d}" for action, n in sorted(summary["by_action"].items())]
    out += [f"  signal {name:20s}{n:6d} days" for name, n in sorted(summary["by_signal"].items())]
    return "\n".join(out)
