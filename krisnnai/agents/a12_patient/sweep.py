"""The sweeper: turns "this patient balance has an open item" into an event the engine can act on.

On each sweep date every claim with a confirmed patient share is checked as of that date. A claim with a gap gets an
`patient.balance_check` event when it first shows one, again when the gap or its aging stage changes, and every
`repeat_days` while it stays open; when a flagged claim comes clean (paid, or a plan) one closing event lets the agent
close its card. Events are append-only and carry `known_at`; running the same sweep twice adds nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256

from sqlalchemy import select

import krisnnai.model as m
from krisnnai.agents.a12_patient import config
from krisnnai.agents.a12_patient.data import load_accounts
from krisnnai.agents.a12_patient.rules import check
from krisnnai.model import tenant_session

EVENT_TYPE = "patient.balance_check"


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool  # True when this exact sweep was already recorded


def sweep(engine, tenant_id: int, start: date, end: date, every_days: int = 7, repeat_days: int = config.REPEAT_DAYS):
    digest = sha256(f"a12sweep|{tenant_id}|{start}|{end}|{every_days}|{repeat_days}".encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        accounts = load_accounts(s)
        last: dict[str, tuple[date, tuple]] = {}
        rounds: dict[str, int] = {}
        for payload in s.scalars(select(m.Event.payload).where(m.Event.event_type == EVENT_TYPE)):
            p = json.loads(payload)
            day, sig = date.fromisoformat(p["due_on"]), (p["kind"], p["stage"])
            if p["claim"] not in last or day >= last[p["claim"]][0]:
                last[p["claim"]] = (day, sig if p["kind"] else ())
            rounds[p["claim"]] = rounds.get(p["claim"], 0) + 1
        sf = m.SourceFile(
            file_name=f"a12sweep_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0, status="loaded"
        )
        s.add(sf)
        s.flush()
        added = 0
        day = start
        while day <= end:
            at = datetime.combine(day, time.min)
            for a in accounts.values():
                gaps = check(a.owed, a.confirmed_on, a.statements, a.payments, day)
                sig = (gaps[0].kind, gaps[0].stage) if gaps else ()
                prev = last.get(a.claim)
                if sig:
                    due = prev is None or not prev[1] or prev[1] != sig or (day - prev[0]).days >= repeat_days
                else:
                    due = prev is not None and bool(prev[1])
                if not due:
                    continue
                rounds[a.claim] = rounds.get(a.claim, 0) + 1
                last[a.claim] = (day, sig)
                added += 1
                payload = {"claim": a.claim, "due_on": day.isoformat(), "kind": sig[0] if sig else "",
                           "stage": sig[1] if sig else None, "round": rounds[a.claim]}  # fmt: skip
                s.add(
                    m.Event(
                        source_file_id=sf.id, event_type=EVENT_TYPE, isa13=day.strftime("%Y%m%d"),
                        gs06=str(added)[:9], st02=str(rounds[a.claim]), seq_in_file=added, known_at=at,
                        payload=json.dumps(payload, sort_keys=True),
                    )
                )  # fmt: skip
            day += timedelta(days=every_days)
        s.commit()
    return SweepResult(added, False)
