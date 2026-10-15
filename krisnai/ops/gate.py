"""The load gate: nothing downstream runs on a load that does not reconcile.

Failed files stop the run unless the operator allows them; the existing G0 reconciliation (claim and remit totals,
payment totals, remit-to-claim match rate) must pass as of the run date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.engine import Engine

from krisnai.agents.a15_lite.config import A15Config
from krisnai.agents.a15_lite.g0 import run_g0


@dataclass
class GateResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)


def check_gate(
    engine: Engine, tenant_id: int, as_of: date, files_failed: int, allow_failed: bool = False,
    cfg: A15Config | None = None,
) -> GateResult:
    reasons: list[str] = []
    if files_failed and not allow_failed:
        reasons.append(f"{files_failed} file(s) failed to load (see rejected/); fix them or pass --allow-failed")
    g0 = run_g0(engine, tenant_id, as_of, cfg)
    for c in g0.checks:
        if not c["passed"]:
            reasons.append(
                f"{c['name']}: {c['mismatches']} of {c['items']} off by up to {c['max_difference']} "
                f"(tolerance {c['tolerance']})"
            )
    checks = [{k: v if isinstance(v, (int, bool, str)) else str(v) for k, v in c.items()} for c in g0.checks]
    return GateResult(not reasons, reasons, checks)
