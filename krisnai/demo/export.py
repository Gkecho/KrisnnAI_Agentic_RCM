"""The same run as `report.html`, as JSON a front end can load (the static site pattern: `window.KRISNAI_LIVE = {...}`).

Schema (`schema` = 1). Money is a string with two decimals; dates are ISO strings; nothing here is raw patient data.

    meta      as_of, shadow (always true), run {status, gate, files_loaded, events_added}, planted {...}
    queue     open work items, highest priority first, the top QUEUE_PER_KEY of each (owner, agent): agent, owner,
              title, value, deadline, overdue, raised_on, why[],
              next_steps[], evidence[]; and for the worklist screens: action_type, claim (id, or appointment / visit /
              payment / slice for other agents), payer, billed (claim-type cards only, else null), queue_type (Denial,
              Rejection, No response, Underpaid, Filing risk, or null), confidence (0-1 or null), filing_days_left
    queue_totals  per "owner|agent": open (true count of open items) and value (their expected dollars);
              `queue` is capped per (owner, agent)
    staff         SYNTHETIC staff and task logs with the manager analytics built on them (see krisnai/demo/staff.py):
              employees, metrics, benchmark, gaps (with training), strengths, allocation of the real open queue,
              unallocated, improvements, planted answer key and found_vs_planted
    queue_stats   per "owner|agent": open, value, by_cause[{key, open, value}], by_payer[...] (top 8), age{bucket: n},
              due{overdue, next_30, later}: the real figures behind each role's scorecard
    reference     the tables the agents read (no patient data): carc_routes, rejection_routes, ncci_pairs, mue_limits,
              fee_schedule, auth_requirements, filing_windows, appeal_windows, policy: each role's Setup screen
    agents    one per A1..A15: id, name, blurb, decisions, proposed, no_action, actions[{action, count, dollars}],
              planted[{defect, count}], examples[{title, owner, value, deadline, why[], next_steps[]}]
    baseline  A15-lite: findings, recoverable, structural (detected, not recovered)
    slices    A15 investigator: payer or payer|CPT slices below baseline with dollars and top cause
    replay    the history-replay view, from A15-lite: health {claims, clean_claim_rate, days_in_ar, ar_over_90_share},
              reconciliation[{name, description, items, mismatches, max_difference, passed}], found_vs_planted[{type,
              planted, found, precision, recall, correct_recall}] (only when the answer key exists), by_payer[{key,
              findings, recoverable, structural}], opportunities[first 25 findings]
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

from krisnai.demo.report import AGENTS, _planted, _records
from krisnai.demo.staff import build_staff
from krisnai.engine import NO_ACTION

SCHEMA = 1
QUEUE_PER_KEY = 40  # per (owner, agent): the top items; `queue_totals` carries the true count and dollars


def _m(v) -> str:
    return f"{Decimal(str(v)):.2f}"


def _cause(c: dict) -> str:
    """A short label for why the item is open, taken from the card (for the per-role scorecards)."""
    t, a = c["title"], c["agent"]
    if a == "a8_denial":
        return t.split(":")[0]
    if a in ("a3_documentation", "a11_cash", "a13_credentialing") and "," in t:
        return t.rsplit(", ", 1)[-1]
    if a == "a5_prevention":
        return t.rsplit(": ", 1)[-1]
    if a == "a4_coding":
        m = re.search(r", ([\w-]+ signal)", t)
        return m.group(1) if m else c["action_type"]
    if a == "a6_submission":
        m = re.search(r"\((.*?)\)", t)
        return m.group(1) if m else c["action_type"]
    return c["action_type"]


def _queue_stats(cards: list[dict], payers: list[str], as_of: date) -> dict:
    """Per "owner|agent": the real totals behind the per-role scorecards (the queue itself is capped)."""
    from datetime import timedelta

    out: dict[str, dict] = {}
    for c in cards:
        k = out.setdefault(f"{c['owner']}|{c['agent']}", {
            "open": 0, "value": Decimal(0), "cause": defaultdict(lambda: [0, Decimal(0)]),
            "payer": defaultdict(lambda: [0, Decimal(0)]), "age": Counter(), "due": Counter(),
        })  # fmt: skip
        v = c["expected_value"]
        k["open"] += 1
        k["value"] += v
        payer = c["payer"] or next((p for p in payers if p in c["title"]), "")
        for group, key in (("cause", _cause(c)), ("payer", payer)):
            if key:
                k[group][key][0] += 1
                k[group][key][1] += v
        k["age"][c["age_bucket"]] += 1
        due = date.fromisoformat(c["deadline"])
        k["due"]["overdue" if due < as_of else "next_30" if due <= as_of + timedelta(days=30) else "later"] += 1

    def ranked(d: dict) -> list[dict]:
        return [{"key": x, "open": n, "value": _m(v)} for x, (n, v) in sorted(d.items(), key=lambda i: -i[1][1])]

    return {
        key: {"open": k["open"], "value": _m(k["value"]), "by_cause": ranked(k["cause"]),
              "by_payer": ranked(k["payer"])[:8], "age": dict(k["age"]), "due": dict(k["due"])}
        for key, k in out.items()
    }  # fmt: skip


def _reference(engine: Engine, tenant_id: int) -> dict:
    """The reference tables the agents read (no patient data), for each role's Setup screen."""
    sql = {
        "carc_routes": "select carc_code as carc, category, owner, disposition, description from carc_route"
                       " where tenant_id=:t order by carc_code",
        "rejection_routes": "select source, status_category, status_code, category, kind, owner, description"
                            " from rejection_route where tenant_id=:t order by source, status_category",
        "ncci_pairs": "select cpt_a, cpt_b, modifier_indicator from ncci_pair where tenant_id=:t order by cpt_a, cpt_b",
        "mue_limits": "select cpt, max_units from mue_limit where tenant_id=:t order by cpt",
        "fee_schedule": "select p.name as payer, f.cpt, f.modifier, f.allowed_amount as allowed,"
                        " f.effective_date as effective, f.end_date as ends from fee_schedule f join payer p"
                        " on p.id=f.payer_id and p.tenant_id=f.tenant_id where f.tenant_id=:t order by p.name, f.cpt",
        "auth_requirements": "select p.name as payer, a.cpt, a.validity_days from auth_requirement a join payer p"
                             " on p.id=a.payer_id and p.tenant_id=a.tenant_id where a.tenant_id=:t"
                             " order by p.name, a.cpt",
        "filing_windows": "select p.name as payer, w.filing_days as days from payer_filing_window w join payer p"
                          " on p.id=w.payer_id and p.tenant_id=w.tenant_id where w.tenant_id=:t order by p.name",
        "appeal_windows": "select p.name as payer, w.appeal_days as days from payer_appeal_window w join payer p"
                          " on p.id=w.payer_id and p.tenant_id=w.tenant_id where w.tenant_id=:t order by p.name",
        "policy": "select action_type, allowed, autonomy_level as level, mode, max_amount, approver_role from policy"
                  " where tenant_id=:t order by action_type",
    }  # fmt: skip
    with engine.connect() as conn:
        out = {k: [{c: (_m(v) if isinstance(v, Decimal) else v) for c, v in r._mapping.items()}
                   for r in conn.execute(text(q), {"t": tenant_id})] for k, q in sql.items()}  # fmt: skip
    return out


