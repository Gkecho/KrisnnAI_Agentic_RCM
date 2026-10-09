"""Match quality report: counts, match rates, which rule matched, and why the rest did not."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Level:
    """Match outcome for one kind of row (remit, remit line or 277CA)."""

    total: int = 0
    matched: int = 0
    newly_matched: int = 0  # linked by this run (0 on an idempotent re-run)
    by_method: Counter = field(default_factory=Counter)
    unmatched_reasons: Counter = field(default_factory=Counter)

    @property
    def rate(self) -> float:
        return self.matched / self.total if self.total else 1.0

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "matched": self.matched,
            "newly_matched": self.newly_matched,
            "rate": round(self.rate, 6),
            "by_method": dict(self.by_method),
            "unmatched_reasons": dict(self.unmatched_reasons),
        }


@dataclass
class PaymentCheck:
    payments: int = 0
    reconciled: int = 0
    mismatched: list[dict] = field(default_factory=list)  # payment id, BPR02, remits - PLB

    def to_dict(self) -> dict:
        return {"payments": self.payments, "reconciled": self.reconciled, "mismatched": self.mismatched}


@dataclass
class MatchReport:
    tenant_id: int
    as_of: str | None
    remits: Level = field(default_factory=Level)
    lines: Level = field(default_factory=Level)
    acks: Level = field(default_factory=Level)
    payments: PaymentCheck = field(default_factory=PaymentCheck)

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "as_of": self.as_of,
            "remits": self.remits.to_dict(),
            "remit_lines": self.lines.to_dict(),
            "acks_277ca": self.acks.to_dict(),
            "payments": self.payments.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_text(self) -> str:
        out = [f"Match report - tenant {self.tenant_id}" + (f", as of {self.as_of}" if self.as_of else "")]
        for name, lvl in (("remit -> claim", self.remits), ("remit line -> claim line", self.lines),
                          ("277CA -> claim", self.acks)):  # fmt: skip
            out.append(f"{name}: {lvl.matched}/{lvl.total} matched ({lvl.rate:.2%}), {lvl.newly_matched} new this run")
            for method, n in lvl.by_method.most_common():
                out.append(f"    matched by {method}: {n}")
            for reason, n in lvl.unmatched_reasons.most_common():
                out.append(f"    unmatched {reason}: {n}")
        p = self.payments
        out.append(f"remit -> payment: {p.reconciled}/{p.payments} payments reconcile (BPR02 = sum CLP04 - PLB)")
        for row in p.mismatched[:10]:
            out.append(f"    payment {row['payment_id']}: BPR02 {row['payment_amount']} vs remits {row['remit_total']}")
        return "\n".join(out)


def money_sum(values) -> Decimal:
    return sum(values, Decimal("0"))
