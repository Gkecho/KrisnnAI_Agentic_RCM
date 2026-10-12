"""krisnai command line.

    krisnai init-db                          create tables (dev / SQLite; SQL Server uses Alembic)
    krisnai tenant-create NAME --salt-key K  register a tenant and print its id
    krisnai ingest PATH --tenant ID          load X12 files / fee schedule CSVs (idempotent)
    krisnai load-valley --tenant ID --valley-config FILE   load a sample of the Valley Wellness database
    krisnai metrics --tenant ID --as-of DATE [--kpi NAME] [--json]   compute KPIs as of a date
    krisnai a15 --tenant ID --as-of DATE --out DIR [--ground-truth CSV]   leakage diagnostic (read-only)
    krisnai a8 seed|replay --tenant ID                                    denial agent (shadow only)
    krisnai a5 seed|replay --tenant ID                                    claim prevention agent (shadow only)
    krisnai a7 sweep|replay|inbox --tenant ID                             AR follow-up agent (shadow only)
    krisnai a6 seed|replay --tenant ID                                    rejection handling agent (shadow only)
    krisnai tower --tenant ID --as-of DATE [--json]                       control tower snapshot (read-only)
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
    args = parser.parse_args(argv)

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
