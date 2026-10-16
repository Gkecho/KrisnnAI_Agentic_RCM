"""The same run as `report.html`, as JSON a front end can load (the static site pattern: `window.KRISNAI_LIVE = {...}`).

Schema (`schema` = 1). Money is a string with two decimals; dates are ISO strings; nothing here is raw patient data.

    meta      as_of, shadow (always true), run {status, gate, files_loaded, events_added}, planted {...}
    queue     open work items, highest priority first: agent, owner, title, value, deadline, overdue, raised_on, why[],
              next_steps[], evidence[]; and for the worklist screens: action_type, claim (id, or appointment / visit /
              payment / slice for other agents), payer, billed (claim-type cards only, else null), queue_type (Denial,
              Rejection, No response, Underpaid, Filing risk, or null), confidence (0-1 or null), filing_days_left
    agents    one per A1..A15: id, name, blurb, decisions, proposed, no_action, actions[{action, count, dollars}],
              planted[{defect, count}], examples[{title, owner, value, deadline, why[], next_steps[]}]
    baseline  A15-lite: findings, recoverable, structural (detected, not recovered)
    slices    A15 investigator: payer or payer|CPT slices below baseline with dollars and top cause
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.engine import Engine

from krisnai.demo.report import AGENTS, _planted, _records
from krisnai.engine import NO_ACTION

SCHEMA = 1
QUEUE_LIMIT = 300


def _m(v) -> str:
    return f"{Decimal(str(v)):.2f}"


def build_payload(engine: Engine, tenant_id: int, out_dir: Path, as_of: date, planted: dict | None = None,
                  run=None, baseline: dict | None = None) -> dict:  # fmt: skip
    from krisnai.agents.a14_tower import open_cards
    from krisnai.agents.a15_investigator import summarize

    truth_dir = out_dir / "truth"
    recs = _records(engine, tenant_id)
    cards = open_cards(engine, tenant_id, as_of)
    queue = [
        {
            "agent": c["agent"], "owner": c["owner"], "title": c["title"], "value": _m(c["expected_value"]),
            "priority": _m(c["priority"]), "deadline": c["deadline"], "overdue": c["overdue"],
            "raised_on": c["raised_on"], "why": c["card"]["why"], "next_steps": c["card"]["next_steps"],
            "evidence": c["card"]["evidence"], "action_type": c["action_type"], "claim": c["claim"],
            "payer": c["payer"], "billed": _m(c["billed"]) if c["billed"] is not None else None,
            "queue_type": c["queue_type"], "filing_days_left": c["filing_days_left"],
            "confidence": f"{Decimal(c['confidence']):.2f}" if c["confidence"] is not None else None,
        }
        for c in cards[:QUEUE_LIMIT]
    ]
    agents = []
    for short, name, blurb, agent_id, truths in AGENTS:
        rows = recs.get(agent_id, [])
        by_action: dict[str, list] = defaultdict(lambda: [0, Decimal(0)])
        for action, amount, _ in rows:
            by_action[action][0] += 1
            by_action[action][1] += amount if action != NO_ACTION else Decimal(0)
        planted_rows: Counter = Counter()
        for spec in truths:
            planted_rows.update(_planted(truth_dir, spec))
        withcard = [p for a, _, p in rows if a != NO_ACTION and isinstance(p.get("card"), dict)]
        withcard.sort(key=lambda p: (-Decimal(p["card"]["priority"]), p["card"]["title"]))
        seen: set[str] = set()
        examples = []
        for p in withcard:
            c = p["card"]
            if c["title"] in seen:
                continue
            seen.add(c["title"])
            examples.append({"title": c["title"], "owner": c["owner"], "value": _m(c["expected_value"]),
                             "deadline": c["deadline"], "why": c["why"], "next_steps": c["next_steps"]})  # fmt: skip
            if len(examples) == 3:
                break
        agents.append({
            "id": short, "name": name, "blurb": blurb, "decisions": len(rows),
            "proposed": sum(1 for a, _, _ in rows if a != NO_ACTION),
            "no_action": sum(1 for a, _, _ in rows if a == NO_ACTION),
            "actions": [{"action": a, "count": n, "dollars": _m(v)} for a, (n, v) in sorted(by_action.items())],
            "planted": [{"defect": k, "count": v} for k, v in sorted(planted_rows.items())],
            "examples": examples,
        })  # fmt: skip
    if baseline is None:
        f = out_dir / "a15" / "a15_lite.json"
        baseline = json.loads(f.read_text(encoding="utf-8"))["summary"] if f.exists() else {}
    s = summarize(engine, tenant_id)
    return {
        "schema": SCHEMA,
        "meta": {
            "as_of": as_of.isoformat(), "shadow": True, "planted": planted or {},
            "run": {
                "status": getattr(run, "status", None), "gate": getattr(run, "gate", None),
                "files_loaded": getattr(run, "files_loaded", None), "events_added": getattr(run, "events_added", None),
            },
        },
        "queue": queue,
        "agents": agents,
        "baseline": baseline or {},
        "slices": [{"slice": x["slice"], "dollars": _m(x["impact"]), "top_cause": x["top_cause"]} for x in s["slices"]],
    }


def write_ui_data(engine: Engine, tenant_id: int, out_dir: Path, as_of: date, planted: dict | None = None,
                  run=None, baseline: dict | None = None) -> tuple[Path, Path]:  # fmt: skip
    payload = build_payload(engine, tenant_id, out_dir, as_of, planted, run, baseline)
    text = json.dumps(payload, indent=1, sort_keys=True)
    j, js = out_dir / "ui_data.json", out_dir / "ui_data.js"
    j.write_text(text + "\n", encoding="utf-8", newline="\n")
    js.write_text("window.KRISNAI_LIVE = " + text + ";\n", encoding="utf-8", newline="\n")
    return j, js
