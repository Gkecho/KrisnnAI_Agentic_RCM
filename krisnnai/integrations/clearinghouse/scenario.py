"""Choosing the day a bot acts, so its effect can be seen at the agents' next checkpoint.

The simulated book is historical, so "upcoming visit" only makes sense relative to a chosen day. A1 raises its 72 h
checkpoint three days before a visit and its 24 h checkpoint one day before. The best day is the one with the most
appointments that carry a planted check defect (no check, stale check) and whose visit is exactly three days later: A1
flags them that day, the bot checks eligibility the same day, and the 24 h checkpoint two days later sees the answer.
"""

from __future__ import annotations

import csv
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from krisnnai.integrations.clearinghouse.claim_store import PmExtract

DEFECTS = {"no_check", "stale_check"}
WINDOW = (3, 3)  # days between the bot's day and the visit


def read_defects(truth_dir: Path) -> dict[str, str]:
    path = truth_dir / "elig_truth.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {r["appointment_id"]: r["defect"] for r in csv.DictReader(f)}


def pick_bot_day(extract: PmExtract, truth_dir: Path) -> tuple[date, list[str]]:
    """(day, appointment ids with a planted check defect and a visit three days after it)."""
    defects = read_defects(truth_dir)
    appts = [
        (a["appointment_id"], date.fromisoformat(a["appt_date"]), date.fromisoformat(a["booked_on"]))
        for a in extract.appointments.values()
        if defects.get(a["appointment_id"]) in DEFECTS
    ]
    if not appts:
        raise ValueError("no appointment with a planted no_check / stale_check defect in this book")
    score: Counter = Counter()
    for _, dos, booked in appts:
        for lead in range(WINDOW[0], WINDOW[1] + 1):
            day = dos - timedelta(days=lead)
            if day >= booked:
                score[day] += 1
    day = max(score, key=lambda d: (score[d], d))
    chosen = [
        appt for appt, dos, booked in appts
        if WINDOW[0] <= (dos - day).days <= WINDOW[1] and day >= booked
    ]  # fmt: skip
    return day, sorted(chosen)
