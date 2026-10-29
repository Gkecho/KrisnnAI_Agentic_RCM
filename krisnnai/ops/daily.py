"""One run of the whole system: load what arrived, check it, advance every agent, report.

    load inbox -> match -> load gate -> for each date window, each agent in dependency order:
        (seed its tables) -> sweep -> replay its new events only  -> tower for the last days -> summary

A daily run is a one-window backfill, so the two cannot drift apart: sweep dates sit on the same calendar grid
(`registry.grid_start`) and replay skips events that already have a decision record. Every step is idempotent, so a run
that stops half way is finished by running it again. Shadow mode throughout: nothing is executed or sent.
"""

from __future__ import annotations

import json
import time as clock
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.engine import Engine

import krisnnai.model as m
from krisnnai.engine import replay
from krisnnai.match import run_matching
from krisnnai.model import tenant_session
from krisnnai.ops.gate import check_gate
from krisnnai.ops.inbox import LoadReport, load_inbox
from krisnnai.ops.registry import Step, grid_start, steps

TOWER_DAYS = 7  # a backfill gives the tower this many daily events at the end; a daily run gives it today's


@dataclass
class RunReport:
    mode: str
    as_of: date
    status: str  # ok | gated | failed
    gate: str  # passed | failed | skipped
    files_loaded: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    events_added: int = 0
    reasons: list[str] = field(default_factory=list)
    steps: dict[str, dict] = field(default_factory=dict)
    cards: dict = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)
    run_id: int | None = None

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


# ---------------------------------------------------------------------------------------------- run log


def last_run(engine: Engine, tenant_id: int, ok_only: bool = False) -> m.OpsRun | None:
    with tenant_session(engine, tenant_id) as s:
        stmt = select(m.OpsRun).order_by(m.OpsRun.id.desc())
        if ok_only:
            stmt = stmt.where(m.OpsRun.status == "ok")
        row = s.scalars(stmt).first()
        if row is not None:
            s.expunge(row)
        return row


def watermark(engine: Engine, tenant_id: int) -> date | None:
    """The latest date every agent has been advanced to by a run that finished ok."""
    with tenant_session(engine, tenant_id) as s:
        return s.scalar(select(func.max(m.OpsRun.as_of)).where(m.OpsRun.status == "ok"))


def _record(engine: Engine, tenant_id: int, rep: RunReport, started: datetime, go_live: date | None) -> int:
    with tenant_session(engine, tenant_id) as s:
        row = m.OpsRun(
            mode=rep.mode, as_of=rep.as_of, go_live=go_live, started_at=started, finished_at=datetime.utcnow(),
            files_loaded=rep.files_loaded, files_skipped=rep.files_skipped, files_failed=rep.files_failed,
            events_added=rep.events_added, gate=rep.gate, status=rep.status,
            detail=json.dumps({"reasons": rep.reasons, "steps": rep.steps, "cards": rep.cards, "timings": rep.timings},
                              sort_keys=True),
        )
        s.add(row)
        s.commit()
        return row.id


# ---------------------------------------------------------------------------------------------- the run


def _decisions(engine: Engine, tenant_id: int, agent_id: str) -> int:
    with tenant_session(engine, tenant_id) as s:
        return s.scalar(select(func.count()).select_from(m.DecisionRecord).where(m.DecisionRecord.agent_id == agent_id))


def _windows(start: date, end: date, step_days: int) -> list[tuple[date, date]]:
    out, a = [], start
    while a <= end:
        b = min(a + timedelta(days=step_days - 1), end)
        out.append((a, b))
        a = b + timedelta(days=1)
    return out


def _advance(
    engine: Engine, tenant_id: int, step: Step, a: date, b: date, until: datetime, tower_from: date | None, out: dict
) -> None:
    rec = out.setdefault(step.name, {"sweep_events": 0, "records": 0, "seconds": 0.0})
    t0 = clock.perf_counter()
    if step.sweep is not None:
        lo = a
        if step.cadence:
            lo = grid_start(a, step.cadence)
        elif step.name == "a14":
            lo = max(a, tower_from or a)
        if lo <= b:
            res = step.sweep(engine, tenant_id, lo, b, step.cadence) if step.cadence else step.sweep(
                engine, tenant_id, lo, b
            )
            rec["sweep_events"] += res.events
    before = _decisions(engine, tenant_id, step.agent_id)
    replay(engine, tenant_id, step.make_agent(), until=until, only_new=True)
    rec["records"] += _decisions(engine, tenant_id, step.agent_id) - before
    rec["seconds"] = round(rec["seconds"] + clock.perf_counter() - t0, 3)


