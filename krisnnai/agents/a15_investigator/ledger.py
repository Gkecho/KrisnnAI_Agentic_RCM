"""The recovered-leakage ledger: of the leaks detected on one date, how many dollars were paid by a later date.

Detected against later paid only. "Worked" and "incremental" are not claimed: there is no work log and no control group,
so a claim the payer paid on its own after the detection date counts as paid here too.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from krisnnai.agents.a15_lite.detect import detect
from krisnnai.agents.a15_lite.snapshot import load_snapshot

ZERO = Decimal(0)
CENT = Decimal("0.01")


def ledger(engine, tenant_id: int, detected_on: date, through: date) -> dict:
    """Findings at `detected_on`, and what the remits received after it and by `through` paid on those claims."""
    if through < detected_on:
        raise ValueError("through must not be before the detection date")
    findings = detect(load_snapshot(engine, tenant_id, detected_on))
    later = load_snapshot(engine, tenant_id, through)
    paid_after: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for r in later.remits:
        claim = later.claims.get(r.claim_id) if r.claim_id is not None else None
        if claim is not None and r.status != "22" and r.payment_date > detected_on:
            paid_after[claim.sid] += r.total_paid
    rows: dict[tuple[str, str], dict] = {}
    budget = dict(paid_after)  # one claim's later payment is counted once across its findings
    for f in sorted(findings, key=lambda f: (f.claim, f.type, f.line_no or 0)):
        row = rows.setdefault((f.type, f.status), {"type": f.type, "status": f.status, "detected": 0,
                                                   "detected_amount": ZERO, "recovered": 0,
                                                   "recovered_amount": ZERO})  # fmt: skip
        row["detected"] += 1
        row["detected_amount"] += f.expected_amount
        got = min(f.expected_amount, budget.get(f.claim, ZERO)) if f.claim else ZERO
        if got > 0:
            budget[f.claim] -= got
            row["recovered"] += 1
            row["recovered_amount"] += got
    out = sorted(rows.values(), key=lambda r: (r["type"], r["status"]))
    det = sum((r["detected_amount"] for r in out), ZERO)
    rec = sum((r["recovered_amount"] for r in out), ZERO)
    return {"detected_on": detected_on.isoformat(), "through": through.isoformat(), "rows": out,
            "detected_amount": det.quantize(CENT), "recovered_amount": rec.quantize(CENT),
            "rate": (rec / det).quantize(Decimal("0.0001")) if det > 0 else None}  # fmt: skip


def format_ledger(x: dict) -> str:
    rate = f" ({x['rate']:.1%})" if x["rate"] is not None else ""
    head = (f"A15 ledger - detected {x['detected_on']}, paid by {x['through']}: detected {x['detected_amount']}, "
            f"later paid {x['recovered_amount']}{rate}")
    lines = [
        f"  {r['type']:24s}{r['status']:12s}{r['detected']:6d} {r['detected_amount']:>12}"
        f"{r['recovered']:6d} {r['recovered_amount']:>12}"
        for r in x["rows"]
    ]
    return "\n".join([head, *lines, "  (later payment on the same claim; not proof the work caused it)"])
