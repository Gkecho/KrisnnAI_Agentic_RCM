"""Where a flagged slice's dollars went: each shortfall line is explained by the A15-lite finding on its claim,
then tagged with the upstream agents that flagged the claim before it was billed.

Attribution by key match to leaks already detected, not a causal proof. A shortfall nothing detected explains is
reported as "unexplained", never guessed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from krisnnai.agents.a15_investigator.variance import Slice
from krisnnai.agents.a15_lite import config as lite
from krisnnai.agents.a15_lite.detect import Finding

UNEXPLAINED = "unexplained"
UNDERPAID = "underpayment"
NOT_SEEN = "none"  # no upstream agent flagged the claim before it was billed
ZERO = Decimal(0)
CENT = Decimal("0.01")


@dataclass
class Cause:
    name: str  # denial:<category>, underpayment, unexplained_adjustment, unexplained
    dollars: Decimal = ZERO
    lines: int = 0
    carcs: dict[str, int] = field(default_factory=dict)
    claims: set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        return {"cause": self.name, "dollars": str(self.dollars.quantize(CENT)), "lines": self.lines,
                "carcs": dict(sorted(self.carcs.items())), "claims": len(self.claims)}  # fmt: skip


def _cause_of(claim: str, line_no: int, by_claim: dict[str, list[Finding]]) -> tuple[str, str]:
    """(cause name, CARC) for one shortfall line: an underpayment on that line, a denial, an unexplained adjustment."""
    found = by_claim.get(claim, [])
    for f in found:
        if f.type == lite.UNDERPAYMENT and f.line_no == line_no:
            return UNDERPAID, f.carc
    for f in found:
        if f.type == lite.DENIAL:
            return f"denial:{f.category}", f.carc
        if f.type == lite.TIMELY_FILING:
            return "denial:timely_filing", f.carc
    for f in found:
        if f.type == lite.UNEXPLAINED_ADJUSTMENT:
            return "unexplained_adjustment", f.carc
    return UNEXPLAINED, ""


def explain(slc: Slice, findings: list[Finding], flags: dict[str, set[str]]) -> dict:
    """The cause table and the upstream table for one slice; plain data, ready for an event payload."""
    by_claim: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        if f.claim:
            by_claim[f.claim].append(f)
    causes: dict[str, Cause] = {}
    upstream: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for x in slc.shortfall_lines:
        gap = x.expected - x.actual
        name, carc = _cause_of(x.claim_sid, x.line.line_number, by_claim)
        c = causes.setdefault(name, Cause(name))
        c.dollars += gap
        c.lines += 1
        c.claims.add(x.claim_sid)
        if carc:
            c.carcs[carc] = c.carcs.get(carc, 0) + 1
        for agent in sorted(flags.get(x.claim_sid, ())) or [NOT_SEEN]:
            upstream[agent] += gap
    ordered = sorted(causes.values(), key=lambda c: (-c.dollars, c.name))
    return {
        "shortfall": str(sum((c.dollars for c in ordered), ZERO).quantize(CENT)),
        "causes": [c.to_dict() for c in ordered],
        "upstream": {k: str(v.quantize(CENT)) for k, v in sorted(upstream.items())},
    }
