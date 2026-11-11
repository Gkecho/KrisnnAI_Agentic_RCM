"""Applies tools/replay/r2_compat.sql to krisnnai_r2: schema canon_compat with read-only views over the R2 tables, named as the Replay engine expects.

Usage:  python tools/replay/r2_compat.py            (idempotent: CREATE SCHEMA IF NOT EXISTS + CREATE OR REPLACE VIEW)
        python tools/replay/r2_compat.py --check    (only lists what is in canon_compat)

The only writes are the schema and its views. Credentials come from the existing connect() helper and are never printed.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "synth"))
DB = "krisnnai_r2"
os.environ["KRISNNAI_PG_DB"] = DB
from core import connect  # noqa: E402


def objects(cur):
    cur.execute("SELECT c.relname, c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'canon_compat' AND c.relkind NOT IN ('i','S','c','t') ORDER BY 1")
    return cur.fetchall()


def main():
    conn, db = connect()
    assert db == DB, db
    cur = conn.cursor()
    if "--check" not in sys.argv:
        cur.execute((HERE / "r2_compat.sql").read_text(encoding="utf-8"))
        conn.commit()
    objs = objects(cur)
    non_view = [o for o in objs if o[1] != "v"]
    print(f"canon_compat in {db}: {len(objs)} objects, {len(objs) - len(non_view)} views, non-views: {non_view}")
    for name, _ in objs:
        cur.execute(f'SELECT count(*) FROM canon_compat."{name}"')
        print(f"  {name:22s} {cur.fetchone()[0]:>10,}")
    conn.close()
    assert not non_view, "canon_compat must contain views only"


if __name__ == "__main__":
    main()
