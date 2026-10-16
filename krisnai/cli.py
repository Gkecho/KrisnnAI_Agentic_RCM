"""krisnai command line.

    krisnai init-db                          create tables (dev / SQLite; SQL Server uses Alembic)
    krisnai tenant-create NAME --salt-key K  register a tenant and print its id
    krisnai ingest PATH --tenant ID          load X12 files / fee schedule CSVs (idempotent)
    krisnai load-valley --tenant ID --valley-config FILE   load a sample of the Valley Wellness database
    krisnai metrics --tenant ID --as-of DATE [--kpi NAME] [--json]   compute KPIs as of a date
    krisnai a15 --tenant ID --as-of DATE --out DIR [--ground-truth CSV]   leakage diagnostic (read-only)
    krisnai a8 seed|replay --tenant ID                                    denial agent (shadow only)
    krisnai a5 seed|replay --tenant ID                                    claim prevention agent (shadow only)
    krisnai a10 replay|patterns --tenant ID                               underpayment agent (shadow only)
    krisnai a3 sweep|replay --tenant ID                                   documentation agent (shadow only)
    krisnai a1 sweep|replay --tenant ID                                   pre-visit clearance agent (shadow only)
    krisnai a9 sweep|replay|approve|reject|forward|attribution            denial learning agent (shadow only)
    krisnai a2 seed|sweep|replay --tenant ID                              authorization agent (shadow only)
    krisnai a11 sweep|replay --tenant ID                                  cash reconciliation agent (shadow only)
    krisnai a13 sweep|replay --tenant ID                                  credentialing agent (shadow only)
    krisnai stage1 [--out DIR] [--with-fhir]                              bots against local mock services + report
    krisnai fhir up|down|seed|pull                                        local FHIR server and feeds
    krisnai demo [--out DIR] [--synthea DIR]                              mock practice + report.html (shadow only)
    krisnai ops daily|backfill|status|bench --tenant ID                   inbox runner (shadow only)
    krisnai investigate sweep|replay|ledger --tenant ID                   revenue assurance investigator (shadow only)
    krisnai a12 sweep|replay --tenant ID                                  patient balance worklist (staff-facing)
    krisnai a4 replay|variance --tenant ID                                coding audit, suggestions only
    krisnai a7 sweep|replay|inbox --tenant ID                             AR follow-up agent (shadow only)
    krisnai a6 seed|replay --tenant ID                                    rejection handling agent (shadow only)
    krisnai tower --tenant ID --as-of DATE [--json]                       control tower snapshot (read-only)
    krisnai synthea run|build                                             Synthea patients -> billed claims + truth
    krisnai a14 sweep|replay --tenant ID                                  control tower agent (shadow only)
    krisnai match --tenant ID [--as-of ISO] [--json]       link remits to claims, print the match report

The patient-hash salt is read from the environment variable named by the tenant's salt key.
Use --db-url (or KRISNAI_DB_URL) for a non-SQL-Server database such as sqlite:///dev.db.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from krisnai.db import make_engine
from krisnai.ingest.loader import ingest_path
from krisnai.model import Base, Tenant


def _salt_for(engine, tenant_id: int) -> str:
    with Session(engine) as s:
        tenant = s.get(Tenant, tenant_id)
        if tenant is None:
            raise SystemExit(f"tenant {tenant_id} does not exist; run tenant-create first")
        key = tenant.patient_salt_key
    salt = os.environ.get(key)
    if not salt:
        raise SystemExit(f"set the environment variable {key} (this tenant's patient-hash salt)")
    return salt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="krisnai")
    parser.add_argument("--db-url", help="SQLAlchemy URL; default KRISNAI_DB_URL or SQL Server env vars")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="create all tables (dev only)")
    t = sub.add_parser("tenant-create")
    t.add_argument("name")
    t.add_argument("--salt-key", required=True, help="env var name that holds this tenant's salt")
    i = sub.add_parser("ingest")
    i.add_argument("path", type=Path)
    i.add_argument("--tenant", type=int, required=True)
    v = sub.add_parser("load-valley", help="load a sample from the (fabricated) Valley Wellness Postgres DB")
    v.add_argument("--tenant", type=int, required=True)
    v.add_argument("--valley-config", type=Path, required=True, help="KEY=VALUE file with PGHOST, PGDATABASE, ...")
    v.add_argument("--files", type=int, default=2, help="837P files to load (about 860 claims each)")
    v.add_argument("--max-remit-files", type=int, default=500)
    mt = sub.add_parser("match", help="claim/remit/payment matching and match quality report")
    mt.add_argument("--tenant", type=int, required=True)
    mt.add_argument("--as-of", type=datetime.fromisoformat, help="only use data known by this timestamp")
    mt.add_argument("--json", action="store_true", help="print the report as JSON")
    kp = sub.add_parser("metrics", help="compute KPIs (docs/metrics.md) as of a date; run match first")
    kp.add_argument("--tenant", type=int, required=True)
    kp.add_argument("--as-of", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    kp.add_argument("--kpi", help="one KPI name; default all")
    kp.add_argument("--json", action="store_true")
    a = sub.add_parser("a15", help="A15-lite revenue leakage diagnostic (read-only; run match first)")
    a.add_argument("--tenant", type=int, required=True)
    a.add_argument("--as-of", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a.add_argument("--out", type=Path, required=True, help="folder for a15_lite.json and a15_lite.xlsx")
    a.add_argument("--ground-truth", type=Path, help="synthetic ground_truth.csv to score the findings against")
    a.add_argument("--g0-tolerance", type=Decimal, default=Decimal("0.01"), help="largest accepted reconciliation gap")
    a8 = sub.add_parser("a8", help="A8 denial and appeal agent, shadow mode only")
    a8_sub = a8.add_subparsers(dest="a8_cmd", required=True)
    seed_help = "load the default CARC routing table for a tenant"
    replay_help = "replay A8 over the tenant's history in shadow mode and print the summary"
    for name, text in (("seed", seed_help), ("replay", replay_help)):
        a8_sub.add_parser(name, help=text).add_argument("--tenant", type=int, required=True)
    a10 = sub.add_parser("a10", help="A10 contract and underpayment agent, shadow mode only")
    a10_sub = a10.add_subparsers(dest="a10_cmd", required=True)
    a10_replay = "replay A10 over the tenant's payments in shadow mode and print the summary"
    a10_patterns = "list payer-wide short-payment patterns (one dispute each) from the replay"
    for name, text in (("replay", a10_replay), ("patterns", a10_patterns)):
        a10_sub.add_parser(name, help=text).add_argument("--tenant", type=int, required=True)
    a4 = sub.add_parser("a4", help="A4 coding integrity copilot (suggestions only), shadow mode only")
    a4_sub = a4.add_subparsers(dest="a4_cmd", required=True)
    a4_sub.add_parser("replay", help="replay A4 over the claims in shadow mode").add_argument(
        "--tenant", type=int, required=True
    )
    a4_sub.add_parser("variance", help="audit variance: billed vs documented E/M level").add_argument(
        "--tenant", type=int, required=True
    )
    a12 = sub.add_parser("a12", help="A12 patient engagement agent (staff-facing worklist), shadow mode only")
    a12_sub = a12.add_subparsers(dest="a12_cmd", required=True)
    a12_sweep = a12_sub.add_parser("sweep", help="raise a balance check event for each open patient balance item")
    a12_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a12_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a12_sweep.add_argument("--every-days", type=int, default=7)
    a12_replay = a12_sub.add_parser("replay", help="replay A12 over the events in shadow mode")
    a12_replay.add_argument("--as-of", type=date.fromisoformat, help="date for the collections KPI")
    for sp in (a12_sweep, a12_replay):
        sp.add_argument("--tenant", type=int, required=True)
    a13 = sub.add_parser("a13", help="A13 credentialing and enrollment agent, shadow mode only")
    a13_sub = a13.add_subparsers(dest="a13_cmd", required=True)
    a13_sweep = a13_sub.add_parser("sweep", help="raise enrollment and screening events for open gaps")
    a13_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a13_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a13_sweep.add_argument("--every-days", type=int, default=7)
    a13_replay = a13_sub.add_parser("replay", help="replay A13 over the events in shadow mode")
    for sp in (a13_sweep, a13_replay):
        sp.add_argument("--tenant", type=int, required=True)
    demo = sub.add_parser("demo", help="build a mock practice, run every agent in shadow mode, write report.html")
    demo.add_argument("--out", type=Path, default=Path("out/demo"), help="folder to (re)build; wiped first")
    demo.add_argument("--synthea", type=Path, default=Path("out/synthea"), help="Synthea output folder")
    demo.add_argument("--as-of", type=date.fromisoformat, default=date(2026, 10, 14), help="YYYY-MM-DD")
    demo.add_argument("--seed", type=int, default=7)
    st1 = sub.add_parser("stage1", help="run the bots against the local mock clearinghouse and portal, write a report")
    st1.add_argument("--out", type=Path, default=Path("out/stage1"))
    st1.add_argument("--synthea", type=Path, default=Path("out/synthea"))
    st1.add_argument("--as-of", type=date.fromisoformat, default=date(2026, 6, 30), help="YYYY-MM-DD")
    st1.add_argument("--seed", type=int, default=7)
    st1.add_argument("--limit", type=int, default=25, help="items per bot")
    st1.add_argument("--with-fhir", action="store_true", help="also run the FHIR round trip (Docker, ~2 GB images)")
    sd = sub.add_parser("stedi", help="Stedi sandbox: one eligibility check with a TEST key (needs STEDI_API_KEY)")
    sd.add_argument("--payer", default="60054", help="Stedi's documented Aetna mock payer id")
    sd.add_argument("--member", default="AETNA12345", help="the documented mock subscriber member id")
    sd.add_argument("--first", default="Jane")
    sd.add_argument("--last", default="Doe")
    sd.add_argument("--dob", default="20040404")
    sd.add_argument("--npi", default="1999999984", help="Stedi's mock provider NPI (must pass the check digit)")
    fh = sub.add_parser("fhir", help="local FHIR server: up, down, seed from feeds, pull feeds back out")
    fh_sub = fh.add_subparsers(dest="fhir_cmd", required=True)
    fh_up = fh_sub.add_parser("up", help="start the Microsoft FHIR server and SQL Server containers")
    fh_down = fh_sub.add_parser("down", help="stop and remove them (and their data)")
    fh_seed = fh_sub.add_parser("seed", help="load appointments.csv, visits.csv and notes.csv into the server")
    fh_pull = fh_sub.add_parser("pull", help="write those three feeds from the server into a folder")
    for sp in (fh_up, fh_down):
        sp.add_argument("--work", type=Path, default=Path("out/fhir"))
    for sp in (fh_seed, fh_pull):
        sp.add_argument("--url", default="http://localhost:8080")
    fh_seed.add_argument("--feeds", type=Path, required=True)
    fh_pull.add_argument("--out", type=Path, required=True)
    fh_pull.add_argument("--since", help="YYYY-MM-DD: only resources updated after this day")
    ops = sub.add_parser("ops", help="daily and backfill runs over an inbox folder (shadow mode throughout)")
    ops_sub = ops.add_subparsers(dest="ops_cmd", required=True)
    ops_daily = ops_sub.add_parser("daily", help="load the inbox, check it, advance every agent to --as-of")
    ops_back = ops_sub.add_parser("backfill", help="load history, then advance every agent over a date range")
    ops_status = ops_sub.add_parser("status", help="recent runs and the watermark")
    ops_bench = ops_sub.add_parser("bench", help="time a synthetic load and every agent step")
    for sp in (ops_daily, ops_back):
        sp.add_argument("--inbox", type=Path, required=True)
        sp.add_argument("--archive", type=Path, help="default: <inbox>/../archive")
        sp.add_argument("--allow-failed", action="store_true", help="continue past files that failed to load")
    ops_daily.add_argument("--as-of", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    ops_back.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    ops_back.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    ops_back.add_argument("--step-days", type=int, default=28)
    ops_back.add_argument("--go-live", type=date.fromisoformat, help="cards raised on/after this are reported as new")
    for sp in (ops_daily, ops_back, ops_status):
        sp.add_argument("--tenant", type=int, required=True)
    ops_bench.add_argument("--claims", type=int, default=2000)
    ops_bench.add_argument("--workdir", type=Path, help="scratch folder (default: a temp folder)")
    inv = sub.add_parser("investigate", help="A15 revenue assurance investigator, shadow mode only")
    inv_sub = inv.add_subparsers(dest="inv_cmd", required=True)
    inv_sweep = inv_sub.add_parser("sweep", help="raise variance events for slices whose realisation fell")
    inv_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    inv_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    inv_sweep.add_argument("--every-days", type=int, default=28)
    inv_replay = inv_sub.add_parser("replay", help="replay A15 over the events in shadow mode")
    inv_ledger = inv_sub.add_parser("ledger", help="leakage detected on one date vs paid by a later date")
    inv_ledger.add_argument("--detected-on", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    inv_ledger.add_argument("--through", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    for sp in (inv_sweep, inv_replay, inv_ledger):
        sp.add_argument("--tenant", type=int, required=True)
    a11 = sub.add_parser("a11", help="A11 cash reconciliation agent, shadow mode only")
    a11_sub = a11.add_subparsers(dest="a11_cmd", required=True)
    a11_sweep = a11_sub.add_parser("sweep", help="raise reconciliation events for payments and deposits")
    a11_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a11_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a11_sweep.add_argument("--every-days", type=int, default=7)
    a11_replay = a11_sub.add_parser("replay", help="replay A11 over the events in shadow mode")
    a11_replay.add_argument("--as-of", type=date.fromisoformat, help="date for the days-to-deposit / post KPIs")
    for sp in (a11_sweep, a11_replay):
        sp.add_argument("--tenant", type=int, required=True)
    a2 = sub.add_parser("a2", help="A2 authorization agent, shadow mode only")
    a2_sub = a2.add_subparsers(dest="a2_cmd", required=True)
    a2_seed = a2_sub.add_parser("seed", help="load the placeholder payer + CPT authorization requirements")
    a2_sweep = a2_sub.add_parser("sweep", help="raise the 7 d and 2 d authorization checkpoints in a window")
    a2_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a2_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a2_replay = a2_sub.add_parser("replay", help="replay A2 over the checkpoints in shadow mode")
    for sp in (a2_seed, a2_sweep, a2_replay):
        sp.add_argument("--tenant", type=int, required=True)
    a9 = sub.add_parser("a9", help="A9 denial prevention learning agent, shadow mode only")
    a9_sub = a9.add_subparsers(dest="a9_cmd", required=True)
    a9_sweep = a9_sub.add_parser("sweep", help="raise an event for each new recurring denial pattern")
    a9_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a9_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a9_sweep.add_argument("--every-days", type=int, default=30)
    a9_replay = a9_sub.add_parser("replay", help="replay A9 over the pattern events in shadow mode")
    a9_approve = a9_sub.add_parser("approve", help="a named person approves a proposed rule (A5 then uses it)")
    a9_reject = a9_sub.add_parser("reject", help="a named person rejects a proposed rule")
    a9_forward = a9_sub.add_parser("forward", help="forward test of each rule on claims filed after it was proposed")
    a9_attr = a9_sub.add_parser("attribution", help="which upstream agent had flagged each denial")
    for sp in (a9_approve, a9_reject):
        sp.add_argument("--rule", required=True, help="rule key, payer|cpt|carc")
        sp.add_argument("--by", required=True, help="the approver's name (stored with the decision)")
    for sp in (a9_forward, a9_attr):
        sp.add_argument("--as-of", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    for sp in (a9_sweep, a9_replay, a9_approve, a9_reject, a9_forward, a9_attr):
        sp.add_argument("--tenant", type=int, required=True)
    a1 = sub.add_parser("a1", help="A1 pre-visit clearance agent, shadow mode only")
    a1_sub = a1.add_subparsers(dest="a1_cmd", required=True)
    a1_sweep = a1_sub.add_parser("sweep", help="raise the 72 h and 24 h clearance checkpoints in a date window")
    a1_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a1_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a1_replay = a1_sub.add_parser("replay", help="replay A1 over the checkpoints in shadow mode")
    for sp in (a1_sweep, a1_replay):
        sp.add_argument("--tenant", type=int, required=True)
    a3 = sub.add_parser("a3", help="A3 documentation completeness agent, shadow mode only")
    a3_sub = a3.add_subparsers(dest="a3_cmd", required=True)
    a3_sweep = a3_sub.add_parser("sweep", help="raise a documentation check event for each visit with a gap")
    a3_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a3_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a3_sweep.add_argument("--every-days", type=int, default=7)
    a3_replay = a3_sub.add_parser("replay", help="replay A3 over the check events in shadow mode")
    a3_replay.add_argument("--as-of", type=date.fromisoformat, help="date for the charge-lag KPI")
    for sp in (a3_sweep, a3_replay):
        sp.add_argument("--tenant", type=int, required=True)
    a5 = sub.add_parser("a5", help="A5 claim prevention agent, shadow mode only")
    a5_sub = a5.add_subparsers(dest="a5_cmd", required=True)
    a5_seed = "load the placeholder NCCI and MUE rows for a tenant"
    a5_replay = "replay A5 over the tenant's claims in shadow mode and print the summary"
    for name, text in (("seed", a5_seed), ("replay", a5_replay)):
        a5_sub.add_parser(name, help=text).add_argument("--tenant", type=int, required=True)
    tw = sub.add_parser("tower", help="RCM control tower snapshot as of a date (read-only; run match first)")
    tw.add_argument("--tenant", type=int, required=True)
    tw.add_argument("--as-of", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    tw.add_argument("--backtest-weeks", type=int, default=8, help="past forecasts used to measure accuracy")
    tw.add_argument("--json", action="store_true")
    a14 = sub.add_parser("a14", help="A14 control tower agent, shadow mode only")
    a14_sub = a14.add_subparsers(dest="a14_cmd", required=True)
    a14_sweep = a14_sub.add_parser("sweep", help="raise one daily tower event per day")
    a14_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a14_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a14_replay = a14_sub.add_parser("replay", help="replay A14 over the daily events in shadow mode")
    for sp in (a14_sweep, a14_replay):
        sp.add_argument("--tenant", type=int, required=True)
    a6 = sub.add_parser("a6", help="A6 claim submission and response agent (rejections), shadow mode only")
    a6_sub = a6.add_subparsers(dest="a6_cmd", required=True)
    a6_seed = "load the placeholder rejection routing rows for a tenant"
    a6_replay = "replay A6 over the tenant's 999 / 277CA rejections in shadow mode and print the summary"
    for name, text in (("seed", a6_seed), ("replay", a6_replay)):
        a6_sub.add_parser(name, help=text).add_argument("--tenant", type=int, required=True)
    a7 = sub.add_parser("a7", help="A7 AR next-best-action agent, shadow mode only")
    a7_sub = a7.add_subparsers(dest="a7_cmd", required=True)
    a7_sweep = a7_sub.add_parser("sweep", help="raise a follow-up event for each overdue unpaid claim")
    a7_sweep.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a7_sweep.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    a7_sweep.add_argument("--every-days", type=int, default=7)
    a7_replay = a7_sub.add_parser("replay", help="replay A7 over the follow-up events in shadow mode")
    a7_inbox = a7_sub.add_parser("inbox", help="print the ranked cards (latest per claim)")
    a7_inbox.add_argument("--top", type=int, default=20)
    for sp in (a7_sweep, a7_replay, a7_inbox):
        sp.add_argument("--tenant", type=int, required=True)
    sy = sub.add_parser("synthea", help="generate Synthea patients and turn them into billed, paid, denied claims")
    sy_sub = sy.add_subparsers(dest="synthea_cmd", required=True)
    sy_run = sy_sub.add_parser("run", help="run Synthea in Docker (prints the plan; add --yes to run it)")
    sy_run.add_argument("--out", type=Path, default=Path("out/synthea"))
    sy_run.add_argument("--cache", type=Path, default=Path("out/synthea_cache"))
    sy_run.add_argument("--population", type=int, default=300)
    sy_run.add_argument("--seed", type=int, default=7)
    sy_run.add_argument("--state", default="Massachusetts")
    sy_run.add_argument("--yes", action="store_true", help="download the jar / pull the image and run")
    sy_build = sy_sub.add_parser("build", help="Synthea CSV folder -> X12 files + fee schedule + ground truth")
    sy_build.add_argument("--in", dest="src", type=Path, required=True, help="Synthea output (or its csv folder)")
    sy_build.add_argument("--out", type=Path, required=True)
    sy_build.add_argument("--as-of", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    sy_build.add_argument("--seed", type=int, default=7)
    sy_build.add_argument("--lookback-days", type=int, default=548, help="drop visits older than this")
    sy_build.add_argument("--documentation", action="store_true",
                          help="also write notes.csv, charges.csv, all visits and doc_truth.csv (planted defects)")
    sy_build.add_argument("--denial-pattern", action="append", default=[], metavar="PAYER:CPT:CARC:RATE:YYYY-MM-DD",
                          help="from a date a payer denies claims with a CPT at RATE (0-1): a planted recurring defect")
    sy_build.add_argument("--coding", action="store_true",
                          help="level elements on E/M notes and coding_truth.csv (needs --documentation)")
    sy_build.add_argument("--patient", action="store_true",
                          help="also write patient_payments.csv, statements.csv and patient_truth.csv")
    sy_build.add_argument("--enrollment", action="store_true",
                          help="also write enrollments.csv, screenings.csv and credentialing_truth.csv "
                               "(needs --documentation)")
    sy_build.add_argument("--cash", action="store_true",
                          help="also write bank_deposits.csv, postings.csv and cash_truth.csv (planted defects)")
    sy_build.add_argument("--authorization", action="store_true",
                          help="also write authorizations.csv and auth_truth.csv (needs --eligibility)")
    sy_build.add_argument("--eligibility", action="store_true",
                          help="also write appointments.csv, 271 files and elig_truth.csv (planted coverage problems)")
    sy_build.add_argument("--rate-cut", action="append", default=[], metavar="PAYER:CPT:YYYY-MM-DD:PCT",
                          help="a payer pays PCT%% less on a CPT from a date (repeatable); planted underpayment")
    args = parser.parse_args(argv)

    if args.cmd == "synthea":
        from krisnai.synthea import build as synthea_build
        from krisnai.synthea import runner

        if args.synthea_cmd == "run":
            p = runner.plan(args.out, args.cache, args.population, args.seed, args.state)
            print("download jar: " + " ".join(p.download))
            print("run synthea:  " + " ".join(p.docker))
            if not args.yes:
                print("nothing run (add --yes to download the jar, pull the image and run)")
                return 0
            return runner.run(p)
        report = synthea_build(
            args.src, args.out, args.as_of, args.seed, args.lookback_days, args.rate_cut, args.documentation,
            args.eligibility, args.denial_pattern,
            args.authorization, args.cash, args.enrollment, args.patient,
            args.coding,
        )
        print(json.dumps(report, indent=2))
        return 0

    if args.cmd == "ops" and args.ops_cmd == "bench":
        from krisnai.ops.bench import format_bench, run_bench

        print(format_bench(run_bench(args.claims, args.workdir)))
        return 0
    if args.cmd == "stage1":
        from krisnai.integrations.stage1 import run_stage1

        res = run_stage1(args.out, args.synthea, args.as_of, args.seed, args.with_fhir, args.limit)
        print(f"report: {res.report.resolve()}")
        print(json.dumps({k: v for k, v in res.summary.items() if k != "fhir"}, sort_keys=True))
        return 0
    if args.cmd == "stedi":
        from krisnai.integrations.clearinghouse.stedi import StediClient
        from krisnai.integrations.clearinghouse.x12_out import write_270

        today = date.today()
        sc = StediClient()
        x12 = write_270(args.payer, "PAYER", args.member, args.last, args.first, args.dob, today, "KRISNAISMOKE", 1, today,
                       args.npi)
        text = sc.check_eligibility(x12)
        print(f"mode: {sc.last_mode or 'not reported'}; response starts: {text[:60]!r}; {len(text)} characters of X12")
        return 0
    if args.cmd == "fhir":
        from krisnai.integrations.fhir import docker as fdocker
        from krisnai.integrations.fhir.client import FhirClient
        from krisnai.integrations.fhir.sync import pull as fhir_pull
        from krisnai.integrations.fhir.sync import seed as fhir_seed

        if args.fhir_cmd == "up":
            print(f"FHIR server ready at {fdocker.up(args.work)}")
        elif args.fhir_cmd == "down":
            fdocker.down(args.work)
            print("stopped")
        elif args.fhir_cmd == "seed":
            print(json.dumps(fhir_seed(FhirClient(args.url), args.feeds), sort_keys=True))
        else:
            print(json.dumps(fhir_pull(FhirClient(args.url), args.out, args.since), sort_keys=True))
        return 0
    if args.cmd == "demo":
        from krisnai.demo import make_demo

        res = make_demo(args.out, args.synthea, args.as_of, seed=args.seed)
        print(f"report: {(res.root / 'report.html').resolve()}")
        db = (res.root / "demo.sqlite").resolve()
        print(f"database: {db} (tenant {res.tenant_id}, salt env DEMO_SALT=demo-salt)")
        print(f"planted: {res.planted['rate_cut']['payer']} {res.planted['rate_cut']['cpt']} rate cut; "
              f"{res.planted['denial_pattern']['payer']} {res.planted['denial_pattern']['cpt']} denial pattern")
        print(f"ui data: {(res.root / 'ui_data.js').resolve()}")
        res.engine.dispose()  # release demo.sqlite so a re-run can replace the folder (Windows keeps open files)
        return 0

    engine = make_engine(args.db_url)
    if args.cmd == "init-db":
        Base.metadata.create_all(engine)
        print("tables created")
    elif args.cmd == "tenant-create":
        with Session(engine) as s:
            existing = s.scalars(select(Tenant).where(Tenant.name == args.name)).first()
            tenant = existing or Tenant(name=args.name, patient_salt_key=args.salt_key)
            s.add(tenant)
            s.commit()
            print(f"tenant {tenant.tenant_id} ({tenant.name})")
    elif args.cmd == "ingest":
        if not args.path.exists():
            raise SystemExit(f"{args.path} does not exist")
        results = ingest_path(engine, args.tenant, args.path, _salt_for(engine, args.tenant))
        for r in results:
            note = f" - {r.reason}" if r.reason else ""
            print(f"{r.status:8s} {r.file_type:14s} {Path(r.path).name}{note}")
        counts = {k: sum(1 for r in results if r.status == k) for k in ("loaded", "skipped", "failed")}
        print(f"{counts['loaded']} loaded, {counts['skipped']} skipped, {counts['failed']} failed")
        return 1 if counts["failed"] else 0
    elif args.cmd == "load-valley":
        from krisnai.ingest.valley import connect_readonly, load_valley

        salt = _salt_for(engine, args.tenant)
        conn = connect_readonly(args.valley_config)
        try:
            report = load_valley(engine, args.tenant, salt, conn, args.files, args.max_remit_files)
        finally:
            conn.close()
        print(f"{report.count('loaded')} loaded, {report.count('skipped')} skipped")
        for reason, n in report.skipped_rows.most_common():
            print(f"  skipped rows: {n} x {reason}")
    elif args.cmd == "match":
        from krisnai.match import run_matching

        report = run_matching(engine, args.tenant, args.as_of)
        print(report.to_json() if args.json else report.to_text())
    elif args.cmd == "metrics":
        from krisnai.metrics import compute, compute_all

        result = (
            {args.kpi: compute(engine, args.tenant, args.kpi, args.as_of)}
            if args.kpi
            else compute_all(engine, args.tenant, args.as_of)
        )
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            for kpi, rows in result.items():
                print(f"{kpi} (as of {args.as_of})")
                for row in rows:
                    print("   " + ", ".join(f"{k}={v}" for k, v in row.items()))
    elif args.cmd == "a15":
        from krisnai.agents.a15_lite import A15Config, G0Error, format_scores, run_a15

        try:
            res = run_a15(engine, args.tenant, args.as_of, args.out, A15Config(g0_tolerance=args.g0_tolerance),
                          args.ground_truth)  # fmt: skip
        except G0Error as e:
            print(f"STOPPED: {e}", file=sys.stderr)
            return 2
        s = res.report["summary"]
        print(f"{s['findings']} findings detected: recoverable {s['recoverable']}, structural {s['structural']}")
        for kind, v in s["by_type"].items():
            rec, struct = v["recoverable"], v["structural"]
            print(f"   {kind:24s} {v['findings']:4d}   recoverable {rec:>10}   structural {struct:>10}")
        print(f"wrote {res.json_path} and {res.xlsx_path}")
        if res.scores:
            print(format_scores(res.scores))
    elif args.cmd == "a8":
        from krisnai.agents.a8_denial import A8DenialAgent, format_summary, seed_defaults, summarize
        from krisnai.engine import replay
        from krisnai.model import tenant_session

        if args.a8_cmd == "seed":
            with tenant_session(engine, args.tenant) as s:
                added = seed_defaults(s)
                s.commit()
            print(f"{added} routing rows added")
        else:
            items = replay(engine, args.tenant, A8DenialAgent())
            print(f"replayed {len(items)} events (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant)))
    elif args.cmd == "a4":
        from krisnai.agents.a4_coding import A4CodingAgent, format_variance, variance
        from krisnai.engine import replay

        if args.a4_cmd == "replay":
            items = replay(engine, args.tenant, A4CodingAgent())
            print(f"replayed {len(items)} claims (shadow: nothing executed; suggestions only, a coder decides)")
        print(format_variance(variance(engine, args.tenant)))
    elif args.cmd == "a12":
        from krisnai.agents.a12_patient import A12PatientAgent, format_summary, summarize, sweep
        from krisnai.engine import replay

        if args.a12_cmd == "sweep":
            res = sweep(engine, args.tenant, args.start, args.end, args.every_days)
            added = f"{res.events} patient balance events added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        else:
            items = replay(engine, args.tenant, A12PatientAgent())
            print(f"replayed {len(items)} events (shadow: nothing executed; nothing sent to patients)")
            print(format_summary(summarize(engine, args.tenant, args.as_of)))
    elif args.cmd == "ops":
        from krisnai import ops as opsm
        from krisnai.ops.daily import format_report

        if args.ops_cmd == "status":
            wm = opsm.watermark(engine, args.tenant)
            print(f"watermark: {wm or 'none (no run has finished ok)'}")
            last = opsm.last_run(engine, args.tenant)
            if last is not None:
                print(f"last run: {last.mode} to {last.as_of}, {last.status}, gate {last.gate}, "
                      f"{last.files_loaded} files loaded, {last.events_added} events")
        else:
            salt = _salt_for(engine, args.tenant)
            archive = args.archive or args.inbox.parent / "archive"
            if args.ops_cmd == "daily":
                rep = opsm.run_period(engine, args.tenant, salt, args.as_of, inbox=args.inbox, archive=archive,
                                      mode="daily", allow_failed=args.allow_failed)  # fmt: skip
            else:
                rep = opsm.run_period(engine, args.tenant, salt, args.end, inbox=args.inbox, archive=archive,
                                      mode="backfill", start=args.start, step_days=args.step_days,
                                      go_live=args.go_live, allow_failed=args.allow_failed)  # fmt: skip
            print(format_report(rep))
            return 0 if rep.status == "ok" else 1
    elif args.cmd == "investigate":
        from krisnai.agents.a15_investigator import (
            A15InvestigatorAgent,
            format_ledger,
            format_summary,
            ledger,
            summarize,
            sweep,
        )
        from krisnai.engine import replay

        if args.inv_cmd == "sweep":
            res = sweep(engine, args.tenant, args.start, args.end, args.every_days)
            added = f"{res.events} variance events added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        elif args.inv_cmd == "replay":
            items = replay(engine, args.tenant, A15InvestigatorAgent())
            print(f"replayed {len(items)} events (shadow: nothing executed, nothing recovered)")
            print(format_summary(summarize(engine, args.tenant)))
        else:
            print(format_ledger(ledger(engine, args.tenant, args.detected_on, args.through)))
    elif args.cmd == "a13":
        from krisnai.agents.a13_credentialing import A13CredentialingAgent, format_summary, summarize, sweep
        from krisnai.engine import replay

        if args.a13_cmd == "sweep":
            res = sweep(engine, args.tenant, args.start, args.end, args.every_days)
            added = f"{res.events} credentialing events added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        else:
            items = replay(engine, args.tenant, A13CredentialingAgent())
            print(f"replayed {len(items)} events (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant)))
    elif args.cmd == "a11":
        from krisnai.agents.a11_cash import A11CashAgent, format_summary, summarize, sweep
        from krisnai.engine import replay

        if args.a11_cmd == "sweep":
            res = sweep(engine, args.tenant, args.start, args.end, args.every_days)
            added = f"{res.events} reconciliation events added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        else:
            items = replay(engine, args.tenant, A11CashAgent())
            print(f"replayed {len(items)} events (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant, args.as_of)))
    elif args.cmd == "a2":
        from krisnai.agents.a2_authorization import (
            A2AuthorizationAgent,
            format_summary,
            seed_defaults,
            summarize,
            sweep,
        )
        from krisnai.engine import replay
        from krisnai.model import tenant_session

        if args.a2_cmd == "seed":
            with tenant_session(engine, args.tenant) as s:
                added = seed_defaults(s)
                s.commit()
            print(f"{added} authorization requirement rows added")
        elif args.a2_cmd == "sweep":
            res = sweep(engine, args.tenant, args.start, args.end)
            added = f"{res.events} authorization checkpoints added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        else:
            items = replay(engine, args.tenant, A2AuthorizationAgent())
            print(f"replayed {len(items)} checkpoints (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant)))
    elif args.cmd == "a9":
        from krisnai.agents import a9_learning as a9m
        from krisnai.engine import replay

        if args.a9_cmd == "sweep":
            res = a9m.sweep(engine, args.tenant, args.start, args.end, args.every_days)
            added = f"{res.events} pattern events added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        elif args.a9_cmd == "replay":
            items = replay(engine, args.tenant, a9m.A9LearningAgent())
            print(f"replayed {len(items)} patterns (shadow: nothing executed)")
            print(a9m.format_summary(a9m.proposals(engine, args.tenant), args.tenant))
        elif args.a9_cmd in ("approve", "reject"):
            status = a9m.APPROVED if args.a9_cmd == "approve" else a9m.REJECTED
            try:
                print(json.dumps(a9m.decide(engine, args.tenant, args.rule, status, args.by)))
            except a9m.DecisionError as e:
                raise SystemExit(str(e)) from None
        elif args.a9_cmd == "forward":
            print(a9m.format_forward(a9m.forward(engine, args.tenant, args.as_of)))
        else:
            print(a9m.format_attribution(a9m.attribution(engine, args.tenant, args.as_of)))
    elif args.cmd == "a1":
        from krisnai.agents.a1_clearance import A1ClearanceAgent, format_summary, summarize, sweep
        from krisnai.engine import replay

        if args.a1_cmd == "sweep":
            res = sweep(engine, args.tenant, args.start, args.end)
            added = f"{res.events} clearance checkpoints added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        else:
            items = replay(engine, args.tenant, A1ClearanceAgent())
            print(f"replayed {len(items)} checkpoints (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant)))
    elif args.cmd == "a3":
        from krisnai.agents.a3_documentation import A3DocumentationAgent, format_summary, summarize, sweep
        from krisnai.engine import replay

        if args.a3_cmd == "sweep":
            res = sweep(engine, args.tenant, args.start, args.end, args.every_days)
            added = f"{res.events} documentation check events added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        else:
            items = replay(engine, args.tenant, A3DocumentationAgent())
            print(f"replayed {len(items)} checks (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant, args.as_of)))
    elif args.cmd == "a10":
        from krisnai.agents.a10_underpay import (
            A10UnderpaymentAgent,
            format_patterns,
            format_summary,
            patterns,
            summarize,
        )
        from krisnai.engine import replay

        if args.a10_cmd == "replay":
            items = replay(engine, args.tenant, A10UnderpaymentAgent())
            print(f"replayed {len(items)} payments (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant)))
        else:
            print(format_patterns(patterns(engine, args.tenant), args.tenant))
    elif args.cmd == "a5":
        from krisnai.agents.a5_prevention import A5PreventionAgent, format_summary, seed_defaults, summarize
        from krisnai.engine import replay
        from krisnai.model import tenant_session

        if args.a5_cmd == "seed":
            with tenant_session(engine, args.tenant) as s:
                added = seed_defaults(s)
                s.commit()
            print(f"{added} rule rows added")
        else:
            items = replay(engine, args.tenant, A5PreventionAgent())
            print(f"replayed {len(items)} claims (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant)))
    elif args.cmd == "tower":
        from krisnai.agents.a14_tower import compute_tower, format_tower

        tower = compute_tower(engine, args.tenant, args.as_of, args.backtest_weeks)
        print(json.dumps(tower, default=str, indent=2) if args.json else format_tower(tower))
    elif args.cmd == "a14":
        from krisnai.agents.a14_tower import A14TowerAgent, format_summary, summarize, sweep
        from krisnai.engine import replay

        if args.a14_cmd == "sweep":
            res = sweep(engine, args.tenant, args.start, args.end)
            added = f"{res.events} daily tower events added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        else:
            items = replay(engine, args.tenant, A14TowerAgent())
            print(f"replayed {len(items)} days (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant)))
    elif args.cmd == "a6":
        from krisnai.agents.a6_submission import A6SubmissionAgent, format_summary, seed_defaults, summarize
        from krisnai.engine import replay
        from krisnai.model import tenant_session

        if args.a6_cmd == "seed":
            with tenant_session(engine, args.tenant) as s:
                added = seed_defaults(s)
                s.commit()
            print(f"{added} routing rows added")
        else:
            items = replay(engine, args.tenant, A6SubmissionAgent())
            print(f"replayed {len(items)} rejections (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant)))
    elif args.cmd == "a7":
        from krisnai.agents.a7_ar import A7ArAgent, format_inbox, format_summary, inbox, summarize, sweep
        from krisnai.engine import replay

        if args.a7_cmd == "sweep":
            res = sweep(engine, args.tenant, args.start, args.end, args.every_days)
            added = f"{res.events} follow-up events added"
            print("this sweep was already recorded: nothing added" if res.skipped else added)
        elif args.a7_cmd == "replay":
            items = replay(engine, args.tenant, A7ArAgent())
            print(f"replayed {len(items)} follow-ups (shadow: nothing executed)")
            print(format_summary(summarize(engine, args.tenant)))
        else:
            print(format_inbox(inbox(engine, args.tenant, args.top), args.tenant))
    return 0


if __name__ == "__main__":
    sys.exit(main())
