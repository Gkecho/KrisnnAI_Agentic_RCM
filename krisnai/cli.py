"""krisnai command line.

    krisnai init-db                          create tables (dev / SQLite; SQL Server uses Alembic)
    krisnai tenant-create NAME --salt-key K  register a tenant and print its id
    krisnai ingest PATH --tenant ID          load X12 files / fee schedule CSVs (idempotent)

The patient-hash salt is read from the environment variable named by the tenant's salt key.
Use --db-url (or KRISNAI_DB_URL) for a non-SQL-Server database such as sqlite:///dev.db.
"""

from __future__ import annotations

import argparse
import os
import sys
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
