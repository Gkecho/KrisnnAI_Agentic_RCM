"""Build the mock practice and run it.

    Synthea CSV -> book (837/835/999/277CA/271 + PM feeds, planted defects, answer keys) -> inbox
    -> fresh SQLite db -> `ops backfill` (load, match, gate, every agent) -> report.html

Everything lives under one folder that is wiped and rebuilt, so the demo is disposable and repeatable. Shadow mode
throughout: nothing is executed, sent or submitted.
"""

from __future__ import annotations

import csv
import os
import shutil
import stat
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai.model import Base
from krisnnai.ops.daily import RunReport, run_period
from krisnnai.synthea import build

SALT = "demo-salt"  # the demo tenant's patient-hash salt; `ops daily` on this db needs env DEMO_SALT=demo-salt
LOOKBACK = 547
PLANT_DAYS = 56  # planted payer-wide problems start this long before as-of: inside A9's and A15's windows


@dataclass
class DemoResult:
    root: Path
    engine: Engine
    tenant_id: int
    as_of: date
    book: Path
    report: RunReport
    planted: dict


def _engine(path: Path) -> Engine:
    eng = create_engine(f"sqlite:///{path}")

    @event.listens_for(eng, "connect")
    def _fk(conn, _rec):  # noqa: ANN001
        conn.execute("PRAGMA foreign_keys=ON")

    return eng


def _wipe(path: Path) -> None:
    """Remove a folder tree; Windows (and OneDrive) can hold files briefly, so retry and clear read-only flags."""

    def _onerror(func, p, _exc):  # noqa: ANN001
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass

    for _ in range(5):
        shutil.rmtree(path, onerror=_onerror)
        if not path.exists():
            return
        time.sleep(1)
    raise SystemExit(f"could not remove {path}; close anything using it (an open report, a db browser) and run again")


def _pick_targets(book: Path) -> tuple[tuple[str, str], tuple[str, str]]:
    """The two most-billed (payer, CPT) pairs on different payers: one gets a rate cut, one a denial pattern."""
    counts: Counter = Counter()
    with (book / "visits.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            counts[(r["payer_id"], r["cpt"])] += 1
    ranked = [k for k, _ in counts.most_common()]
    if len(ranked) < 2:
        raise SystemExit("the book has fewer than two payer + CPT pairs; cannot plant the payer-wide problems")
    first = ranked[0]
    second = next((k for k in ranked[1:] if k[0] != first[0]), ranked[1])
    return first, second


def make_demo(
    out_dir: Path, synthea_dir: Path, as_of: date, seed: int = 7, step_days: int = 28, log=print
) -> DemoResult:
    if not synthea_dir.exists():
        raise SystemExit(
            f"{synthea_dir} does not exist. Generate Synthea output first (`krisnnai synthea run --yes`, needs Docker) "
            "or point --synthea at an existing Synthea output folder."
        )
    if out_dir.exists():
        _wipe(out_dir)
    out_dir.mkdir(parents=True)
    scratch = out_dir / "_scan"
    log("1/4 building the mock practice from Synthea ...")
    build(synthea_dir, scratch, as_of, seed=seed, documentation=True)
    (rate_payer, rate_cpt), (den_payer, den_cpt) = _pick_targets(scratch)
    _wipe(scratch)
    plant_from = as_of - timedelta(days=PLANT_DAYS)
    book = out_dir / "inbox"
    # a small book can plant no authorization defect by chance (a handful of claims need one): try a few seeds so the
    # demo always has something for A2 to find
    for attempt in range(8):
        if book.exists():
            _wipe(book)
        info = build(
            synthea_dir, book, as_of, seed=seed + attempt, documentation=True, eligibility=True, authorization=True,
            cash=True, enrollment=True, patient=True, coding=True,
            rate_cuts=[f"{rate_payer}:{rate_cpt}:{plant_from.isoformat()}:30"],
            denial_patterns=[f"{den_payer}:{den_cpt}:50:0.6:{plant_from.isoformat()}"],
        )
        with (book / "auth_truth.csv").open(encoding="utf-8") as f:
            if sum(1 for _ in f) - 1 >= 3:
                break
    planted = {
        "rate_cut": {"payer": rate_payer, "cpt": rate_cpt, "from": plant_from.isoformat(), "percent": 30},
        "denial_pattern": {
            "payer": den_payer, "cpt": den_cpt, "carc": "50", "rate": 0.6, "from": plant_from.isoformat(),
        },
        "claims_billed": info.get("claims_billed"),
    }
    # the answer keys stay beside the data, not in the inbox (they are not feeds)
    truth = out_dir / "truth"
    truth.mkdir()
    for p in list(book.glob("*truth*.csv")):
        shutil.move(str(p), str(truth / p.name))

    log("2/4 creating the database and tenant ...")
    engine = _engine(out_dir / "demo.sqlite")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        tenant = m.Tenant(name="demo", patient_salt_key="DEMO_SALT")
        s.add(tenant)
        s.commit()
        tenant_id = tenant.tenant_id

    log("3/4 loading and running all fifteen agents (shadow mode) ...")
    report = run_period(
        engine, tenant_id, SALT, as_of, inbox=book, archive=out_dir / "archive", mode="backfill",
        start=as_of - timedelta(days=LOOKBACK), step_days=step_days, go_live=as_of - timedelta(days=28),
    )
    if report.status != "ok":
        raise SystemExit("the demo run did not finish ok: " + "; ".join(report.reasons))
    log("4/4 writing the report ...")
    from krisnnai.demo.report import write_report

    write_report(engine, tenant_id, out_dir, as_of, planted=planted, run=report)
    from krisnnai.demo.export import write_ui_data

    write_ui_data(engine, tenant_id, out_dir, as_of, planted=planted, run=report)
    return DemoResult(out_dir, engine, tenant_id, as_of, out_dir / "archive" / as_of.isoformat(), report, planted)
