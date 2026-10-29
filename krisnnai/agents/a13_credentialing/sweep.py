"""The sweeper: turns "this enrollment or screening has an open gap" into an event the engine can act on.

On each sweep date every provider + payer pair and every provider is checked as of that date. A pair or provider with a
gap gets an event when it first shows one, again when its set of gaps changes, and every `repeat_days` while it stays
open; when a flagged one comes clean one closing event (no gaps) lets the agent close its card. Events are append-only
and carry `known_at`; running the same sweep twice adds nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256

from sqlalchemy import select

import krisnnai.model as m
from krisnnai.agents.a13_credentialing import config
from krisnnai.agents.a13_credentialing.data import Book
from krisnnai.agents.a13_credentialing.rules import check_enrollment, check_screening, latest_known
from krisnnai.model import tenant_session

ENROLLMENT_EVENT = "enrollment.check"
SCREENING_EVENT = "provider.screening_check"


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool  # True when this exact sweep was already recorded


def sweep(engine, tenant_id: int, start: date, end: date, every_days: int = 7, repeat_days: int = config.REPEAT_DAYS):
    digest = sha256(f"a13sweep|{tenant_id}|{start}|{end}|{every_days}|{repeat_days}".encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        book = Book(s)
        last: dict[str, tuple[date, tuple[str, ...], int]] = {}
        rounds: dict[str, int] = {}
        for payload in s.scalars(
            select(m.Event.payload).where(m.Event.event_type.in_((ENROLLMENT_EVENT, SCREENING_EVENT)))
        ):
            p = json.loads(payload)
            day, kinds = date.fromisoformat(p["due_on"]), tuple(p["gaps"])
            if p["key"] not in last or day >= last[p["key"]][0]:
                last[p["key"]] = (day, kinds, p.get("n", 0))
            rounds[p["key"]] = rounds.get(p["key"], 0) + 1

        sf = m.SourceFile(
            file_name=f"a13sweep_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0, status="loaded"
        )
        s.add(sf)
        s.flush()
        added = 0

        def raise_event(
            event_type: str, key: str, payload: dict, day: date, kinds: tuple[str, ...], n: int
        ) -> None:
            nonlocal added
            rounds[key] = rounds.get(key, 0) + 1
            last[key] = (day, kinds, n)
            added += 1
            payload = {**payload, "key": key, "due_on": day.isoformat(), "gaps": list(kinds), "round": rounds[key],
                       "n": n}  # fmt: skip
            s.add(
                m.Event(
                    source_file_id=sf.id, event_type=event_type, isa13=day.strftime("%Y%m%d"),
                    gs06=str(added)[:9], st02=str(rounds[key]), seq_in_file=added,
                    known_at=datetime.combine(day, time.min), payload=json.dumps(payload, sort_keys=True),
                )
            )  # fmt: skip

        def due(key: str, day: date, kinds: tuple[str, ...], n: int) -> bool:
            """New gaps, changed gaps, more (or fewer) services at risk, or the repeat interval; or a closing event."""
            prev = last.get(key)
            if kinds:
                return (
                    prev is None or not prev[1] or prev[1] != kinds or prev[2] != n
                    or (day - prev[0]).days >= repeat_days
                )
            return prev is not None and bool(prev[1])

        day = start
        while day <= end:
            for pair in book.pairs:
                npi, payer = book.providers[pair[0]], book.payers[pair[1]]
                seen = [x for x in book.unpriced_services(pair) if x.when <= day]
                gaps = check_enrollment(latest_known(book.enrollments.get(pair, []), day), seen, day)
                kinds = tuple(sorted({g.kind for g in gaps}))
                n = sum(1 for x in seen if (day - x.when).days < config.SERVICE_WINDOW_DAYS)
                key = f"{npi}|{payer}"
                if due(key, day, kinds, n if kinds else 0):
                    raise_event(
                        ENROLLMENT_EVENT, key, {"kind": "enrollment", "npi": npi, "payer": payer}, day, kinds,
                        n if kinds else 0,
                    )
            for provider_id in book.screened:
                npi = book.providers[provider_id]
                result, when = book.latest_screening(provider_id, day)
                kinds = tuple(sorted({g.kind for g in check_screening(result, when, day)}))
                if due(npi, day, kinds, 0):
                    raise_event(SCREENING_EVENT, npi, {"kind": "screening", "npi": npi}, day, kinds, 0)
            day += timedelta(days=every_days)
        s.commit()
    return SweepResult(added, False)
