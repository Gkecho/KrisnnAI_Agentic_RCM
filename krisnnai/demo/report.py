"""One self-contained HTML page for the demo run: the work queue, one section per agent, planted vs found.

Built from the database and the answer-key CSVs only (decision records, open cards, the A15-lite scorer). No external
assets, no timestamps: the same database renders to the same bytes.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from html import escape
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.engine import NO_ACTION
from krisnnai.model import tenant_session

# (short id, name, what it does, agent_id, answer key file(s) and the column that names the planted defect)
AGENTS = [
    (
        'A1', 'Pre-visit financial clearance',
        'Checks coverage, other-payer and eligibility 72 h and 24 h before a visit.',
        'a1_clearance', [('elig_truth.csv', 'defect')],
    ),
    (
        'A2', 'Authorization intelligence',
        'Finds visits that need an authorization that is missing, expired, pending or used up.',
        'a2_authorization', [('auth_truth.csv', 'defect')],
    ),
    (
        'A3', 'Documentation completeness',
        'Finds visits with a missing or unsigned note, missing elements, late or missing charges.',
        'a3_documentation', [('doc_truth.csv', 'defect')],
    ),
    (
        'A4', 'Coding audit (suggestions only)',
        'Compares the billed E/M level with the level the note supports; a coder decides.',
        'a4_coding', [('coding_truth.csv', 'defect')],
    ),
    (
        'A5', 'Claim prevention',
        'Scores each claim before the payer sees it: duplicates, bundling, unit limits, filing deadline.',
        'a5_prevention', [],
    ),
    (
        'A6', 'Submission and response',
        'Turns rejections (999/277CA) into a correction task with a deadline.',
        'a6_submission', [('ground_truth.csv', 'issue_type', {'rejection'})],
    ),
    (
        'A7', 'AR next-best-action',
        'Ranks open claims by what to do next and when.',
        'a7_ar', [],
    ),
    (
        'A8', 'Denial resolution and appeal',
        'Routes each denial to an owner and drafts the appeal package with a deadline.',
        'a8_denial', [('ground_truth.csv', 'issue_type', {'denial', 'timely_filing'})],
    ),
    (
        'A9', 'Denial prevention learning',
        'Finds payer + CPT + reason denial patterns and proposes a rule; a named person approves.',
        'a9_learning', [('pattern_truth.csv', None)],
    ),
    (
        'A10', 'Contract and underpayment',
        'Compares each payment with the contract and finds payer-wide short-pay patterns.',
        'a10_underpay', [('ground_truth.csv', 'issue_type', {'underpayment'})],
    ),
    (
        'A11', 'Payment posting and reconciliation',
        'Finds missing, short, duplicate or unposted deposits and payments.',
        'a11_cash', [('cash_truth.csv', 'defect')],
    ),
    (
        'A12', 'Patient financial engagement (staff-facing)',
        'Worklist of patient balances with a plain-language explanation; sends nothing.',
        'a12_patient', [('patient_truth.csv', 'defect')],
    ),
    (
        'A13', 'Credentialing and enrollment',
        'Finds provider enrollments that are missing, pending too long, expiring or excluded.',
        'a13_credentialing', [('credentialing_truth.csv', 'defect')],
    ),
    (
        'A14', 'Control tower',
        'One queue across agents: backlog, deadlines, cash forecast and signals.',
        'a14_tower', [],
    ),
    (
        'A15', 'Revenue assurance investigator',
        'Watches realisation against contract by payer and CPT and explains each drop.',
        'a15_investigator', [],
    ),
]
CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#ddd;--card:#f6f7f9;--acc:#0b5cab;--warn:#8a5a00;--warnbg:#fff7e0}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--fg:#e8e8e8;--mut:#9aa;--line:#333;--card:#1d2026;--acc:#6fb1ff;
--warn:#f0c36b;--warnbg:#2a2412}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
h1{font-size:1.6rem;margin:.2em 0}h2{font-size:1.2rem;margin:1.6em 0 .4em;border-bottom:1px solid var(--line)}
h3{font-size:1rem;margin:1em 0 .3em}table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{border-bottom:1px solid var(--line);padding:4px 8px;text-align:left;vertical-align:top}th{color:var(--mut)}
td.n{text-align:right;font-variant-numeric:tabular-nums}
.banner{background:var(--warnbg);color:var(--warn);padding:8px 12px;
border-radius:6px;margin:10px 0}.card{background:var(--card);padding:8px 12px;border-radius:6px;margin:6px 0}
.mut{color:var(--mut)}
.pill{display:inline-block;padding:0 8px;border-radius:10px;background:var(--card);margin-right:4px}
nav a{margin-right:10px;color:var(--acc);text-decoration:none}pre{background:var(--card);padding:8px;overflow:auto}
@media (max-width:600px){table{font-size:.8rem}}
"""


