"""Synthetic-data framework for the KrisnnAI canonical model (PostgreSQL).

Rows are built in memory with `Synth.add`, checked against the model (mandatory columns, lengths, foreign keys),
then bulk-loaded with COPY. Nothing here contacts a client system, and all values are synthetic (no real PHI).

Connection settings come from a dotenv-style file (KRISNNAI_PG_ENV_FILE) or the environment (PGHOST, PGPORT, PGUSER,
PGPASSWORD); the database name comes from KRISNNAI_PG_DB (default krisnnai_canonical). The password is never printed.
"""
import csv
import datetime as dt
import hashlib
import io
import json
import os
import random
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_PATH = HERE.parent / "data_model" / "build" / "model.json"
SALT = "krisnnai-synthetic-salt"
TENANT = 1
TODAY = dt.date(2026, 11, 2)           # the demo's "today"; visits after it are scheduled, not yet happened
BOILER = {"tenant_id": TENANT, "source": "synthetic", "is_reconstructed": False, "is_active": True,
          "version": 1, "is_current": True}


def h(kind, n):
    """Salted hash of a synthetic identifier (the model never stores raw patient or member numbers)."""
    return hashlib.sha256(f"{SALT}|{kind}|{n}".encode()).digest()


def load_env():
    env = dict(os.environ)
    path = os.environ.get("KRISNNAI_PG_ENV_FILE", r"C:\Users\gopi.v\OneDrive\projects\edi-dashboard\config.env")
    if os.path.exists(path):
        for k, v in re.findall(r"^(\w+)=(.*)$", open(path, encoding="utf-8").read(), re.M):
            env.setdefault(k, v.strip())
    return env


def connect():
    import psycopg2
    env = load_env()
    db = env.get("KRISNNAI_PG_DB", "krisnnai_canonical")
    return psycopg2.connect(host=env["PGHOST"], port=env.get("PGPORT", 5432), user=env["PGUSER"],
                            password=env.get("PGPASSWORD", ""), dbname=db, connect_timeout=20,
                            sslmode=env.get("PGSSLMODE", "require")), db


