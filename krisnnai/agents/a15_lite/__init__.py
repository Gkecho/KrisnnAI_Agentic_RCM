"""A15-lite: read-only revenue leakage diagnostic (M5). Detects, ranks and maps leaks; recovers nothing."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy.engine import Engine

from krisnnai.agents.a15_lite.config import A15Config
from krisnnai.agents.a15_lite.detect import Finding, detect
from krisnnai.agents.a15_lite.evaluate import TypeScore, evaluate, format_scores
from krisnnai.agents.a15_lite.g0 import G0Error, G0Result, require_g0, run_g0
from krisnnai.agents.a15_lite.report import build_report, write_json, write_xlsx
from krisnnai.agents.a15_lite.snapshot import load_snapshot
from krisnnai.metrics import compute_all


@dataclass
class A15Result:
    findings: list[Finding]
    report: dict
    json_path: Path
    xlsx_path: Path
    scores: dict[str, TypeScore] | None = None


def run_a15(
    engine: Engine,
    tenant_id: int,
    as_of: date,
    out_dir: Path,
    cfg: A15Config | None = None,
    ground_truth: Path | None = None,
) -> A15Result:
    """Reconcile (G0), detect, report. Raises G0Error before anything is written if the totals do not reconcile."""
    cfg = cfg or A15Config()
    g0 = require_g0(engine, tenant_id, as_of, cfg)
    findings = detect(load_snapshot(engine, tenant_id, as_of), cfg)
    report = build_report(tenant_id, as_of, findings, g0, compute_all(engine, tenant_id, as_of))
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path, xlsx_path = out_dir / "a15_lite.json", out_dir / "a15_lite.xlsx"
    write_json(report, json_path)
    write_xlsx(report, xlsx_path)
    scores = evaluate(findings, ground_truth) if ground_truth else None
    return A15Result(findings, report, json_path, xlsx_path, scores)


__all__ = [
    "A15Config",
    "A15Result",
    "Finding",
    "G0Error",
    "G0Result",
    "detect",
    "evaluate",
    "format_scores",
    "load_snapshot",
    "require_g0",
    "run_a15",
    "run_g0",
]