def _money(v) -> str:
    return f"{Decimal(str(v)):,.2f}"


def _table(head: list[str], rows: list[list], numeric: set[int] = frozenset()) -> str:
    if not rows:
        return '<p class="mut">none</p>'
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    body = "".join(
        "<tr>" + "".join(
            f'<td class="n">{escape(str(c))}</td>' if i in numeric else f"<td>{escape(str(c))}</td>"
            for i, c in enumerate(r)
        ) + "</tr>"
        for r in rows
    )
    return f"<table><tr>{th}</tr>{body}</table>"


def _planted(truth_dir: Path, spec: tuple) -> Counter:
    name, column, *only = spec
    path = truth_dir / name
    out: Counter = Counter()
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            label = r.get(column) if column else "pattern claim"
            if only and label not in only[0]:
                continue
            out[label or "(blank)"] += 1
    return out


def _records(engine: Engine, tenant_id: int) -> dict[str, list[tuple[str, Decimal, dict]]]:
    out: dict[str, list] = defaultdict(list)
    with tenant_session(engine, tenant_id) as s:
        for rec in s.scalars(select(m.DecisionRecord).order_by(m.DecisionRecord.id)):
            out[rec.agent_id].append((rec.action_type, rec.materiality_amount, json.loads(rec.action_payload)))
    return out


def _agent_section(
    short: str, name: str, blurb: str, agent_id: str, truths: list, recs: list, truth_dir: Path
) -> str:
    acted = [r for r in recs if r[0] != NO_ACTION]
    by_action: dict[str, list] = defaultdict(lambda: [0, Decimal(0)])
    for action, amount, _ in recs:
        by_action[action][0] += 1
        by_action[action][1] += amount if action != NO_ACTION else Decimal(0)
    rows = [[a, n, _money(v)] for a, (n, v) in sorted(by_action.items(), key=lambda kv: (kv[0] == NO_ACTION, kv[0]))]
    out = [f'<h2 id="{short.lower()}">{short} - {escape(name)}</h2><p>{escape(blurb)}</p>']
    out.append(f'<p class="mut">{len(recs)} decisions, {len(acted)} proposed something, '
               f"{len(recs) - len(acted)} found nothing to do.</p>")  # fmt: skip
    out.append(_table(["action", "decisions", "dollars at stake"], rows, {1, 2}))
    for spec in truths:
        planted = _planted(truth_dir, spec)
        if planted:
            what = "planted in the data (answer key " + spec[0] + ")"
            out.append(f"<h3>{what}</h3>" + _table(["defect", "planted"], sorted(planted.items()), {1}))
    cards = [p for _, _, p in acted if isinstance(p.get("card"), dict)]
    cards.sort(key=lambda p: (-Decimal(p["card"]["priority"]), p["card"]["title"]))
    seen: set[str] = set()
    distinct = [p for p in cards if not (p["card"]["title"] in seen or seen.add(p["card"]["title"]))]
    for p in distinct[:3]:
        c = p["card"]
        why = "".join(f"<li>{escape(w)}</li>" for w in c["why"])
        nxt = "".join(f"<li>{escape(n)}</li>" for n in c["next_steps"])
        out.append(
            f'<div class="card"><b>{escape(c["title"])}</b><br>'
            f'<span class="pill">owner: {escape(c["owner"])}</span>'
            f'<span class="pill">value {_money(c["expected_value"])}'
            f'</span><span class="pill">due {escape(c["deadline"])}</span>'
            f"<ul>{why}</ul><div class=\"mut\">Next steps</div><ul>{nxt}</ul></div>"
        )
    return "\n".join(out)


def _queue(engine: Engine, tenant_id: int, as_of: date, go_live: date | None) -> str:
    from krisnnai.agents.a14_tower import open_cards

    cards = open_cards(engine, tenant_id, as_of)
    by_agent = Counter(c["agent"] for c in cards)
    total = sum((c["expected_value"] for c in cards), Decimal(0))
    head = (f"<p>{len(cards)} open items, {sum(1 for c in cards if c['overdue'])} overdue, "
            f"{_money(total)} expected value.</p>")  # fmt: skip
    mix = " ".join(f'<span class="pill">{escape(a)}: {n}</span>' for a, n in sorted(by_agent.items()))
    rows = [
        [c["priority"].quantize(Decimal("0.01")), c["agent"], c["owner"], c["title"], _money(c["expected_value"]),
         c["deadline"] + (" (overdue)" if c["overdue"] else ""),
         "new" if go_live and date.fromisoformat(c["raised_on"]) >= go_live else "history"]
        for c in cards[:40]
    ]  # fmt: skip
    cols = ["priority", "agent", "owner", "what", "value", "due", "since go-live"]
    return head + f"<p>{mix}</p>" + _table(cols, rows, {0, 4})


