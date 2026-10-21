"""Synthetic staff activity and the manager analytics built on it (demo only).

The engine records no employee data: in shadow mode nothing is written back, so nobody "completes" a task. To show what
a billing or coding manager would see, this module invents a small team with fictional names and plants a few strengths
and weaknesses, generates 90 days of task logs, and then runs the same analysis a real task log would get:

    metrics       per employee and task type: tasks, median minutes, first-pass rate, on-time rate, trend
    gaps          clear shortfalls against the team (enough tasks and a clear margin), each with a training module
    allocation    the real open queue, split across the people who fit each task type best and have room
    improvements  findings for the manager that are not about one person
    found_vs_planted  whether the analysis found what was planted (the answer key stays in the payload for the preview)

Everything here is a suggestion to the manager. Nothing is assigned in any system, and the figures are not for hiring,
firing or pay decisions. Comparisons are always within one task type.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

SEED = 20261014
DAYS = 90
MIN_TASKS = 20  # fewer completed tasks than this: "not enough data", never a flag
QUALITY_MARGIN = 0.12  # rework rate this far above the team ...
QUALITY_RATIO = 1.5  # ... and at least this many times the team's
SLOW_RATIO = 1.4  # median minutes this many times the team's
FAST_RATIO = 0.8
BUSY = 0.9  # share of weekly capacity already assigned

# task type: (label, base minutes, rework reasons with weights)
TASKS = {
    "a6_rejection_task": ("Rejected claims", 12.0, {"missing data": 5, "invalid NPI": 3, "modifier": 2}),
    "a3_charge_review": ("Charge review", 9.0, {"charge not entered": 5, "wrong units": 3, "wrong date": 2}),
    "a7_resubmit_review": ("Resubmissions", 15.0, {"defect not fixed": 5, "wrong payer": 3, "missing attachment": 2}),
    "a7_escalate_review": ("Unpaid claim escalation", 11.0, {"wrong next step": 5, "no payer contact": 3, "late": 2}),
    "a7_status_check_task": ("Status checks", 6.0, {"status not recorded": 5, "wrong claim": 3, "late": 2}),
    "a8_appeal_task": ("Appeals", 28.0, {"weak evidence": 5, "missed deadline": 2, "wrong reason": 3}),
    "a8_fix_task": ("Denial fixes", 14.0, {"coverage/eligibility": 5, "wrong code left": 2, "resubmitted twice": 3}),
    "a8_write_off_review": (
        "Write-off reviews",
        10.0,
        {"still recoverable": 5, "missing approval": 3, "wrong category": 2},
    ),
    "a4_coding_review": ("Coding reviews", 18.0, {"under-coding": 5, "over-coding": 3, "missed modifier": 2}),
    "a5_hold_review": ("Claim holds", 10.0, {"NCCI pair": 5, "unit limit": 3, "wrong modifier": 2}),
}

# training catalogue: (task type, gap kind, rework reason or None) -> module
TRAINING = {
    ("a6_rejection_task", "quality", "modifier"): "Modifier rules for claim corrections (25, 59, XU)",
    ("a6_rejection_task", "quality", "missing data"): "Required claim data elements (277CA A3 fixes)",
    ("a6_rejection_task", "quality", "invalid NPI"): "Provider master data and NPI mapping",
    ("a6_rejection_task", "speed", None): "Reading a 277CA rejection quickly",
    ("a3_charge_review", "quality", None): "Charge capture from the clinical note",
    ("a7_resubmit_review", "quality", None): "Resubmission checklist and clearinghouse rules",
    ("a7_escalate_review", "speed", None): "Payer escalation playbook",
    ("a7_status_check_task", "speed", None): "Payer portal and 276/277 status checks",
    ("a8_appeal_task", "quality", None): "Appeal letters that quote the note",
    ("a8_appeal_task", "speed", None): "Denial triage by CARC category",
    ("a8_fix_task", "quality", "coverage/eligibility"): "Front-end fixes: coverage and authorization denials",
    ("a8_fix_task", "quality", None): "Correcting and resubmitting denied claims",
    ("a8_write_off_review", "quality", None): "Recoverability and write-off approvals",
    ("a4_coding_review", "quality", "under-coding"): "E/M leveling calibration (under- and over-coding)",
    ("a4_coding_review", "quality", None): "E/M leveling calibration (under- and over-coding)",
    ("a4_coding_review", "speed", None): "From documentation to code: a faster workflow",
    ("a5_hold_review", "quality", None): "NCCI pairs and MUE limits",
    ("a5_hold_review", "speed", None): "Clearing claim holds quickly",
}

# employee: id, name, role, weekly capacity, share of capacity already assigned elsewhere,
# and per task type (weekly volume, minutes factor, first-pass rate [, dominant rework reason])
_B = "billing"
_C = "coding"
STAFF = {
    _B: [
        (
            "B01",
            "Asha Raman",
            "Billing specialist",
            80,
            0.45,
            {
                "a6_rejection_task": (6, 0.75, 0.93),
                "a3_charge_review": (5, 1.0, 0.92),
                "a7_resubmit_review": (3, 1.0, 0.9),
            },
        ),
        (
            "B02",
            "Brian Kessler",
            "Billing specialist",
            80,
            0.55,
            {
                "a6_rejection_task": (6, 1.0, 0.64, "modifier"),
                "a3_charge_review": (5, 1.05, 0.9),
                "a7_resubmit_review": (3, 1.0, 0.88),
            },
        ),
        (
            "B03",
            "Carmen Diaz",
            "Billing specialist",
            80,
            0.35,
            {
                "a6_rejection_task": (5, 1.05, 0.9),
                "a3_charge_review": (6, 0.9, 0.95),
                "a7_resubmit_review": (3, 1.1, 0.85),
            },
        ),
        (
            "B04",
            "Dev Patel",
            "Denial specialist",
            80,
            0.6,
            {"a8_appeal_task": (4, 0.9, 0.9), "a8_fix_task": (6, 1.0, 0.9), "a8_write_off_review": (3, 1.0, 0.92)},
        ),
        (
            "B05",
            "Elena Moreau",
            "Denial specialist",
            80,
            0.5,
            {
                "a8_appeal_task": (4, 1.0, 0.91),
                "a8_fix_task": (6, 1.0, 0.68, "coverage/eligibility"),
                "a8_write_off_review": (3, 1.0, 0.9),
            },
        ),
        (
            "B06",
            "Farid Sayed",
            "Denial specialist",
            80,
            0.4,
            {"a8_appeal_task": (4, 1.9, 0.9), "a8_fix_task": (6, 0.95, 0.92), "a8_write_off_review": (3, 1.0, 0.9)},
        ),
        (
            "B07",
            "Grace Lindqvist",
            "AR specialist",
            80,
            0.7,
            {
                "a7_escalate_review": (5, 0.9, 0.93),
                "a7_status_check_task": (8, 0.6, 0.96),
                "a7_resubmit_review": (3, 1.0, 0.9),
            },
        ),
        (
            "B08",
            "Hiro Tanaka",
            "AR specialist",
            80,
            0.3,
            {
                "a7_escalate_review": (5, 1.0, 0.9),
                "a7_status_check_task": (8, 1.0, 0.9),
                "a7_resubmit_review": (3, 1.0, 0.88),
            },
        ),
    ],
    _C: [
        (
            "C01",
            "Ines Vargas",
            "Coder",
            60,
            0.5,
            {"a4_coding_review": (5, 1.0, 0.92), "a5_hold_review": (4, 1.0, 0.95), "a8_appeal_task": (3, 1.0, 0.9)},
        ),
        (
            "C02",
            "Jon Weber",
            "Coder",
            60,
            0.45,
            {"a4_coding_review": (5, 1.0, 0.93), "a5_hold_review": (4, 1.1, 0.9), "a8_appeal_task": (3, 1.0, 0.88)},
        ),
        (
            "C03",
            "Kavya Nair",
            "Coder",
            60,
            0.35,
            {
                "a4_coding_review": (5, 0.95, 0.6, "under-coding"),
                "a5_hold_review": (4, 1.0, 0.93),
                "a8_appeal_task": (3, 1.0, 0.9),
            },
        ),
        (
            "C04",
            "Liam O'Connor",
            "Coder",
            60,
            0.55,
            {"a4_coding_review": (5, 1.0, 0.9), "a5_hold_review": (4, 1.8, 0.92), "a8_appeal_task": (3, 1.0, 0.9)},
        ),
        (
            "C05",
            "Mei Chen",
            "Coder",
            60,
            0.4,
            {"a4_coding_review": (5, 1.0, 0.92), "a5_hold_review": (4, 0.65, 0.97), "a8_appeal_task": (3, 0.9, 0.93)},
        ),
        (
            "C06",
            "Noah Brooks",
            "Coder",
            60,
            0.95,
            {"a4_coding_review": (5, 1.0, 0.9), "a5_hold_review": (4, 1.0, 0.9), "a8_appeal_task": (3, 1.0, 0.9)},
        ),
    ],
}
TEAM_LABEL = {_B: "Billing team", _C: "Coding team"}
# the real open work each team can take: (task type, owners; None = any)
WORK = {
    _B: [
        ("a6_rejection_task", {"billing"}),
        ("a3_charge_review", {"biller"}),
        ("a7_resubmit_review", {"billing"}),
        ("a7_escalate_review", {"ar_lead"}),
        ("a7_status_check_task", {"billing"}),
        ("a8_appeal_task", {"billing", "front_desk"}),
        ("a8_fix_task", {"billing", "front_desk"}),
        ("a8_write_off_review", {"billing", "front_desk"}),
    ],
    _C: [
        ("a4_coding_review", {"coder"}),
        ("a5_hold_review", {"coding"}),
        ("a8_appeal_task", {"coding"}),
        ("a8_fix_task", {"coding"}),
        ("a8_write_off_review", {"coding"}),
    ],
}
PLANTED = [  # the answer key: what the generator did on purpose
    {"employee": "B02", "task_type": "a6_rejection_task", "kind": "quality", "note": "modifier errors on corrections"},
    {
        "employee": "B05",
        "task_type": "a8_fix_task",
        "kind": "quality",
        "note": "coverage and eligibility fixes come back",
    },
    {"employee": "B06", "task_type": "a8_appeal_task", "kind": "speed", "note": "appeals take about twice as long"},
    {"employee": "C03", "task_type": "a4_coding_review", "kind": "quality", "note": "under-coding in E/M leveling"},
    {"employee": "C04", "task_type": "a5_hold_review", "kind": "speed", "note": "claim holds take much longer"},
    {"employee": "B01", "task_type": "a6_rejection_task", "kind": "strength", "note": "fastest on rejections"},
    {"employee": "B07", "task_type": "a7_status_check_task", "kind": "strength", "note": "fastest on status checks"},
    {"employee": "C05", "task_type": "a5_hold_review", "kind": "strength", "note": "fastest on claim holds"},
    {"employee": "C06", "task_type": "load", "kind": "capacity", "note": "95% of weekly capacity already assigned"},
]


def _tasks(emp: tuple, rng: random.Random) -> dict[str, list[tuple[float, bool, bool, int]]]:
    """(minutes, first pass, on time, days ago) for each task type this person works."""
    out: dict[str, list] = {}
    for tt, spec in emp[5].items():
        vol, speed, q = spec[0], spec[1], spec[2]
        reason = spec[3] if len(spec) > 3 else None
        rows = []
        for _ in range(round(vol * DAYS / 7)):
            minutes = TASKS[tt][1] * speed * rng.lognormvariate(0, 0.22)
            first = rng.random() < q
            rows.append((minutes, first, rng.random() < 0.95 - 0.2 * (1 - q), rng.randrange(DAYS)))
        out[tt] = rows
        if reason:
            out[tt + "#reason"] = reason
    return out


def _metrics(logs: dict) -> dict:
    out: dict[str, dict] = {}
    for tt, rows in logs.items():
        if tt.endswith("#reason") or not rows:
            continue
        recent, older = [r[1] for r in rows if r[3] < 30], [r[1] for r in rows if r[3] >= 30]
        rate = lambda x: sum(x) / len(x) if x else None  # noqa: E731
        out[tt] = {
            "n": len(rows),
            "done_30d": len(recent),
            "median_min": round(statistics.median(r[0] for r in rows), 1),
            "first_pass": round(rate([r[1] for r in rows]), 3),
            "on_time": round(rate([r[2] for r in rows]), 3),
            "trend": round(rate(recent) - rate(older), 3) if recent and older else None,
        }
    return out


def _reasons(rng: random.Random, tt: str, rework: int, dominant: str | None) -> Counter:
    weights = dict(TASKS[tt][2])
    if dominant:
        weights = {k: (40 if k == dominant else v) for k, v in weights.items()}
    return Counter(rng.choices(list(weights), weights=list(weights.values()), k=rework))


def build_staff(cards: list[dict], as_of: date, cause=None) -> dict:
    """The `staff` section of the UI export. `cards` are the open A14 cards (real); everything about people is synthetic."""  # noqa: E501
    rng = random.Random(SEED)
    employees, metrics, reasons, team_of, series = [], {}, {}, {}, {}
    for team, rows in STAFF.items():
        for emp in rows:
            logs = _tasks(emp, rng)
            met = _metrics(logs)
            metrics[emp[0]] = met
            series[emp[0]] = _series(logs)
            team_of[emp[0]] = team
            reasons[emp[0]] = {
                tt: _reasons(rng, tt, round(m["n"] * (1 - m["first_pass"])), logs.get(tt + "#reason"))
                for tt, m in met.items()
            }
            employees.append(
                {
                    "id": emp[0],
                    "name": emp[1],
                    "role": emp[2],
                    "team": team,
                    "capacity_week": emp[3],
                    "assigned": round(emp[3] * emp[4]),
                    "task_types": list(met),
                    "done_30d": sum(m["done_30d"] for m in met.values()),
                }
            )
    # team benchmarks, per task type
    bench: dict[str, dict] = {}
    for tt in TASKS:
        who = [e for e, m in metrics.items() if tt in m]
        if len(who) >= 2:
            ms = [metrics[e][tt] for e in who]
            bench[tt] = {
                "median_min": round(statistics.median(m["median_min"] for m in ms), 1),
                "first_pass": round(sum(m["first_pass"] * m["n"] for m in ms) / sum(m["n"] for m in ms), 3),
                "people": len(who),
            }
    for emp in employees:
        mets = metrics[emp["id"]]
        usual = sum(m["median_min"] * m["n"] for m in mets.values()) / sum(m["n"] for m in mets.values())
        emp["minutes_week"] = round(emp["capacity_week"] * usual)
    gaps, strengths = [], []
    for e, met in metrics.items():
        for tt, m in met.items():
            b = bench.get(tt)
            if not b or m["n"] < MIN_TASKS:
                continue
            rework, team_rework = 1 - m["first_pass"], 1 - b["first_pass"]
            top = reasons[e][tt].most_common(1)[0][0] if reasons[e][tt] else None
            label = TASKS[tt][0].lower()
            if rework - team_rework >= QUALITY_MARGIN and rework >= QUALITY_RATIO * team_rework:
                mod = TRAINING.get((tt, "quality", top)) or TRAINING.get((tt, "quality", None))
                gaps.append(
                    {
                        "employee": e,
                        "task_type": tt,
                        "kind": "quality",
                        "n": m["n"],
                        "module": mod,
                        "avoidable_tasks": round(m["n"] * (rework - team_rework)),
                        "avoidable_minutes": round(m["n"] * (rework - team_rework) * m["median_min"]),
                        "evidence": f"Rework {rework:.0%} against the team's {team_rework:.0%} on {label} ({m['n']} tasks); "  # noqa: E501
                        f"most common reason: {top}.",
                    }
                )
            if m["median_min"] >= SLOW_RATIO * b["median_min"]:
                gaps.append(
                    {
                        "employee": e,
                        "task_type": tt,
                        "kind": "speed",
                        "n": m["n"],
                        "module": TRAINING.get((tt, "speed", None)),
                        "avoidable_tasks": 0,
                        "avoidable_minutes": round(m["n"] * (m["median_min"] - b["median_min"])),
                        "evidence": f"Median {m['median_min']:.0f} min against the team's {b['median_min']:.0f} on {label} "  # noqa: E501
                        f"({m['n']} tasks).",
                    }
                )
            if m["median_min"] <= FAST_RATIO * b["median_min"] and m["first_pass"] >= b["first_pass"]:
                strengths.append(
                    {
                        "employee": e,
                        "task_type": tt,
                        "kind": "strength",
                        "n": m["n"],
                        "evidence": f"Median {m['median_min']:.0f} min against the team's {b['median_min']:.0f} on {label}, "  # noqa: E501
                        f"first pass {m['first_pass']:.0%} ({m['n']} tasks).",
                    }
                )
    for emp in employees:
        emp["busy"] = emp["assigned"] >= BUSY * emp["capacity_week"]
    avoid = {(g["employee"], g["task_type"]) for g in gaps if g["kind"] == "quality"}
    alloc, left = _allocate(cards, employees, metrics, bench, avoid)
    found = {(g["employee"], g["task_type"], g["kind"]) for g in gaps + strengths}
    found |= {(e["id"], "load", "capacity") for e in employees if e["busy"]}
    key = [(p["employee"], p["task_type"], p["kind"]) for p in PLANTED]
    return {
        "synthetic": True,
        "note": "Staff, names and task logs are synthetic. The engine records no employee data in shadow mode; the open "  # noqa: E501
        "queue is real. Suggestions are for the manager to decide, not for hiring, firing or pay decisions.",
        "as_of": as_of.isoformat(),
        "days": DAYS,
        "min_tasks": MIN_TASKS,
        "teams": {
            t: {"label": TEAM_LABEL[t], "task_types": [{"id": tt, "label": TASKS[tt][0]} for tt, _ in WORK[t]]}
            for t in STAFF
        },
        "employees": employees,
        "metrics": metrics,
        "benchmark": bench,
        "reasons": {e: {tt: dict(c.most_common(3)) for tt, c in r.items()} for e, r in reasons.items()},
        "history": _history(series, employees),
        "handle_time": {e: {tt: v["spread"] for tt, v in d.items()} for e, d in series.items()},
        "rework_minutes": {
            e: {tt: round(m["n"] * (1 - m["first_pass"]) * m["median_min"]) for tt, m in met.items()}
            for e, met in metrics.items()
        },
        "scenarios": _scenarios(cards, employees, metrics, bench, gaps, as_of, cause),
        "assumptions": {
            "week_minutes": "Each person's weekly minutes = weekly slot capacity x their usual handling time (volume-weighted median).",  # noqa: E501
            "rework": "A reworked task is done twice, so a task costs its median minutes x (1 + rework rate).",
            "inflow": "New work arrives each week at the rate of the last 30 days.",
            "overtime": OVERTIME,
            "upstream_cut": UPSTREAM_CUT,
            "weeks": WEEKS,
        },
        "gaps": gaps,
        "strengths": strengths,
        "allocation": alloc,
        "unallocated": left,
        "improvements": _improvements(cards, employees, metrics, reasons, team_of, left, cause),
        "planted": PLANTED,
        "found_vs_planted": {
            "planted": len(key),
            "found": sum(1 for k in key if k in found),
            "flagged_but_not_planted": [list(k) for k in sorted(found - set(key))],
        },
    }


def _why(tt: str, m: dict, b: dict, free: int, cap: int) -> str:
    label = TASKS[tt][0].lower()
    parts = []
    if m["median_min"] <= FAST_RATIO * b["median_min"]:
        parts.append(f"fastest on {label} (median {m['median_min']:.0f} min against the team's {b['median_min']:.0f})")
    elif m["median_min"] <= 0.95 * b["median_min"]:
        parts.append(f"faster than the team median on {label} ({m['median_min']:.0f} against {b['median_min']:.0f})")
    parts.append(f"first pass {m['first_pass']:.0%} (team {b['first_pass']:.0%})")
    parts.append(f"{free} of {cap} weekly slots were free")
    return "; ".join(parts).capitalize() + "."


def _allocate(cards: list[dict], employees: list[dict], metrics: dict, bench: dict, avoid: set):
    """Split each team's real open work across the people who fit best and have room. Returns (rows, unallocated).

    People with a quality gap on that task type are left out until they have been trained.
    Score = 0.4 speed (against the team median) + 0.4 first-pass rate + 0.2 share of weekly capacity still free, less a
    small penalty for each chunk this person already took of the same task type, so one person does not take it all.
    """
    rows, left = [], []
    for team, work in WORK.items():
        crew = [e for e in employees if e["team"] == team]
        room = {e["id"]: e["capacity_week"] - e["assigned"] for e in crew}
        groups = []
        for tt, owners in work:
            items = [c for c in cards if c["action_type"] == tt and c["owner"] in owners]
            if items:
                items.sort(key=lambda c: -c["expected_value"])
                groups.append((tt, items))
        # most constrained task types first (fewest people who can do them), so specialists are not used up elsewhere
        able = {tt: sum(1 for e in crew if tt in metrics[e["id"]] and (e["id"], tt) not in avoid) for tt, _ in groups}
        groups.sort(key=lambda g: (able[g[0]], -sum(c["expected_value"] for c in g[1])))
        for tt, items in groups:
            todo, given, row_of = list(items), Counter(), {}
            chunk_cap = max(1, math.ceil(len(items) / 3))
            while todo:
                fit = []
                for e in crew:
                    m = metrics[e["id"]].get(tt)
                    if m and m["n"] >= MIN_TASKS and room[e["id"]] > 0 and (e["id"], tt) not in avoid:
                        speed = max(0.5, min(1.5, bench[tt]["median_min"] / m["median_min"])) / 1.5
                        score = 0.4 * speed + 0.4 * m["first_pass"] + 0.2 * room[e["id"]] / e["capacity_week"]
                        fit.append((score - 0.15 * given[e["id"]], e, m))
                if not fit:
                    break
                _, e, m = max(fit, key=lambda f: f[0])
                take = todo[: min(room[e["id"]], chunk_cap)]
                todo = todo[len(take) :]
                given[e["id"]] += 1
                if e["id"] in row_of:
                    row = row_of[e["id"]]
                    row["items"] += len(take)
                    row["value"] = f"{Decimal(row['value']) + sum(c['expected_value'] for c in take):.2f}"
                    row["load_after"] += len(take)
                else:
                    row = {
                        "team": team,
                        "task_type": tt,
                        "employee": e["id"],
                        "items": len(take),
                        "value": f"{sum(c['expected_value'] for c in take):.2f}",
                        "sample": [c["claim"] for c in take[:3]],
                        "reason": _why(tt, m, bench[tt], room[e["id"]], e["capacity_week"]),
                        "load_before": e["capacity_week"] - room[e["id"]],
                        "load_after": e["capacity_week"] - room[e["id"]] + len(take),
                        "capacity_week": e["capacity_week"],
                    }
                    row_of[e["id"]] = row
                    rows.append(row)
                room[e["id"]] -= len(take)
            if todo:
                left.append(
                    {
                        "team": team,
                        "task_type": tt,
                        "items": len(todo),
                        "value": f"{sum(c['expected_value'] for c in todo):.2f}",
                        "why": "Nobody on the team has completed enough of these to suggest an owner"
                        if not any(metrics[e["id"]].get(tt) for e in crew)
                        else "Only people with a quality gap on this task have free capacity"
                        if any(room[e["id"]] > 0 and (e["id"], tt) in avoid for e in crew)
                        else "No free weekly capacity left on the people who fit",
                    }
                )
    return rows, left


WEEKS = 12  # scenario horizon
HISTORY_WEEKS = 13

OVERTIME = 0.10
UPSTREAM_CUT = 0.5


def _q(sorted_vals: list[float], p: float) -> float:
    return round(sorted_vals[min(len(sorted_vals) - 1, int(p * len(sorted_vals)))], 1)


def _series(logs: dict) -> dict:
    """Per task type: tasks and rework by week (oldest first) and the spread of handling time."""
    out = {}
    for tt, rows in logs.items():
        if tt.endswith("#reason") or not rows:
            continue
        weeks, rework = [0] * HISTORY_WEEKS, [0] * HISTORY_WEEKS
        for _, first, _, ago in rows:
            w = HISTORY_WEEKS - 1 - min(HISTORY_WEEKS - 1, ago // 7)
            weeks[w] += 1
            rework[w] += 0 if first else 1
        mins = sorted(r[0] for r in rows)
        out[tt] = {
            "weeks": weeks, "rework": rework,
            "spread": [_q(mins, p) for p in (0.1, 0.25, 0.5, 0.75, 0.9)],
        }  # fmt: skip
    return out


def _profile(metrics: dict, bench: dict, e: str, tt: str, train: bool) -> tuple[float, float]:
    """Median minutes and first-pass rate for a person on a task, with the flagged gaps closed when `train`."""
    m, b = metrics[e][tt], bench[tt]
    med, fp = m["median_min"], m["first_pass"]
    if train:
        if med >= SLOW_RATIO * b["median_min"]:
            med = b["median_min"]
        if (1 - fp) - (1 - b["first_pass"]) >= QUALITY_MARGIN and (1 - fp) >= QUALITY_RATIO * (1 - b["first_pass"]):
            fp = b["first_pass"]
    return med, fp


def _simulate(crew, work, items, inflow, metrics, bench, avoid, *, smart, train=False, overtime=0.0, scale=None):
    """Twelve weeks of clearing one team's open work. `items` is {task type: [dollars, highest first]}.

    A reworked task is done twice, so a task costs median minutes x (1 + rework rate). Smart = the suggested
    allocation (best score first, people with a quality gap left out); otherwise an even split ignoring skill.
    """
    scale = scale or {}
    orphans = [
        tt for tt in items if not any(tt in metrics[e["id"]] and metrics[e["id"]][tt]["n"] >= MIN_TASKS for e in crew)
    ]  # task types nobody on the team has enough history on: they cannot be placed, so they are left out
    todo = {tt: sorted(v, reverse=True) for tt, v in items.items() if tt not in orphans}
    inflow = {tt: r for tt, r in inflow.items() if tt not in orphans}
    acc = Counter()
    weeks = []
    ceiling = 0.0
    for wk in range(WEEKS):
        free = {e["id"]: e["minutes_week"] * (1 - e["assigned"] / e["capacity_week"] + overtime) for e in crew}
        if wk == 0:
            for e in crew:
                effs = [
                    (lambda p: p[0] * (1 + (1 - p[1])))(_profile(metrics, bench, e["id"], tt, False))
                    for tt in metrics[e["id"]]
                    if tt in todo and metrics[e["id"]][tt]["n"] >= MIN_TASKS
                ]
                ceiling += free[e["id"]] / min(effs) if effs else 0
        used = rework = cleared = redone = 0.0
        dollars = 0.0
        able = {
            tt: sum(1 for e in crew if tt in metrics[e["id"]] and (train or not smart or (e["id"], tt) not in avoid))
            for tt in todo
        }
        for tt in sorted(todo, key=lambda t: (able[t] if smart else 0, -sum(todo[t]))):
            elig = [
                e for e in crew
                if tt in metrics[e["id"]] and metrics[e["id"]][tt]["n"] >= MIN_TASKS
                and (train or not smart or (e["id"], tt) not in avoid)
            ]  # fmt: skip
            if not elig or not todo[tt]:
                continue
            prof = {e["id"]: _profile(metrics, bench, e["id"], tt, train) for e in elig}
            if smart:

                def score(e, prof=prof, tt=tt, free=free):
                    med, fp = prof[e["id"]]
                    speed = max(0.5, min(1.5, bench[tt]["median_min"] / med)) / 1.5
                    return 0.4 * speed + 0.4 * fp + 0.2 * free[e["id"]] / e["minutes_week"]

                order = sorted(elig, key=score, reverse=True)
                share = len(todo[tt])
            else:
                order = elig
                share = math.ceil(len(todo[tt]) / len(elig))
            for e in order:
                med, fp = prof[e["id"]]
                eff = med * (1 + (1 - fp))
                k = min(share, len(todo[tt]), int(free[e["id"]] // eff))
                if k <= 0:
                    continue
                got, todo[tt] = todo[tt][:k], todo[tt][k:]
                free[e["id"]] -= k * eff
                used += k * eff
                rework += k * (1 - fp) * med
                redone += k * (1 - fp)
                cleared += k
                dollars += sum(got)
        for tt, rate in inflow.items():
            acc[tt] += rate * scale.get(tt, 1.0)
            n = int(acc[tt])
            acc[tt] -= n
            if n and items.get(tt):
                todo[tt] = sorted(todo.get(tt, []) + [sum(items[tt]) / len(items[tt])] * n, reverse=True)
        weeks.append({
            "backlog": sum(len(v) for v in todo.values()), "cleared": int(cleared),
                "right_first_time": round(cleared - redone), "dollars": round(dollars, 2),
            "backlog_dollars": round(sum(sum(v) for v in todo.values()), 2), "rework_min": round(rework),
            "minutes_used": round(used),
        })  # fmt: skip
    return weeks, round(ceiling, 1), orphans, round(sum(inflow.values()), 2)


def _scenarios(cards, employees, metrics, bench, gaps, as_of, cause) -> dict:
    avoid = {(g["employee"], g["task_type"]) for g in gaps if g["kind"] == "quality"}
    out = {}
    for team, work in WORK.items():
        crew = [e for e in employees if e["team"] == team]
        items, inflow = defaultdict(list), Counter()
        mine = []
        for c in cards:
            for tt, owners in work:
                if c["action_type"] == tt and c["owner"] in owners:
                    items[tt].append(float(c["expected_value"]))
                    mine.append(c)
                    if (as_of - date.fromisoformat(c["raised_on"])).days <= 30:
                        inflow[tt] += 7 / 30
        denials = [c for c in mine if c["agent"] == "a8_denial"]
        top = Counter(cause(c) for c in denials).most_common(1) if cause else []
        share = top[0][1] / len(denials) if top and denials else 0
        cut = {tt: 1 - UPSTREAM_CUT * share for tt in items if tt.startswith("a8")}
        kw = {"crew": crew, "work": work, "items": dict(items), "inflow": dict(inflow), "metrics": metrics,
              "bench": bench, "avoid": avoid}  # fmt: skip
        plan = [
            ("even", "Even split, no guidance", {"smart": False}),
            ("suggested", "Suggested allocation", {"smart": True}),
            ("trained", "+ training closes the flagged gaps", {"smart": True, "train": True}),
            ("overtime", "+ 10% overtime", {"smart": True, "train": True, "overtime": OVERTIME}),
            ("upstream", f"+ upstream fix halves '{top[0][0]}' denials" if top else "+ upstream fix",
             {"smart": True, "train": True, "overtime": OVERTIME, "scale": cut}),
        ]  # fmt: skip
        rows, ceiling = [], 0.0
        for sid, label, extra in plan:
            weeks, ceiling, orphans, rate = _simulate(**kw, **extra)
            settled = 1.05 * rate + 1  # what is left is about one week of new arrivals
            clear = next((i + 1 for i, w in enumerate(weeks) if w["backlog"] <= settled), None)
            extra = OVERTIME if sid in ("overtime", "upstream") else 0
            free_min = sum(e["minutes_week"] * (1 - e["assigned"] / e["capacity_week"] + extra) for e in crew)
            rows.append({
                "id": sid, "label": label, "weeks": weeks, "weeks_to_clear": clear,
                "first_week_cleared": weeks[0]["cleared"],
                "first_week_right": weeks[0]["right_first_time"],
                "dollars_2wk": round(sum(w["dollars"] for w in weeks[:2]), 2),
                "dollars_4wk": round(sum(w["dollars"] for w in weeks[:4]), 2),
                "rework_min_4wk": sum(w["rework_min"] for w in weeks[:4]),
                "utilisation": round(weeks[0]["minutes_used"] / max(1, free_min), 3),
            })  # fmt: skip
        out[team] = {
            "open_items": sum(len(v) for v in items.values()),
            "open_dollars": round(sum(sum(v) for v in items.values()), 2),
            "inflow_per_week": rate, "ceiling_per_week": ceiling, "scenarios": rows,
            "unplaceable": {"types": orphans, "items": sum(len(items[t]) for t in orphans),
                            "dollars": round(sum(sum(items[t]) for t in orphans), 2)},
        }  # fmt: skip
    return out


def _improvements(cards, employees, metrics, reasons, team_of, left, cause) -> list[dict]:
    out = []
    for team, work in WORK.items():
        mine = [c for c in cards if any(c["action_type"] == tt and c["owner"] in o for tt, o in work)]
        crew = [e for e in employees if e["team"] == team]
        spare = sum(e["capacity_week"] - e["assigned"] for e in crew)
        unplaced = sum(x["items"] for x in left if x["team"] == team)
        if unplaced:
            out.append(
                {
                    "team": team,
                    "title": "The open queue is larger than the team's free capacity this week",
                    "evidence": f"{len(mine)} items are open and the team has {spare} free weekly slots; {unplaced} items "  # noqa: E501
                    "cannot be placed. Options: overtime or temporary help, or reduce the inflow at its source.",
                }
            )
        for e in crew:
            if e["busy"]:
                out.append(
                    {
                        "team": team,
                        "title": f"{e['name']} is close to capacity",
                        "evidence": f"{e['assigned']} of {e['capacity_week']} weekly slots are already assigned. "
                        "New work should go elsewhere.",
                    }
                )
        rw: Counter = Counter()
        for e in crew:
            for tt, c in reasons[e["id"]].items():
                for r, k in c.items():
                    rw[(tt, r)] += k
        if rw:
            (tt, r), k = rw.most_common(1)[0]
            out.append(
                {
                    "team": team,
                    "title": f"The most common rework reason is '{r}' on {TASKS[tt][0].lower()}",
                    "evidence": f"{k} of {sum(rw.values())} reworked tasks in {DAYS} days. A checklist or a rule at the start "  # noqa: E501
                    "of this task may help more than training one person.",
                }
            )
        if cause:
            causes = Counter(cause(c) for c in mine if c["agent"] == "a8_denial")
            if causes:
                name, k = causes.most_common(1)[0]
                out.append(
                    {
                        "team": team,
                        "title": f"'{name}' is the largest denial cause in this team's queue",
                        "evidence": f"{k} open denials. If the cause sits upstream (registration, eligibility, "
                        "authorization), fixing it there removes work from this team.",
                    }
                )
    return out


def _history(series: dict, employees: list[dict]) -> dict:
    """Weekly throughput by team and task type (oldest week first), with the weekly rework rate."""
    out: dict[str, dict] = {}
    team_of = {e["id"]: e["team"] for e in employees}
    for e, per in series.items():
        t = out.setdefault(team_of[e], {"by_type": {}, "tasks": [0] * HISTORY_WEEKS, "rework": [0] * HISTORY_WEEKS})
        for tt, d in per.items():
            row = t["by_type"].setdefault(tt, [0] * HISTORY_WEEKS)
            for i in range(HISTORY_WEEKS):
                row[i] += d["weeks"][i]
                t["tasks"][i] += d["weeks"][i]
                t["rework"][i] += d["rework"][i]
    for t in out.values():
        t["first_pass"] = [round(1 - r / n, 3) if n else None for r, n in zip(t["rework"], t["tasks"], strict=True)]
    return out
