"""Read-only snapshot of one tenant's data as of a date, held in plain objects (rule 9: only data known by then)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.model import tenant_session

ZERO = Decimal("0")


@dataclass
class ClaimLine:
    line_number: int
    cpt: str
    modifier: str
    units: Decimal
    charge: Decimal
    service_date: date | None


@dataclass
class Claim:
    id: int
    sid: str  # CLM01
    payer: str  # payer id code
    provider: str  # NPI
    location: str  # place of service
    patient_ref_id: int
    service_date: date | None
    total_charge: Decimal
    lines: list[ClaimLine] = field(default_factory=list)


@dataclass
class RemitLine:
    id: int
    line_number: int
    cpt: str
    modifier: str
    units: Decimal
    paid: Decimal
    charge: Decimal
    service_date: date | None
    # (group, reason, amount); line-level CAS, or the remit's claim-level CAS when it has no line-level CAS at all
    adjustments: list[tuple[str, str, Decimal]] = field(default_factory=list)

    @property
    def patient_share(self) -> Decimal:
        return sum((a for g, _, a in self.adjustments if g == "PR"), ZERO)


@dataclass
class Remit:
    id: int
    claim_id: int | None
    payer: str
    payment_date: date
    status: str  # CLP02
    total_paid: Decimal
    lines: list[RemitLine] = field(default_factory=list)
    claim_adjustments: list[tuple[str, str, Decimal]] = field(default_factory=list)


@dataclass
class Visit:
    ref: str
    payer: str
    provider: str
    patient_ref_id: int
    service_date: date
    cpt: str
    units: Decimal


@dataclass
class Fee:
    payer: str
    cpt: str
    modifier: str
    allowed: Decimal
    effective: date
    end: date | None


@dataclass
class Snapshot:
    tenant_id: int
    as_of: date
    claims: dict[int, Claim]
    remits: list[Remit]
    rejected_claim_ids: set[int]
    visits: list[Visit]
    fees: list[Fee]
    # claims that already exist for a (payer, patient, service date, cpt): used to tell if a visit was billed
    billed_keys: set[tuple[str, int, date, str]]

    def first_remit(self) -> dict[int, Remit]:
        """The first adjudication of each matched claim; reversals (CLP02 22) are ignored."""
        first: dict[int, Remit] = {}
        for r in sorted(self.remits, key=lambda r: (r.payment_date, r.id)):
            if r.claim_id is not None and r.status != "22" and r.claim_id not in first:
                first[r.claim_id] = r
        return first


def load_snapshot(engine: Engine, tenant_id: int, as_of: date) -> Snapshot:
    cutoff = datetime.combine(as_of, time.max)
    with tenant_session(engine, tenant_id) as s:  # read only: nothing is added or committed
        payer = {p.id: p.payer_id_code for p in s.scalars(select(m.Payer))}
        provider = {p.id: p.npi for p in s.scalars(select(m.Provider))}

        known = {e.id for e in s.scalars(select(m.Event).where(m.Event.known_at <= cutoff))}
        events = {e.id: e for e in s.scalars(select(m.Event))}

        claims: dict[int, Claim] = {}
        claim_event: dict[int, m.Event] = {}
        for c in s.scalars(select(m.Claim).where(m.Claim.frequency_code != "8")):
            if c.event_id not in known:
                continue
            claims[c.id] = Claim(
                c.id,
                c.claim_submitter_id,
                payer[c.payer_id],
                provider[c.provider_id],
                c.place_of_service or "",
                c.patient_ref_id,
                c.service_date,
                c.total_charge,
            )
            claim_event[c.id] = events[c.event_id]
        for cl in s.scalars(select(m.ClaimLine).order_by(m.ClaimLine.claim_id, m.ClaimLine.line_number)):
            if cl.claim_id in claims:
                claims[cl.claim_id].lines.append(
                    ClaimLine(cl.line_number, cl.cpt, cl.modifier_1 or "", cl.units, cl.charge, cl.service_date)
                )

        pay = {p.id: p for p in s.scalars(select(m.Payment)) if p.event_id in known}
        remits: dict[int, Remit] = {}
        for r in s.scalars(select(m.Remit)):
            p = pay.get(r.payment_id)
            if p is None or r.event_id not in known:
                continue
            remits[r.id] = Remit(r.id, r.claim_id, payer[p.payer_id], p.payment_date, r.claim_status_code, r.total_paid)
        lines: dict[int, RemitLine] = {}
        for rl in s.scalars(select(m.RemitLine).order_by(m.RemitLine.remit_id, m.RemitLine.line_number)):
            if rl.remit_id in remits:
                line = RemitLine(
                    rl.id,
                    rl.line_number,
                    rl.cpt,
                    rl.modifier_1 or "",
                    rl.units or Decimal(1),
                    rl.paid,
                    rl.charge,
                    rl.service_date,
                )
                lines[rl.id] = line
                remits[rl.remit_id].lines.append(line)
        has_line_cas: set[int] = set()
        for a in s.scalars(select(m.Adjustment).order_by(m.Adjustment.remit_id, m.Adjustment.seq)):
            if a.remit_id not in remits:
                continue
            item = (a.group_code, a.reason_code, a.amount)
            if a.remit_line_id is not None:
                lines[a.remit_line_id].adjustments.append(item)
                has_line_cas.add(a.remit_id)
            else:
                remits[a.remit_id].claim_adjustments.append(item)
        for rid, r in remits.items():  # claim-level CAS stands in for line-level only when there is none
            if rid not in has_line_cas and r.claim_adjustments and len(r.lines) == 1:
                r.lines[0].adjustments = list(r.claim_adjustments)

        rejected: set[int] = set()
        for a in s.scalars(select(m.Ack277Ca).where(m.Ack277Ca.status_category.in_(("A3", "A4")))):
            if a.claim_id in claims and a.event_id in known:
                rejected.add(a.claim_id)
        by_txn = defaultdict(list)
        for cid, ev in claim_event.items():
            by_txn[(ev.gs06, ev.st02)].append(cid)
        for k in s.scalars(select(m.Ack999).where(m.Ack999.transaction_status == "R")):
            if k.event_id in known:
                rejected.update(by_txn.get((k.acked_gs06, k.acked_st02), []))

        visits = [
            Visit(
                v.visit_ref,
                payer[v.payer_id],
                provider[v.provider_id],
                v.patient_ref_id,
                v.service_date,
                v.cpt,
                v.units,
            )
            for v in s.scalars(select(m.Visit))
            if v.service_date <= as_of
        ]
        fees = [
            Fee(payer[f.payer_id], f.cpt, f.modifier, f.allowed_amount, f.effective_date, f.end_date)
            for f in s.scalars(select(m.FeeSchedule))
            if f.effective_date <= as_of
        ]
        billed = {
            (c.payer, c.patient_ref_id, ln.service_date or c.service_date, ln.cpt)
            for c in claims.values()
            for ln in c.lines
        }
    return Snapshot(tenant_id, as_of, claims, list(remits.values()), rejected, visits, fees, billed)
