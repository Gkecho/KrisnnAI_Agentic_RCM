"""Benchmark: load a synthetic book of N claims and time the load, the match, the gate and every agent step.

Development tool. It needs the repo's `tests/fixtures/make_synthetic.py` (the synthetic generator is not shipped in the
package) and uses a throwaway SQLite database, so the numbers show where the Python time goes, not what SQL Server
would do with the same load.
"""

from __future__ import annotations

import shutil
import tempfile
from datetime import date
from pathlib import Path


def run_bench(claims: int, workdir: Path | None = None) -> dict:
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session

    import krisnnai.model as m
    from krisnnai.model import Base
    from krisnnai.ops.daily import run_period

    try:
        from tests.fixtures import make_synthetic as ms
    except ImportError as e:  # pragma: no cover - only when run outside the repo
        raise SystemExit("ops bench needs tests/fixtures/make_synthetic.py (run it from the repo root)") from e

    root = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="krisnnai_bench_"))
    inbox = root / "inbox"
    shutil.rmtree(inbox, ignore_errors=True)
    ms.generate(inbox, seed=11, n_claims=claims)
    engine = create_engine(f"sqlite:///{root / 'bench.sqlite'}")

    @event.listens_for(engine, "connect")
    def _fk(conn, _):  # noqa: ANN001
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(m.Tenant(name="bench", patient_salt_key="BENCH_SALT"))
        s.commit()
    as_of = ms.AS_OF
    rep = run_period(
        engine, 1, "bench", as_of, inbox=inbox, archive=root / "archive", mode="backfill",
        start=date(as_of.year - 1, as_of.month, 1), step_days=28, allow_failed=True,
    )
    with Session(engine) as s:
        n_events = s.query(m.Event).count()
    return {"claims": claims, "events": n_events, "report": rep.to_dict(), "workdir": str(root)}


def format_bench(b: dict) -> str:
    rep = b["report"]
    total = sum(rep["timings"].values()) + sum(v["seconds"] for v in rep["steps"].values())
    lines = [f"bench: {b['claims']} claims, {b['events']} events, status {rep['status']}, total {total:.1f} s"]
    lines += [f"  {k:8s}{v:10.2f} s" for k, v in rep["timings"].items()]
    lines += [
        f"  {name:8s}{v['seconds']:10.2f} s   sweep events {v['sweep_events']:6d}  records {v['records']:6d}"
        for name, v in sorted(rep["steps"].items(), key=lambda kv: -kv[1]["seconds"])
    ]
    return "\n".join(lines)
