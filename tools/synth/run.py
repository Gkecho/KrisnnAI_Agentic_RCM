"""Build the synthetic practice (the history: everything except agent output) and load it into krisnnai_canonical.
Usage: python run.py [--dry] [--schema] [--with-agents]
--dry: build and check only.  --schema: drop and recreate the schema from docs/data_model/schema_postgres.sql first."""
import sys
from pathlib import Path
from core import Synth, connect
from ref import build_reference
from journey import build_journey, add_enrollments
from multispec import build_clinic, build_resource_master, build_resources
from money import build_money
from agents import build_agents


def build():
    s = Synth()
    ctx = build_reference(s)
    build_journey(s, ctx, n_patients=2500)
    build_clinic(s, ctx)
    build_money(s, ctx)
    add_enrollments(s, ctx)
    build_resource_master(s, ctx)
    build_resources(s, ctx)
    if "--with-agents" in sys.argv:        # the old batch build; the replay engine now produces agent output at run time
        build_agents(s, ctx)
    return s, ctx


if __name__ == "__main__":
    s, ctx = build()
    errs = s.check()
    print("model check:", "OK" if not errs else errs[:20])
    if errs or "--dry" in sys.argv:
        print({n: len(r) for n, r in s.rows.items()})
        sys.exit(1 if errs else 0)
    if "--schema" in sys.argv:
        conn, db = connect()
        assert db.startswith("krisnnai_canonical")
        cur = conn.cursor()
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        cur.execute(Path(__file__).resolve().parents[2].joinpath("docs/data_model/schema_postgres.sql").read_text(encoding="utf-8"))
        conn.commit(); conn.close()
        print("schema recreated in", db)
    counts = s.load(reset=True)
    print("loaded:", counts)