class Synth:
    def __init__(self, seed=20261102):
        self.rnd = random.Random(seed)
        m = json.load(open(MODEL_PATH, encoding="utf-8"))
        self.T = {t["name"]: t for t in m["tables"]}
        self.cols = {n: {c["name"]: c for c in t["cols"]} for n, t in self.T.items()}
        self.pk = {n: t["cols"][0]["name"] for n, t in self.T.items()}
        self.rows = defaultdict(list)
        self.ids = defaultdict(set)
        self._next = defaultdict(lambda: 1)
        self.loaded_at = dt.datetime(2026, 11, 2, 6, 0, 0)

    def add(self, table, **vals):
        """Add one row; returns its id. Boilerplate columns and the primary key are filled when absent."""
        cols = self.cols[table]
        bad = [k for k in vals if k not in cols]
        if bad:
            raise KeyError(f"{table}: unknown column(s) {bad}")
        row = dict(vals)
        pk = self.pk[table]
        if row.get(pk) is None:
            row[pk] = self._next[table]
        self._next[table] = max(self._next[table], row[pk]) + 1
        for k, v in BOILER.items():
            if k in cols and k not in row:
                row[k] = v
        if "known_at" in cols and "known_at" not in row:
            row["known_at"] = self.loaded_at
        if "loaded_at" in cols:
            row.setdefault("loaded_at", self.loaded_at)
        for c in cols:                                  # every column is present; unset ones are NULL
            row.setdefault(c, None)
        self.rows[table].append(row)
        self.ids[table].add(row[pk])
        return row[pk]

    def version(self, table, old_id, **changes):
        """Close a row and add a new version of it (nothing is overwritten): returns the new id."""
        old = next(r for r in self.rows[table] if r[self.pk[table]] == old_id)
        new = {k: v for k, v in old.items() if k != self.pk[table]}
        new.update(changes)
        new["version"] = old["version"] + 1
        new[f"previous_{table}_id"] = old_id
        old["is_current"] = False
        if "replaced_date" in self.cols[table]:
            old["replaced_date"] = changes.get("known_at", self.loaded_at)
        return self.add(table, **new)

    # ------------------------------------------------------------------ checks
    def check(self):
        errs = []
        for n, rows in self.rows.items():
            cols = self.cols[n]
            for c in cols.values():
                m = re.match(r"(?:N?VARCHAR|CHAR)\((\d+)\)", c["type"])
                limit = int(m.group(1)) if m else None
                bad_null = bad_len = bad_fk = 0
                for r in rows:
                    v = r.get(c["name"])
                    if v is None:
                        if c["priority"] == "Mandatory" or c["name"] == self.pk[n]:
                            bad_null += 1
                        continue
                    if limit and isinstance(v, str) and len(v) > limit:
                        bad_len += 1
                    if c.get("link") and self.ids[c["link"]] and v not in self.ids[c["link"]]:
                        bad_fk += 1
                for what, k in (("null in mandatory column", bad_null), ("value too long", bad_len), ("link to a missing row", bad_fk)):
                    if k:
                        errs.append(f"{n}.{c['name']}: {k} row(s) with {what}")
        return errs

    # ------------------------------------------------------------------ load order
    def order(self):
        """Parent-first order of the tables that have rows; links that form a cycle (nullable ones) are loaded afterwards."""
        names = [n for n in self.T if self.rows.get(n)]
        edges = []     # (child, parent, column)
        for n in names:
            for c in self.T[n]["cols"]:
                p = c.get("link")
                if p and p != n and p in names:
                    edges.append((n, p, c["name"]))
        deferred = []
        while True:
            indeg = {n: 0 for n in names}
            for ch, pa, col in edges:
                indeg[ch] += 1
            out, ready = [], [n for n in names if indeg[n] == 0]
            left = list(edges)
            while ready:
                n = ready.pop(0)
                out.append(n)
                for e in [e for e in left if e[1] == n]:
                    left.remove(e)
                    indeg[e[0]] -= 1
                    if indeg[e[0]] == 0:
                        ready.append(e[0])
            if len(out) == len(names):
                return out, deferred
            stuck = [e for e in left if self.cols[e[0]][e[2]]["priority"] != "Mandatory"]
            if not stuck:
                raise RuntimeError("cycle of mandatory links, cannot order tables")
            e = stuck[0]
            deferred.append(e)
            edges.remove(e)

    # ------------------------------------------------------------------ load
    @staticmethod
    def _cell(v):
        if v is None:
            return r"\N"
        if isinstance(v, bool):
            return "t" if v else "f"
        if isinstance(v, (bytes, bytearray)):
            return r"\x" + bytes(v).hex()
        if isinstance(v, dt.datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(v, (dt.date, Decimal)):
            return str(v)
        return str(v)

    def load(self, reset=False, conn=None):
        errs = self.check()
        if errs:
            raise ValueError("model check failed:\n  " + "\n  ".join(errs[:40]))
        if conn is None:
            conn, db = connect()
        else:
            conn.rollback()
            cur0 = conn.cursor()
            cur0.execute("select current_database()")
            db = cur0.fetchone()[0]
        if not db.startswith("krisnnai_"):
            raise RuntimeError(f"refusing to load into database {db!r}")
        cur = conn.cursor()
        if reset:
            cur.execute("TRUNCATE " + ",".join(f'"{n}"' for n in self.T) + " RESTART IDENTITY CASCADE")
        order, deferred = self.order()
        defer = defaultdict(set)
        for ch, pa, col in deferred:
            defer[ch].add(col)
        later = defaultdict(list)
        for n in order:
            cols = [c["name"] for c in self.T[n]["cols"]]
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            for r in self.rows[n]:
                for col in defer.get(n, ()):
                    if r.get(col) is not None:
                        later[(n, col)].append((r[self.pk[n]], r[col]))
                w.writerow([self._cell(None if c in defer.get(n, ()) else r.get(c)) for c in cols])
            buf.seek(0)
            cur.copy_expert(f'COPY "{n}" ({",".join(chr(34) + c + chr(34) for c in cols)}) FROM STDIN WITH (FORMAT csv, NULL \'\\N\')', buf)
        for (n, col), pairs in later.items():
            cur.execute("CREATE TEMP TABLE _fix (id bigint, v bigint) ON COMMIT DROP")
            buf = io.StringIO("".join(f"{a},{b}\n" for a, b in pairs))
            cur.copy_expert("COPY _fix (id, v) FROM STDIN WITH (FORMAT csv)", buf)
            cur.execute(f'UPDATE "{n}" t SET "{col}" = f.v FROM _fix f WHERE t."{self.pk[n]}" = f.id')
            cur.execute("DROP TABLE _fix")
        for n in order:
            cur.execute(f"SELECT setval(pg_get_serial_sequence('\"{n}\"', '{self.pk[n]}'), (SELECT max(\"{self.pk[n]}\") FROM \"{n}\"))")
        conn.commit()
        conn.close()
        return {n: len(self.rows[n]) for n in order}