def _a15_lite(engine: Engine, tenant_id: int, as_of: date, out_dir: Path, truth_dir: Path) -> str:
    from krisnnai.agents.a15_lite import format_scores, run_a15

    gt = truth_dir / "ground_truth.csv"
    try:
        res = run_a15(engine, tenant_id, as_of, out_dir / "a15", ground_truth=gt if gt.exists() else None)
    except Exception as e:  # noqa: BLE001 - the page still renders; the reason is shown
        return f'<p class="mut">A15-lite baseline not produced: {escape(type(e).__name__)}: {escape(str(e))}</p>'
    s = res.report["summary"]
    parts = [
        f"<p>{s['findings']} leaks detected: recoverable {_money(s['recoverable'])}, "
        f"structural {_money(s['structural'])}. "
        "Detected, not recovered.</p>"
    ]
    if res.scores:
        parts.append("<h3>Found vs planted (A15-lite against the answer key)</h3>")
        parts.append("<pre>" + escape(format_scores(res.scores)) + "</pre>")
    return "".join(parts)


def _a15_slices(engine: Engine, tenant_id: int) -> str:
    from krisnnai.agents.a15_investigator import summarize

    s = summarize(engine, tenant_id)
    if not s["slices"]:
        return '<p class="mut">No payer or CPT slice is below its baseline at the last sweep.</p>'
    rows = [[x["slice"], _money(x["impact"]), x["top_cause"]] for x in s["slices"]]
    return _table(["slice (payer or payer|CPT)", "dollars below baseline", "largest cause"], rows, {1})


def write_report(
    engine: Engine, tenant_id: int, out_dir: Path, as_of: date, planted: dict | None = None, run=None
) -> Path:
    truth_dir = out_dir / "truth"
    recs = _records(engine, tenant_id)
    go_live = None
    if run is not None and run.cards.get("since_go_live") is not None:
        from datetime import timedelta

        go_live = as_of - timedelta(days=28)
    nav = " ".join(f'<a href="#{a[0].lower()}">{a[0]}</a>' for a in AGENTS)
    body = [
        "<h1>KrisnnAI RCM - mock practice run</h1>",
        f'<p class="mut">As of {as_of.isoformat()}. Synthetic data from Synthea with defects planted by a simulator.'
        "</p>",
        '<div class="banner"><b>Shadow mode.</b> Every agent only proposes. '
        "Nothing was submitted, sent, changed or paid.</div>",
    ]
    if run is not None:
        body.append(
            f"<p>Loaded {run.files_loaded} files, {run.events_added} events; gate {escape(run.gate)}; "
            f"all fifteen agents advanced to {as_of.isoformat()}.</p>"
        )
    if planted:
        rc, dp = planted["rate_cut"], planted["denial_pattern"]
        body.append(
            "<h3>Planted payer-wide problems</h3><ul>"
            f"<li>{escape(rc['payer'])} pays {rc['percent']}% under contract on CPT {escape(rc['cpt'])} "
            f"from {rc['from']}.</li>"
            f"<li>{escape(dp['payer'])} denies CPT {escape(dp['cpt'])} with CARC {dp['carc']} at "
            f"{int(dp['rate'] * 100)}% from {dp['from']}.</li></ul>"
        )
    body += [f"<nav>{nav}</nav>", "<h2 id=\"queue\">Work queue (control tower)</h2>"]
    body.append(_queue(engine, tenant_id, as_of, go_live))
    body += ["<h2 id=\"baseline\">Leakage baseline</h2>", _a15_lite(engine, tenant_id, as_of, out_dir, truth_dir)]
    body += ["<h3>Payer and CPT slices below baseline (A15 investigator)</h3>", _a15_slices(engine, tenant_id)]
    for short, name, blurb, agent_id, truths in AGENTS:
        body.append(_agent_section(short, name, blurb, agent_id, truths, recs.get(agent_id, []), truth_dir))
    body.append(
        '<h2 id="limits">What this does and does not show</h2><div class="banner"><ul>'
        "<li>The data is synthetic and the planted defects were written by the same team as the rules: "
        "a match shows the "
        "pipeline is wired correctly, not that it is right on a real practice.</li>"
        "<li>Thresholds, windows and level tables are placeholders for the practice's leads to set.</li>"
        "<li>It shows detections and agreement with answer keys. It does not measure staff time saved; that needs a "
        "baseline and a control group.</li></ul></div>"
    )
    html = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>KrisnnAI mock run</title>'
        f"<style>{CSS}</style></head><body><main>" + "\n".join(body) + "</main></body></html>"
    )
    path = out_dir / "report.html"
    path.write_text(html, encoding="utf-8", newline="\n")
    return path
