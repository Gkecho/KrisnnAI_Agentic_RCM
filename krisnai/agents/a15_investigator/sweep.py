"""The sweeper: turns "realisation fell in this slice" into an event the engine can act on.

On each sweep date one Snapshot is loaded as of that date, slices are flagged (variance.slices), each flagged slice is
explained (causes.explain) and the answer, known at that date, goes into the event payload. A slice gets an event
when it first flags, again when its fall moves by CHANGE_POINTS or its top cause changes, and once more
(flagged = false) when it clears. Events are append-only and carry `known_at`; running the same sweep twice adds
nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from hashlib import sha256

from sqlalchemy import select

import krisnai.model as m
from krisnai.agents.a15_investigator import config
from krisnai.agents.a15_investigator.causes import explain
from krisnai.agents.a15_investigator.variance import slices
from krisnai.agents.a15_lite.detect import detect
from krisnai.agents.a15_lite.snapshot import load_snapshot
from krisnai.agents.upstream import upstream_flags
from krisnai.model import tenant_session

EVENT_TYPE = "revenue.variance"
D4, D2 = Decimal("0.0001"), Decimal("0.01")


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool  # True when this exact sweep was already recorded


def _planned(engine, tenant_id: int, start: date, end: date, every_days: int, last: dict, rounds: dict) -> list:
    """Every (day, key, payload) this sweep would raise, judged against the slices' latest recorded state."""
    planned: list[tuple[date, str, dict]] = []

    def add(day: date, key: str, payload: dict) -> None:
        rounds[key] = rounds.get(key, 0) + 1
        payload = {**payload, "key": key, "due_on": day.isoformat(), "round": rounds[key]}
        last[key] = payload
        planned.append((day, key, payload))

    day = start
    while day <= end:
        snap = load_snapshot(engine, tenant_id, day)
        now = {x.key: x for x in slices(snap, day)}
        if now:
            findings, flags = detect(snap), upstream_flags(engine, tenant_id, day)
        for key, x in now.items():
            why = explain(x, findings, flags)
            top = why["causes"][0]["cause"] if why["causes"] else ""
            prev = last.get(key)
            if (
                prev is None or not prev["flagged"] or prev["top_cause"] != top
                or abs(Decimal(prev["drop"]) - x.drop) >= config.CHANGE_POINTS
            ):
                add(day, key, {
                    "flagged": True, "payer": x.payer, "cpt": x.cpt or "", "top_cause": top,
                    "baseline": str(x.baseline.quantize(D4)), "recent": str(x.recent.quantize(D4)),
                    "drop": str(x.drop.quantize(D4)), "impact": str(x.impact),
                    "expected_recent": str(x.expected_recent.quantize(D2)),
                    "lines_recent": x.lines_recent, "lines_baseline": x.lines_baseline,
                    "recent_days": config.RECENT_DAYS, "baseline_days": config.BASELINE_DAYS, **why,
                })  # fmt: skip
        for key, prev in list(last.items()):
            if prev["flagged"] and key not in now:
                add(day, key, {"flagged": False, "payer": prev["payer"], "cpt": prev["cpt"], "top_cause": "",
                               "drop": "0", "impact": "0.00"})  # fmt: skip
        day += timedelta(days=every_days)
    return planned


def sweep(engine, tenant_id: int, start: date, end: date, every_days: int = config.SWEEP_EVERY_DAYS) -> SweepResult:
    digest = sha256(f"a15sweep|{tenant_id}|{start}|{end}|{every_days}".encode()).hexdigest()
    last: dict[str, dict] = {}
    rounds: dict[str, int] = {}
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        for payload in s.scalars(select(m.Event.payload).where(m.Event.event_type == EVENT_TYPE)):
            p = json.loads(payload)
            if p["key"] not in last or p["due_on"] >= last[p["key"]]["due_on"]:
                last[p["key"]] = p
            rounds[p["key"]] = rounds.get(p["key"], 0) + 1
    planned = _planned(engine, tenant_id, start, end, every_days, last, rounds)  # reads only; written below
    with tenant_session(engine, tenant_id) as s:
        sf = m.SourceFile(
            file_name=f"a15sweep_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0, status="loaded"
        )
        s.add(sf)
        s.flush()
        for n, (day, key, payload) in enumerate(planned, start=1):
            s.add(
                m.Event(
                    source_file_id=sf.id, event_type=EVENT_TYPE, isa13=day.strftime("%Y%m%d"),
                    gs06=str(n)[:9], st02=str(payload["round"]), seq_in_file=n,
                    known_at=datetime.combine(day, time.min), payload=json.dumps(payload, sort_keys=True),
                )
            )  # fmt: skip
        s.commit()
    return SweepResult(len(planned), False)
