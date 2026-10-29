"""Score the findings against the synthetic ground truth: precision and recall per issue type."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from krisnnai.agents.a15_lite.config import UNDERPAYMENT
from krisnnai.agents.a15_lite.detect import Finding

TOLERANCE = Decimal("0.01")


@dataclass
class TypeScore:
    issue_type: str
    planted: int = 0
    found: int = 0
    matched: int = 0  # found and planted (same type and claim / visit)
    correct: int = 0  # matched, dollars within a cent, same recoverable / structural status

    @property
    def precision(self) -> float | None:
        return self.matched / self.found if self.found else None

    @property
    def recall(self) -> float | None:
        return self.matched / self.planted if self.planted else None

    @property
    def correct_recall(self) -> float | None:
        return self.correct / self.planted if self.planted else None


def _key(issue_type: str, claim: str, visit: str, line_no) -> tuple:
    return (issue_type, claim or visit, int(line_no) if issue_type == UNDERPAYMENT and line_no else None)


def evaluate(findings: list[Finding], ground_truth: Path) -> dict[str, TypeScore]:
    with open(ground_truth, newline="", encoding="utf8") as f:
        truth = {_key(g["issue_type"], g["claim_id"], g["visit_id"], g["line_no"]): g for g in csv.DictReader(f)}
    scores: dict[str, TypeScore] = defaultdict(lambda: TypeScore(""))
    for key in truth:
        sc = scores[key[0]]
        sc.issue_type = key[0]
        sc.planted += 1
    for fnd in findings:
        sc = scores[fnd.type]
        sc.issue_type = fnd.type
        sc.found += 1
        g = truth.get(fnd.key)
        if g is None:
            continue
        sc.matched += 1
        if abs(Decimal(g["expected_amount"]) - fnd.expected_amount) <= TOLERANCE and g["status"] == fnd.status:
            sc.correct += 1
    return dict(sorted(scores.items()))


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.1%}"


def format_scores(scores: dict[str, TypeScore]) -> str:
    rows = [f"{'type':24s}{'planted':>8s}{'found':>7s}{'precision':>11s}{'recall':>9s}{'right $ + status':>18s}"]
    for t, s in scores.items():
        rows.append(
            f"{t:24s}{s.planted:8d}{s.found:7d}{_pct(s.precision):>11s}{_pct(s.recall):>9s}"
            f"{_pct(s.correct_recall):>18s}"
        )
    planted = sum(s.planted for s in scores.values())
    correct = sum(s.correct for s in scores.values())
    overall = _pct(correct / planted if planted else None)
    rows.append(f"{'all planted issues':24s}{planted:8d}{'':7s}{'':11s}{'':9s}{overall:>18s}")
    return "\n".join(rows)
