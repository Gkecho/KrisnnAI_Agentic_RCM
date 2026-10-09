"""G0 reconciliation: do the loaded rows add up to the totals the source files stated?

If any check is off by more than the tolerance the report is not produced: a leakage figure built on data that does
not reconcile would be wrong. Read-only.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine import Engine

import krisnai.model as m
from krisnai.agents.a15_lite.config import A15Config
from krisnai.model import tenant_session

ZERO = Decimal(0)


class G0Error(Exception):
    def __init__(self, result: G0Result):
        self.result = result
        bad = "; ".join(
            f"{c['name']}: {c['mismatches']} of {c['items']} off (max {c['max_difference']})"
            for c in result.checks
            if not c["passed"]
        )
        super().__init__(f"G0 reconciliation failed - {bad}")


@dataclass
class G0Result:
    tenant_id: int
    as_of: date
    checks: list[dict] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c["passed"] for c in self.checks)

    def to_dict(self) -> dict:
        return {"tenant_id": self.tenant_id, "as_of": self.as_of, "passed": self.passed, "checks": self.checks}


def _check(name: str, description: str, pairs: list[tuple[Decimal, Decimal]], tolerance: Decimal) -> dict:
    diffs = [abs(a - b) for a, b in pairs]
    bad = [d for d in diffs if d > tolerance]
    return {
        "name": name,
        "description": description,
        "items": len(pairs),
        "mismatches": len(bad),
        "max_difference": max(diffs, default=ZERO),
        "tolerance": tolerance,
        "passed": not bad,
    }


def run_g0(engine: Engine, tenant_id: int, as_of: date, cfg: A15Config | None = None) -> G0Result:
    cfg = cfg or A15Config()
    cutoff = datetime.combine(as_of, time.max)
    result = G0Result(tenant_id, as_of)
    with tenant_session(engine, tenant_id) as s:
        known = {e for (e,) in s.execute(select(m.Event.id).where(m.Event.known_at <= cutoff))}

        claims = {c.id: c.total_charge for c in s.scalars(select(m.Claim)) if c.event_id in known}
        line_charge: dict[int, Decimal] = defaultdict(Decimal)
        for cl in s.scalars(select(m.ClaimLine)):
            if cl.claim_id in claims:
                line_charge[cl.claim_id] += cl.charge
        result.checks.append(
            _check(
                "claim_charge",
                "claim total (CLM02) = sum of its service lines (SV102)",
                [(claims[i], line_charge[i]) for i in claims],
                cfg.g0_tolerance,
            )
        )

        remits = [r for r in s.scalars(select(m.Remit)) if r.event_id in known]
        rl_charge: dict[int, Decimal] = defaultdict(Decimal)
        rl_paid: dict[int, Decimal] = defaultdict(Decimal)
        ids = {r.id for r in remits}
        for ln in s.scalars(select(m.RemitLine)):
            if ln.remit_id in ids:
                rl_charge[ln.remit_id] += ln.charge
                rl_paid[ln.remit_id] += ln.paid
        result.checks.append(
            _check(
                "remit_charge",
                "remit billed total (CLP03) = sum of its service lines (SVC02)",
                [(r.total_charge, rl_charge[r.id]) for r in remits],
                cfg.g0_tolerance,
            )
        )
        result.checks.append(
            _check(
                "remit_paid",
                "remit payment (CLP04) = sum of its service lines (SVC03)",
                [(r.total_paid, rl_paid[r.id]) for r in remits],
                cfg.g0_tolerance,
            )
        )

        paid_by_payment: dict[int, Decimal] = defaultdict(Decimal)
        for r in remits:
            paid_by_payment[r.payment_id] += r.total_paid
        plb: dict[int, Decimal] = defaultdict(Decimal)
        for p in s.scalars(select(m.PlbAdjustment)):
            plb[p.payment_id] += p.amount
        payments = [p for p in s.scalars(select(m.Payment)) if p.event_id in known]
        result.checks.append(
            _check(
                "payment_total",
                "payment (BPR02) = sum of its remits (CLP04) less provider-level adjustments (PLB)",
                [(p.payment_amount, paid_by_payment[p.id] - plb[p.id]) for p in payments],
                cfg.g0_tolerance,
            )
        )

        matched = sum(1 for r in remits if r.claim_id is not None)
        rate = Decimal(matched) / Decimal(len(remits)) if remits else Decimal(1)
        ok = rate >= cfg.g0_min_match_rate
        result.checks.append(
            {
                "name": "remit_match_rate",
                "description": "remits linked to a claim (run `krisnai match` first)",
                "items": len(remits),
                "mismatches": len(remits) - matched,
                "max_difference": Decimal(1) - rate,
                "tolerance": Decimal(1) - cfg.g0_min_match_rate,
                "passed": ok,
            }
        )
    return result


def require_g0(engine: Engine, tenant_id: int, as_of: date, cfg: A15Config | None = None) -> G0Result:
    result = run_g0(engine, tenant_id, as_of, cfg)
    if not result.passed:
        raise G0Error(result)
    return result
