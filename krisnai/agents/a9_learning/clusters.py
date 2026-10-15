"""Point-in-time claim outcomes and denial clusters: payer + CPT + CARC, with how often that payer denies that CPT.

Everything is computed from events known by `as_of`, so a replay sees what a manager would have seen that day.
A claim carrying several CPTs counts for each of them; a cluster that is just a shadow of a stronger one (same payer and
CARC, mostly the same claims) is dropped, so one defect gives one cluster.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.agents.a9_learning import config


@dataclass
class ClaimOutcome:
    claim_id: int
    sid: str
    payer: str
    cpts: frozenset[str]
    filed_on: date  # when the claim became known
    carcs: set[str] = field(default_factory=set)  # denial reasons seen on its remits (not patient share, not CARC 45)
    denied_on: date | None = None
    adjudicated: bool = False
    adjudicated_on: date | None = None  # first payment answer known


@dataclass
class Cluster:
    payer: str
    cpt: str
    carc: str
    denied_claims: set[int] = field(default_factory=set)  # claim ids
    n_adjudicated: int = 0
    denied_dates: list[date] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.payer}|{self.cpt}|{self.carc}"

    @property
    def n_denials(self) -> int:
        return len(self.denied_claims)

    @property
    def rate(self) -> Decimal:
        return Decimal(self.n_denials) / Decimal(self.n_adjudicated) if self.n_adjudicated else Decimal(0)

    @property
    def qualifies(self) -> bool:
        return self.n_denials >= config.MIN_DENIALS and self.rate >= config.MIN_RATE


def outcomes(session: Session, as_of: date) -> list[ClaimOutcome]:
    """One outcome per claim known by the end of `as_of`: what was filed, what the payer said."""
    end = datetime.combine(as_of, time.max)
    payer_code = {p.id: p.payer_id_code for p in session.scalars(select(m.Payer))}
    known = {e.id: e.known_at for e in session.scalars(select(m.Event).where(m.Event.known_at <= end))}
    pay_payer = {p.id: p.payer_id for p in session.scalars(select(m.Payment))}
    cpts: dict[int, set[str]] = defaultdict(set)
    for claim_id, cpt in session.execute(select(m.ClaimLine.claim_id, m.ClaimLine.cpt)):
        cpts[claim_id].add(cpt)
    out: dict[int, ClaimOutcome] = {}
    for c in session.scalars(select(m.Claim)):
        if c.event_id in known and c.id in cpts:
            payer = payer_code.get(c.payer_id, "")
            out[c.id] = ClaimOutcome(c.id, c.claim_submitter_id, payer, frozenset(cpts[c.id]), known[c.event_id].date())

    remits = [r for r in session.scalars(select(m.Remit)) if r.event_id in known and r.claim_id in out]
    ids = {r.id for r in remits}
    adj: dict[int, list[m.Adjustment]] = defaultdict(list)
    for a in session.scalars(select(m.Adjustment)):
        if a.remit_id in ids:
            adj[a.remit_id].append(a)
    lines: dict[int, list[m.RemitLine]] = defaultdict(list)
    for ln in session.scalars(select(m.RemitLine)):
        if ln.remit_id in ids:
            lines[ln.remit_id].append(ln)

    def odd(items) -> set[str]:
        return {a.reason_code for a in items if a.group_code != "PR" and a.reason_code != config.CONTRACTUAL}

    for r in sorted(remits, key=lambda r: known[r.event_id]):
        o = out[r.claim_id]
        if r.claim_status_code == "22":
            continue
        o.adjudicated = True
        o.adjudicated_on = o.adjudicated_on or known[r.event_id].date()
        if r.claim_status_code == "4":
            carcs = odd(adj.get(r.id, []))
        else:
            by_line: dict[int | None, list[m.Adjustment]] = defaultdict(list)
            for a in adj.get(r.id, []):
                by_line[a.remit_line_id].append(a)
            carcs = set()
            for ln in lines.get(r.id, []):
                if ln.paid == 0:
                    carcs |= odd(by_line.get(ln.id, []))
        if carcs:
            o.carcs |= carcs
            o.denied_on = o.denied_on or known[r.event_id].date()
    return list(out.values())


def clusters_from(items: list[ClaimOutcome]) -> list[Cluster]:
    """Qualifying clusters, strongest first, shadows removed."""
    adjudicated: dict[tuple[str, str], int] = defaultdict(int)
    found: dict[tuple[str, str, str], Cluster] = {}
    for o in items:
        if not o.adjudicated:
            continue
        for cpt in o.cpts:
            adjudicated[(o.payer, cpt)] += 1
            for carc in o.carcs:
                c = found.setdefault((o.payer, cpt, carc), Cluster(o.payer, cpt, carc))
                c.denied_claims.add(o.claim_id)
                if o.denied_on:
                    c.denied_dates.append(o.denied_on)
    for c in found.values():
        c.n_adjudicated = adjudicated[(c.payer, c.cpt)]
    ranked = sorted((c for c in found.values() if c.qualifies), key=lambda c: (-c.rate, -c.n_denials, c.key))
    kept: list[Cluster] = []
    for c in ranked:
        shadow = any(
            k.payer == c.payer and k.carc == c.carc
            and Decimal(len(c.denied_claims & k.denied_claims)) / Decimal(c.n_denials) >= config.EXPLAINED_OVERLAP
            for k in kept
        )  # fmt: skip
        if not shadow:
            kept.append(c)
    return kept


def in_window(items: list[ClaimOutcome], as_of: date) -> list[ClaimOutcome]:
    """Claims the payer answered in the last WINDOW_DAYS: a recent change is not diluted by years of old history."""
    since = as_of - timedelta(days=config.WINDOW_DAYS)
    return [o for o in items if o.adjudicated_on is not None and o.adjudicated_on >= since]


def clusters(session: Session, as_of: date) -> list[Cluster]:
    return clusters_from(in_window(outcomes(session, as_of), as_of))
