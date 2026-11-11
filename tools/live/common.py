"""Shared helpers for the live simulation: the local Postgres connection, the model's column lists, and a small traced database wrapper.

Everything here talks to the local container defined in docker-compose.live.yml (synthetic data only).
"""
import datetime as dt
import json
import re
import sys
import time
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "synth"))
MODEL = json.load(open(ROOT / "tools" / "data_model" / "build" / "model.json", encoding="utf-8"))
COLS = {t["name"]: [c["name"] for c in t["cols"]] for t in MODEL["tables"]}
PK = {t["name"]: t["cols"][0]["name"] for t in MODEL["tables"]}
PORT = 15432
D = Decimal


def password():
    for line in (ROOT / ".env.live").read_text(encoding="utf-8").splitlines():
        if line.startswith("LIVE_PG_PASSWORD="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("no LIVE_PG_PASSWORD in .env.live; run python tools/live/setup_db.py")


def raw_connect(db="krisnnai_live"):
    return psycopg2.connect(host="127.0.0.1", port=PORT, user="postgres", password=password(), dbname=db, connect_timeout=10)


def q2(x):
    return Decimal(x).quantize(Decimal("0.01"))


def jsonable(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    if isinstance(v, memoryview):
        return "<bytes>"
    return v


class DB:
    """One connection used by one thread. Autocommit, so every worker sees the others' rows straight away.
    When `trace` is a list, every read is recorded with its SQL, parameters, row count, time and a sample of the rows."""

    def __init__(self, db="krisnnai_live", clock=None, label=""):
        self.conn = raw_connect(db)
        self.conn.autocommit = True
        self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        self.clock = clock          # object with .now() returning the simulated datetime
        self.trace = None
        self.label = label
        self.queries = 0

    def q(self, sql, params=None, why=""):
        t0 = time.perf_counter()
        self.cur.execute(sql, params)
        rows = [dict(r) for r in self.cur.fetchall()] if self.cur.description else []
        ms = (time.perf_counter() - t0) * 1000
        self.queries += 1
        if self.trace is not None:
            self.trace.append(dict(sql=re.sub(r"\s+", " ", sql).strip(), params=[jsonable(p) for p in (params or [])], rows=len(rows), ms=round(ms, 2), why=why,
                                   sample=[{k: jsonable(v) for k, v in r.items()} for r in rows[:5]]))
        return rows

    def x(self, sql, params=None):
        self.cur.execute(sql, params)

    def insert(self, table, **vals):
        """Inserts one row (boilerplate columns filled), returns its primary key."""
        cols = COLS[table]
        now = self.clock.now() if self.clock else dt.datetime.now()
        vals = dict(vals)
        for k, v in dict(tenant_id=1, source="live", is_reconstructed=False, is_active=True, version=1, is_current=True).items():
            if k in cols and k not in vals:
                vals[k] = v
        if "known_at" in cols and "known_at" not in vals:
            vals["known_at"] = now.replace(microsecond=0)
        if "loaded_at" in cols and "loaded_at" not in vals:
            vals["loaded_at"] = dt.datetime.now().replace(microsecond=0)
        bad = [k for k in vals if k not in cols]
        if bad:
            raise KeyError(f"{table}: unknown columns {bad}")
        names = list(vals)
        self.cur.execute(f'INSERT INTO "{table}" ({",".join(chr(34) + n + chr(34) for n in names)}) VALUES ({",".join(["%s"] * len(names))}) RETURNING "{PK[table]}"', [vals[n] for n in names])
        return self.cur.fetchone()[PK[table]]

    def update(self, table, pk, **vals):
        names = list(vals)
        self.cur.execute(f'UPDATE "{table}" SET {",".join(chr(34) + n + chr(34) + " = %s" for n in names)} WHERE "{PK[table]}" = %s', [vals[n] for n in names] + [pk])

    def close(self):
        self.conn.close()
