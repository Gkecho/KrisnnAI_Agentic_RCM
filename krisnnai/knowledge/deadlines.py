# ruff: noqa: E501
"""Deadlines from the Knowledge Book: the appeal deadline and the corrected-claim deadline are separate routes.

A deadline is computed only when the governing rule, the start date, the day-count method (calendar or business days) and
inclusivity are all configured. Anything unconfigured, unknown or missing comes back as a Problem, never as a date. The
evaluation date is passed in (the simulation clock); this module never reads the computer's date.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from krisnnai.knowledge.book import Book, Problem

ROUTES = {  # route -> (rule family, content field holding the window in days)
    "appeal": ("denial_appeal", "window_days"),
    "corrected_claim": ("billing", "corrected_claim_window_days"),
}


@dataclass(frozen=True)
class Deadline:
    due: date
    rule_id: str
    version: int
    route: str
    start: date
    window_days: int
    method: str
    expired: bool
    days_left: int
    note: str = ""


@dataclass(frozen=True)
class DeadlineResult:
    deadline: Deadline | None = None
    problem: Problem | None = None

    @property
    def ok(self) -> bool:
        return self.deadline is not None


def add_days(start: date, days: int, business: bool, holidays: frozenset[date] = frozenset()) -> date:
    if not business:
        return start + timedelta(days=days)
    d, left = start, days
    while left > 0:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in holidays:
            left -= 1
    return d


def deadline(book: Book, route: str, payer: str, service: str, dates: dict[str, date], as_of: date, plan: str | None = None,
             state: str | None = None) -> DeadlineResult:  # fmt: skip
    family, field_name = ROUTES[route]
    found = book.lookup(payer, family, service, dates, as_of, plan, state)
    if not found.ok:
        return DeadlineResult(problem=found.problem)
    rule = found.rule
    assert rule is not None
    c = rule.content
    missing = [f for f in (field_name, "day_count", "inclusive") if f in rule.unknown or c.get(f) is None]
    if missing:
        return DeadlineResult(problem=Problem(
            "unknown_fact", f"{rule.rule_id} v{rule.version} does not say: {', '.join(missing)}",
            f"Confirm {', '.join(missing)} for {payer} ({route} route)", context={"rule": rule.rule_id, "version": rule.version}))
    if c["day_count"] not in ("calendar", "business"):
        return DeadlineResult(problem=Problem("unknown_fact", f"{rule.rule_id}: day_count must be calendar or business",
                                              f"Confirm how days are counted for {payer}", context={"rule": rule.rule_id}))
    start = dates[rule.date_basis]  # lookup already checked it is present
    window = int(c[field_name])
    business = c["day_count"] == "business"
    holidays = frozenset(date.fromisoformat(h) for h in c.get("holidays", []))
    # inclusive: the start day is day 1, so the window ends window-1 days after it
    due = add_days(start, window - 1 if c["inclusive"] else window, business, holidays)
    note = "business days, weekends skipped" + ("" if holidays else "; no holiday calendar configured") if business else ""
    method = f"{window} {c['day_count']} days from the {rule.date_basis}, {'including' if c['inclusive'] else 'excluding'} the first day"
    return DeadlineResult(deadline=Deadline(due, rule.rule_id, rule.version, route, start, window, method, as_of > due,
                                            (due - as_of).days, note))
