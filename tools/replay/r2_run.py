"""Run the Replay history traces over krisnnai_r2, save the results in the agent_* tables, export ui_data.js.

    python tools/replay/r2_run.py --dry        # run in memory only, print per-agent counts, write nothing
    python tools/replay/r2_run.py              # run, reset this source's agent_* rows, persist, export out/ui/ui_data.js

Reads R2 through the canon_compat views (read-only connection). Writes only the nine agent_* tables (source 'replay').
Shadow mode: nothing is sent anywhere. The database password is never printed.
"""
import argparse
import os
import sys
import time
from pathlib import Path

os.environ["KRISNNAI_REPLAY_DB"] = "krisnnai_r2"
os.environ.setdefault("KRISNNAI_REPLAY_START", "2023-11-06")  # full history: the first day of data
os.environ.setdefault("KRISNNAI_REPLAY_END", "2026-11-06")  # the data date
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "synth"))
sys.path.insert(0, str(ROOT / "tools" / "synthea"))

import engine  # noqa: E402
import r2_export_ui  # noqa: E402
import r2_persist  # noqa: E402
import r2load  # noqa: E402
import world  # noqa: E402


def run_replay():
    t0 = time.time()
    w = world.World(log=lambda m: None)
    assert w.db == "krisnnai_r2", w.db
    print(f"world loaded from {w.db} in {time.time() - t0:.1f}s")
    rp = engine.Replay(w, write=False)  # write=False: nothing is written by the engine itself
    rp.publish = lambda p: None
    t1 = time.time()
    rp.run(speed=100000)
    print(f"replay finished in {time.time() - t1:.1f}s, status {rp.status}, days {rp.day_no}")
    errs = rp.S.check()
    print(f"integrity check errors: {len(errs)}")
    if errs:
        for e in errs[:10]:
            print("  ", e)
        raise SystemExit("integrity check failed; nothing persisted")
    print({n: len(rp.S.rows[n]) for n in engine.AGENT_TABLES})
    for a, s in rp.agent_stat.items():
        print(f"  {a:4s} {engine.NAMES[a]:14s} items={s['items']:>7} dec={s['dec']:>7} find={s['find']:>7} tasks={s['tasks']:>7}")
    return rp


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry", action="store_true", help="run in memory only; write nothing")
    ap.add_argument("--no-export", action="store_true", help="persist but do not export ui_data.js")
    ap.add_argument("--out", default=str(ROOT / "out" / "ui"))
    args = ap.parse_args(argv)

    rp = run_replay()
    if args.dry:
        print("dry run: nothing written")
        return 0

    conn = r2load.connect()  # asserts krisnnai_r2
    try:
        r2_persist.assert_r2(conn)
        stats = r2_persist.persist_run(conn, rp, reset_first=True)
        conn.commit()
        print("persisted:", stats)
    finally:
        conn.close()

    if not args.no_export:
        r2_export_ui.main(["--out", args.out])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