def _replay(engine: Engine, tenant_id: int, out_dir: Path, as_of: date) -> dict:
    """The A15-lite run behind the history-replay screen. Empty when A15-lite has not run for this folder."""
    f = out_dir / "a15" / "a15_lite.json"
    if not f.exists():
        return {}
    d = json.loads(f.read_text(encoding="utf-8"))
    k = d.get("kpis", {})
    first = lambda name, key: (k.get(name) or [{}])[0].get(key)  # noqa: E731
    out = {
        "health": {
            "claims": first("clean_claim_rate", "submitted_claims"),
            "clean_claim_rate": first("clean_claim_rate", "clean_claim_rate"),
            "days_in_ar": first("days_in_ar", "days_in_ar"),
            "ar_over_90_share": first("ar_over_90", "ar_over_90_share"),
        },
        "reconciliation": d.get("reconciliation", {}).get("checks", []),
        "by_payer": d.get("by_payer", [])[:10],
        "opportunities": d.get("opportunities", [])[:25],
    }
    gt = out_dir / "truth" / "ground_truth.csv"
    if gt.exists():
        from krisnai.agents.a15_lite import run_a15

        res = run_a15(engine, tenant_id, as_of, out_dir / "a15", ground_truth=gt)
        out["found_vs_planted"] = [
            {"type": t, "planted": s.planted, "found": s.found, "precision": s.precision, "recall": s.recall,
             "correct_recall": s.correct_recall} for t, s in (res.scores or {}).items()
        ]  # fmt: skip
    return out


def build_payload(engine: Engine, tenant_id: int, out_dir: Path, as_of: date, planted: dict | None = None,
                  run=None, baseline: dict | None = None) -> dict:  # fmt: skip
    from krisnai.agents.a14_tower import open_cards
    from krisnai.agents.a15_investigator import summarize

    truth_dir = out_dir / "truth"
    recs = _records(engine, tenant_id)
    cards = open_cards(engine, tenant_id, as_of)
    taken: Counter = Counter()
    shown = []
    totals: dict[str, list] = defaultdict(lambda: [0, Decimal(0)])
    for c in cards:  # cards are in priority order; keep the top items of each (owner, agent) so every role has a queue
        key = f"{c['owner']}|{c['agent']}"
        totals[key][0] += 1
        totals[key][1] += c["expected_value"]
        if taken[key] < QUEUE_PER_KEY:
            taken[key] += 1
            shown.append(c)
    payers = [r[0] for r in engine.connect().execute(text("select payer_id_code from payer where tenant_id=:t"),
                                                       {"t": tenant_id})]  # fmt: skip
    stats = _queue_stats(cards, payers, as_of)
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
        for c in shown
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
        "queue_totals": {o: {"open": n, "value": _m(v)} for o, (n, v) in sorted(totals.items())},
        "queue_stats": stats,
        "staff": build_staff(cards, as_of, _cause),
        "reference": _reference(engine, tenant_id),
        "agents": agents,
        "baseline": baseline or {},
        "replay": _replay(engine, tenant_id, out_dir, as_of),
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
