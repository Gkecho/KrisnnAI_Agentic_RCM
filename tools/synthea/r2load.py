"""Small loader for the R2 database on AWS (krisnnai_r2): column checks against the R2 model, boilerplate columns, integer keys, COPY.

Synthea ids are UUIDs. Each one is mapped to our own integer key here and the map is kept in memory (and saved with save_maps) for the next load stage; a UUID is never
written to a column. Patient ids are stored only as a salted hash.
"""
import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import pickle
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "synth"))
from core import load_env  # noqa: E402

DB = "krisnnai_r2"
WORK = pathlib.Path(__file__).resolve().parent / "work"
CSV = pathlib.Path(__file__).resolve().parent / "output" / "csv"
SALT = "krisnnai-synthea-2026"
MODEL = json.load(open(ROOT / "docs" / "data_model" / "r2_model.json", encoding="utf-8"))
TBL = {t["name"]: t for t in MODEL["tables"]}
NOW = dt.datetime(2026, 11, 6, 12, 0, 0)
END = dt.date(9999, 12, 31)


def h(kind, value):
    """32-byte salted hash, as a Postgres bytea hex literal."""
    return "\\x" + hashlib.sha256(f"{SALT}|{kind}|{value}".encode()).hexdigest()


def connect():
    import psycopg2
    env = load_env()
    c = psycopg2.connect(host=env["PGHOST"], port=env.get("PGPORT", 5432), user=env["PGUSER"], password=env.get("PGPASSWORD", ""), dbname=DB, connect_timeout=20, sslmode=env.get("PGSSLMODE", "require"))
    cur = c.cursor()
    cur.execute("select current_database()")
    assert cur.fetchone()[0] == DB
    return c


class Loader:
    def __init__(self, conn):
        self.c = conn
        self.next = {}
        self.maps = {}

    def key(self, table):
        self.next[table] = self.next.get(table, 0) + 1
        return self.next[table]

    def rows(self, table, rows):
        """Checks columns, fills the boilerplate and COPYs the rows (dicts). Returns the number loaded."""
        if not rows:
            return 0
        t = TBL[table]
        names = [c["name"] for c in t["cols"]]
        boiler = dict(tenant_id=1, load_batch_id=1, is_source_deleted=False, version=1, is_current=True, is_active=True, source="synthea", loaded_at=NOW)
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        cols = [n for n in names if any(n in r for r in rows) or n in boiler]
        for r in rows:
            bad = [k for k in r if k not in names]
            assert not bad, (table, bad)
            full = {**boiler, **r}
            for c in t["cols"]:
                if c["priority"] == "Mandatory" and c["name"] in cols and full.get(c["name"]) is None:
                    raise ValueError(f"{table}.{c['name']} is mandatory and empty in {r}")
            w.writerow(["" if full.get(n) is None else ("true" if full[n] is True else "false" if full[n] is False else full[n]) for n in cols])
        buf.seek(0)
        cur = self.c.cursor()
        cur.copy_expert(f'COPY "{table}" ({",".join(chr(34) + n + chr(34) for n in cols)}) FROM STDIN WITH (FORMAT csv, NULL \'\')', buf)
        return len(rows)

    def save_maps(self):
        WORK.mkdir(exist_ok=True)
        pickle.dump(dict(maps=self.maps, next=self.next), open(WORK / "idmaps.pkl", "wb"))


def reader(name):
    return csv.DictReader(open(CSV / name, encoding="utf-8"))


def date(s):
    return dt.date.fromisoformat(s[:10]) if s else None