def run_period(
    engine: Engine,
    tenant_id: int,
    salt: str,
    as_of: date,
    *,
    inbox: Path | None = None,
    archive: Path | None = None,
    mode: str = "daily",
    start: date | None = None,
    step_days: int = 28,
    go_live: date | None = None,
    allow_failed: bool = False,
    run_date: date | None = None,
) -> RunReport:
    """Advance everything to `as_of`. `start` defaults to the day after the watermark (or `as_of` on a first run)."""
    started = datetime.utcnow()
    rep = RunReport(mode, as_of, "ok", "skipped")
    t0 = clock.perf_counter()
    try:
        if inbox is not None:
            loaded: LoadReport = load_inbox(
                engine, tenant_id, inbox, archive or inbox.parent / "archive", salt, run_date or as_of
            )
            rep.files_loaded, rep.files_skipped = loaded.count("loaded"), loaded.count("skipped")
            rep.files_failed = loaded.count("failed")
            rep.events_added += loaded.events
            rep.timings["load"] = round(clock.perf_counter() - t0, 3)
        until = datetime.combine(as_of, time.max)
        t1 = clock.perf_counter()
        run_matching(engine, tenant_id, until)
        rep.timings["match"] = round(clock.perf_counter() - t1, 3)
        t1 = clock.perf_counter()
        gate = check_gate(engine, tenant_id, as_of, rep.files_failed, allow_failed)
        rep.timings["gate"] = round(clock.perf_counter() - t1, 3)
        rep.gate = "passed" if gate.passed else "failed"
        if not gate.passed:
            rep.status, rep.reasons = "gated", gate.reasons
            rep.run_id = _record(engine, tenant_id, rep, started, go_live)
            return rep

        registry = steps()
        with tenant_session(engine, tenant_id) as s:
            for st in registry:
                if st.seed is not None:
                    st.seed(s)
            s.commit()
        wm = watermark(engine, tenant_id)
        first = start or ((wm + timedelta(days=1)) if wm is not None else as_of)
        if first <= as_of:
            tower_from = max(first, as_of - timedelta(days=TOWER_DAYS - 1))
            width = (as_of - first).days + 1 if mode == "daily" else step_days
            for a, b in _windows(first, as_of, width):
                for st in registry:
                    _advance(engine, tenant_id, st, a, b, until, tower_from, rep.steps)
        else:  # already advanced past this date: only replay anything new that the load brought in
            for st in registry:
                _advance(engine, tenant_id, st, as_of + timedelta(days=1), as_of, until, None, rep.steps)
        rep.events_added += sum(v["sweep_events"] for v in rep.steps.values())
        rep.cards = _cards(engine, tenant_id, as_of, go_live)
    except Exception as e:
        rep.status, rep.reasons = "failed", [f"{type(e).__name__}: {e}"]
        rep.run_id = _record(engine, tenant_id, rep, started, go_live)
        raise
    rep.run_id = _record(engine, tenant_id, rep, started, go_live)
    return rep


def _cards(engine: Engine, tenant_id: int, as_of: date, go_live: date | None) -> dict:
    from krisnnai.agents.a14_tower import open_cards

    cards = open_cards(engine, tenant_id, as_of)
    by_agent: dict[str, int] = {}
    for c in cards:
        by_agent[c["agent"]] = by_agent.get(c["agent"], 0) + 1
    out = {
        "open": len(cards), "overdue": sum(1 for c in cards if c["overdue"]),
        "expected_value": str(sum((c["expected_value"] for c in cards), start=0)), "by_agent": by_agent,
    }
    if go_live is not None:
        new = [c for c in cards if date.fromisoformat(c["raised_on"]) >= go_live]
        out["since_go_live"] = {"open": len(new), "historical": len(cards) - len(new)}
    return out


def format_report(rep: RunReport) -> str:
    head = (
        f"{rep.mode} run to {rep.as_of}: {rep.status} (gate {rep.gate}); files {rep.files_loaded} loaded, "
        f"{rep.files_skipped} skipped, {rep.files_failed} failed; {rep.events_added} events added"
    )
    lines = [head, *(f"  gate: {r}" for r in rep.reasons if rep.status != "ok")]
    for name, v in rep.steps.items():
        lines.append(f"  {name:4s} sweep events {v['sweep_events']:6d}   decision records {v['records']:6d}")
    if rep.cards:
        c = rep.cards
        lines.append(f"  open cards {c['open']} ({c['overdue']} overdue), expected value {c['expected_value']}")
        if "since_go_live" in c:
            lines.append(f"  since go-live {c['since_go_live']['open']}, historical {c['since_go_live']['historical']}")
    return "\n".join(lines)
