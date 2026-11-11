"""Starts the local live Postgres and builds the baseline: the practice, its history and the appointments already booked (synthetic).

Usage:
  python tools/live/setup_db.py            start the container, build krisnnai_baseline once, and (re)create krisnnai_live from it
  python tools/live/setup_db.py --rebuild  also rebuild the baseline from the generator
  python tools/live/setup_db.py --reset    only drop krisnnai_live and copy it again from the baseline (a few seconds)
"""
import secrets
import subprocess
import sys
import time

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import ROOT, raw_connect  # noqa: E402


def ensure_container():
    env = ROOT / ".env.live"
    if not env.exists():
        env.write_text(f"LIVE_PG_PASSWORD={secrets.token_urlsafe(18)}\n", encoding="utf-8")
        print("created .env.live (git-ignored)")
    subprocess.run(["docker", "compose", "-f", str(ROOT / "docker-compose.live.yml"), "--env-file", str(env), "up", "-d"], check=True)
    for _ in range(40):
        try:
            raw_connect("postgres").close()
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("the live Postgres did not become ready")


def exists(cur, name):
    cur.execute("select 1 from pg_database where datname=%s", (name,))
    return bool(cur.fetchone())


def build_baseline():
    from run import build               # the generator in tools/synth
    c = raw_connect("postgres"); c.autocommit = True
    cur = c.cursor()
    cur.execute("DROP DATABASE IF EXISTS krisnnai_baseline WITH (FORCE)")
    cur.execute("CREATE DATABASE krisnnai_baseline")
    c.close()
    conn = raw_connect("krisnnai_baseline")
    cur = conn.cursor()
    cur.execute((ROOT / "docs" / "data_model" / "schema_postgres.sql").read_text(encoding="utf-8"))
    conn.commit()
    s, ctx = build()
    counts = s.load(reset=False, conn=conn)
    print("baseline loaded:", sum(counts.values()), "rows in", len(counts), "tables")
    conn = raw_connect("krisnnai_baseline")                 # the loader closes its connection
    conn.autocommit = True
    conn.cursor().execute((ROOT / "tools" / "live" / "indexes.sql").read_text(encoding="utf-8"))
    print("indexes created")
    conn.close()


def reset_live():
    c = raw_connect("postgres"); c.autocommit = True
    cur = c.cursor()
    cur.execute("DROP DATABASE IF EXISTS krisnnai_live WITH (FORCE)")
    cur.execute("CREATE DATABASE krisnnai_live TEMPLATE krisnnai_baseline")
    c.close()
    print("krisnnai_live created from the baseline")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools" / "synth"))
    if "--reset" not in sys.argv:
        ensure_container()
        c = raw_connect("postgres"); c.autocommit = True
        cur = c.cursor()
        have = exists(cur, "krisnnai_baseline")
        c.close()
        if not have or "--rebuild" in sys.argv:
            build_baseline()
    reset_live()
