"""The sweeper: turns "this claim is overdue" into an event, so the engine (which only runs on events) can act on it.

For each sweep date it appends one `ar.followup_due` event per open claim that has passed its payer's expected payment
date, and repeats every `repeat_days` while the claim stays open. Events are append-only and carry `known_at`, so a
replay sees exactly what a person would have seen that day. Running the same sweep twice adds nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256

from sqlalchemy import select

import krisnnai.model as m
from krisnnai.agents.a7_ar import timing
from krisnnai.model import tenant_session

EVENT_TYPE = "ar.followup_due"
REPEAT_DAYS = 14  # how often an unpaid claim comes back to the inbox; TBD at spec review


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool  # True when this exact sweep was already recorded


def sweep(engine, tenant_id: int, start: date, end: date, every_days: int = 7, repeat_days: int = REPEAT_DAYS):
    digest = sha256(f"sweep|{tenant_id}|{start}|{end}|{every_days}|{repeat_days}".encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        claims = s.execute(
            select(m.Claim.id, m.Claim.claim_submitter_id, m.Claim.payer_id, m.Claim.submitted_on, m.Event.known_at)
            .join(m.Event, m.Event.id == m.Claim.event_id)
            .where(m.Claim.frequency_code != "8", m.Claim.submitted_on.is_not(None))
            .order_by(m.Claim.id)
        ).all()
        first_remit: dict[int, datetime] = {}
        for cid, known in s.execute(
            select(m.Remit.claim_id, m.Event.known_at)
            .join(m.Event, m.Event.id == m.Remit.event_id)
            .where(m.Remit.claim_id.is_not(None))
        ):
            if cid not in first_remit or known < first_remit[cid]:
                first_remit[cid] = known
        last: dict[int, date] = {}  # claim id -> date of its latest follow-up event, from earlier sweeps too
        rounds: dict[int, int] = {}
        for payload in s.scalars(select(m.Event.payload).where(m.Event.event_type == EVENT_TYPE)):
            p = json.loads(payload)
            due = date.fromisoformat(p["due_on"])
            last[p["claim_id"]] = max(last.get(p["claim_id"], due), due)
            rounds[p["claim_id"]] = rounds.get(p["claim_id"], 0) + 1

        sf = m.SourceFile(
            file_name=f"sweep_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0, status="loaded"
        )
        s.add(sf)
        s.flush()
        expected_cache: dict[tuple[int, date], int] = {}
        added = 0
        day = start
        while day <= end:
            at = datetime.combine(day, time.min)
            for cid, sid, payer_id, submitted, known in claims:
                if known > at or (cid in first_remit and first_remit[cid] <= at):
                    continue  # not submitted yet, or already answered
                if (payer_id, day) not in expected_cache:
                    expected_cache[(payer_id, day)] = timing.expected_days(s, payer_id, at)[0]
                expected = expected_cache[(payer_id, day)]
                age = (day - submitted).days
                if age < expected or (cid in last and (day - last[cid]).days < repeat_days):
                    continue
                rounds[cid] = rounds.get(cid, 0) + 1
                last[cid] = day
                payload = {
                    "claim_id": cid, "claim": sid, "payer_id": payer_id, "due_on": day.isoformat(),
                    "age_days": age, "expected_days": expected, "round": rounds[cid],
                }  # fmt: skip
                s.add(
                    m.Event(
                        source_file_id=sf.id,
                        event_type=EVENT_TYPE,
                        isa13=day.strftime("%Y%m%d"),
                        gs06=str(cid),
                        st02=str(rounds[cid]),
                        seq_in_file=added + 1,
                        known_at=at,
                        payload=json.dumps(payload, sort_keys=True),
                    )
                )
                added += 1
            day += timedelta(days=every_days)
        s.commit()
    return SweepResult(added, False)
