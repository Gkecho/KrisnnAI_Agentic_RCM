"""The sweeper: turns "this payment has an open reconciliation gap" into an event the engine can act on.

On each sweep date every known payment is checked as of that date. A payment with an actionable gap gets a
`payment.reconcile_due` event when it first shows one, again when its set of gaps changes, and every `repeat_days`
while it stays open; when a flagged payment comes clean one closing event (no gaps) lets the agent close its card.
A bank deposit that no payment explains gets one `deposit.unidentified` event. Events are append-only and carry
`known_at`; running the same sweep twice adds nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from hashlib import sha256

from sqlalchemy import select

import krisnnai.model as m
from krisnnai.agents.a11_cash import config
from krisnnai.agents.a11_cash.ledger import Ledger
from krisnnai.agents.a11_cash.rules import reconcile
from krisnnai.model import tenant_session

PAYMENT_EVENT = "payment.reconcile_due"
DEPOSIT_EVENT = "deposit.unidentified"


@dataclass(frozen=True)
class SweepResult:
    events: int
    skipped: bool  # True when this exact sweep was already recorded


def sweep(engine, tenant_id: int, start: date, end: date, every_days: int = 7, repeat_days: int = config.REPEAT_DAYS):
    digest = sha256(f"a11sweep|{tenant_id}|{start}|{end}|{every_days}|{repeat_days}".encode()).hexdigest()
    with tenant_session(engine, tenant_id) as s:
        if s.scalar(select(m.SourceFile.id).where(m.SourceFile.file_sha256 == digest)) is not None:
            return SweepResult(0, True)
        ledger = Ledger(s)
        last: dict[str, tuple[date, tuple[str, ...]]] = {}
        rounds: dict[str, int] = {}
        raised_deposits: set[str] = set()
        for et, payload in s.execute(
            select(m.Event.event_type, m.Event.payload).where(m.Event.event_type.in_((PAYMENT_EVENT, DEPOSIT_EVENT)))
        ):
            p = json.loads(payload)
            if et == DEPOSIT_EVENT:
                raised_deposits.add(p["deposit_ref"])
                continue
            day, kinds = date.fromisoformat(p["due_on"]), tuple(p["gaps"])
            if p["trace"] not in last or day >= last[p["trace"]][0]:
                last[p["trace"]] = (day, kinds)
            rounds[p["trace"]] = rounds.get(p["trace"], 0) + 1

        sf = m.SourceFile(
            file_name=f"a11sweep_{start}_{end}", file_sha256=digest, file_type="sweep", byte_size=0, status="loaded"
        )
        s.add(sf)
        s.flush()
        added = 0
        day = start
        while day <= end:
            at = datetime.combine(day, time.min)
            for v in ledger.payments:
                p = v.payment
                if v.known_on > day or (day - p.paid_on).days < config.POST_DUE_DAYS:
                    continue
                gaps = [
                    g for g in reconcile(
                        p, v.claims_paid, ledger.candidates(p), ledger.postings_for(p), day, ledger.rivals(p)
                    )
                    if g.actionable
                ]  # fmt: skip
                kinds = tuple(sorted({g.kind for g in gaps}))
                prev = last.get(p.trace)
                if kinds:
                    due = prev is None or not prev[1] or prev[1] != kinds or (day - prev[0]).days >= repeat_days
                else:
                    due = prev is not None and bool(prev[1])
                if not due:
                    continue
                rounds[p.trace] = rounds.get(p.trace, 0) + 1
                last[p.trace] = (day, kinds)
                payload = {"trace": p.trace, "payer": p.payer, "paid_on": p.paid_on.isoformat(),
                           "due_on": day.isoformat(), "gaps": list(kinds), "round": rounds[p.trace]}  # fmt: skip
                added += 1
                s.add(
                    m.Event(
                        source_file_id=sf.id, event_type=PAYMENT_EVENT, isa13=day.strftime("%Y%m%d"),
                        gs06=p.trace[:9], st02=str(rounds[p.trace]), seq_in_file=added, known_at=at,
                        payload=json.dumps(payload, sort_keys=True),
                    )
                )  # fmt: skip
            for d in ledger.deposits:
                if d.ref in raised_deposits or (day - d.deposited_on).days < config.UNIDENTIFIED_AFTER_DAYS:
                    continue
                if not ledger.is_unidentified(d):
                    continue
                raised_deposits.add(d.ref)
                added += 1
                payload = {"deposit_ref": d.ref, "due_on": day.isoformat(), "amount": str(d.amount)}
                s.add(
                    m.Event(
                        source_file_id=sf.id, event_type=DEPOSIT_EVENT, isa13=day.strftime("%Y%m%d"),
                        gs06=d.ref[:9], st02="1", seq_in_file=added, known_at=at,
                        payload=json.dumps(payload, sort_keys=True),
                    )
                )  # fmt: skip
            day += timedelta(days=every_days)
        s.commit()
    return SweepResult(added, False)
