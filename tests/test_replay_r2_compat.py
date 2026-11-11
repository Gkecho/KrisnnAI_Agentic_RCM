"""Replay on R2: the env switch keeps today's defaults, and the canon_compat layer is views only, tenant-scoped, and row-for-row with the R2 tables.

The database tests are skipped when krisnnai_r2 cannot be reached. They only SELECT (read-only session); nothing is written.
"""
import datetime as dt
import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "replay"))
sys.path.insert(0, str(ROOT / "tools" / "synth"))


def _fresh(monkeypatch, **env):
    for k in ("KRISNNAI_REPLAY_DB", "KRISNNAI_REPLAY_START", "KRISNNAI_REPLAY_END"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    import world
    import engine
    return importlib.reload(world), importlib.reload(engine)


def test_default_is_unchanged(monkeypatch):
    world, engine = _fresh(monkeypatch)
    assert world.replay_db() is None and not world.is_r2()
    assert engine.START == dt.date(2025, 11, 3)
    assert engine.RULES_FROM == dt.date(2025, 11, 1)
    assert engine.A15_FROM == dt.date(2026, 1, 5)
    assert engine.A14_FROM == dt.date(2026, 2, 2)
    assert engine.A5_NEXT_BIZ is False and engine.AR_AS_OF is False          # canonical keeps today's behaviour


def test_r2_enables_next_business_day_and_as_of_ar(monkeypatch):
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_DB="krisnnai_r2")
    assert engine.A5_NEXT_BIZ is True and engine.AR_AS_OF is True


def test_a5_flag_works_for_canonical(monkeypatch):
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_A5_NEXT_BIZ="1")
    assert engine.A5_NEXT_BIZ is True and engine.AR_AS_OF is False


def test_plan_of_care_is_unknown_without_documents(monkeypatch):
    _, engine = _fresh(monkeypatch)
    from types import SimpleNamespace
    r = SimpleNamespace(W=SimpleNamespace(doc_types=set()))
    assert engine.Replay.has_poc(r, {"patient_id": 1, "encounter_date": dt.date(2025, 1, 1)}) is None      # unknown, not "missing"


def test_plan_of_care_known_when_documents_exist(monkeypatch):
    _, engine = _fresh(monkeypatch)
    from types import SimpleNamespace
    e = {"patient_id": 1, "encounter_date": dt.date(2025, 3, 1), "encounter_type": "evaluation"}
    W = SimpleNamespace(doc_types={"plan_of_care"}, pat_enc={1: [e]}, pat_doc={1: [{"document_type": "plan_of_care", "document_date": dt.date(2025, 3, 1)}]})
    r = SimpleNamespace(W=W)
    assert engine.Replay.has_poc(r, e) is True
    W.pat_doc = {1: []}
    assert engine.Replay.has_poc(r, e) is False


def test_only_exact_r2_name_is_accepted(monkeypatch):
    world, _ = _fresh(monkeypatch)
    for bad in ("krisnnai_r2_copy", "krisnnai_canonical", "krisnnai_r", "KRISNNAI_R2", "x"):
        monkeypatch.setenv("KRISNNAI_REPLAY_DB", bad)
        with pytest.raises(ValueError):
            world.replay_db()
    monkeypatch.setenv("KRISNNAI_REPLAY_DB", "krisnnai_r2")
    assert world.is_r2()


def test_window_env_overrides(monkeypatch):
    _, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_START="2023-11-06", KRISNNAI_REPLAY_END="2026-11-06")
    assert engine.START == dt.date(2023, 11, 6) and engine.TODAY == dt.date(2026, 11, 6)
    assert engine.A14_FROM == engine.START + dt.timedelta(days=91)


def test_r2_write_mode_is_refused(monkeypatch):
    world, engine = _fresh(monkeypatch, KRISNNAI_REPLAY_DB="krisnnai_r2")
    r = engine.Replay.__new__(engine.Replay)
    r.write = True
    r._reset_state = lambda: None
    with pytest.raises(RuntimeError):
        engine.Replay.prepare(r)


@pytest.fixture(scope="module")
def cur():
    os.environ["KRISNNAI_PG_DB"] = "krisnnai_r2"
    try:
        from core import connect
        conn, db = connect()
    except Exception as ex:          # no network / credentials: skip rather than fail
        pytest.skip(f"krisnnai_r2 not reachable: {type(ex).__name__}")
    assert db == "krisnnai_r2"
    conn.set_session(readonly=True)
    c = conn.cursor()
    yield c
    conn.close()


def test_schema_has_views_only(cur):
    cur.execute("SELECT c.relkind, count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'canon_compat' AND c.relkind NOT IN ('i','S','c','t') GROUP BY 1")
    assert dict(cur.fetchall()) == {"v": 29}


def test_every_view_filters_tenant_1(cur):
    cur.execute("SELECT viewname, definition FROM pg_views WHERE schemaname = 'canon_compat'")
    for name, definition in cur.fetchall():
        assert "tenant_id = 1" in definition, name


def test_no_cross_tenant_rows_visible(cur):
    cur.execute("SELECT table_name FROM information_schema.columns WHERE table_schema = 'canon_compat' AND column_name = 'tenant_id'")
    for (t,) in cur.fetchall():
        cur.execute(f'SELECT count(*) FROM canon_compat."{t}" WHERE tenant_id <> 1')
        assert cur.fetchone()[0] == 0, t


@pytest.mark.parametrize("view,source", [("claim", "claim"), ("claim_details", "claim_line"), ("appointment_details", "appointment_line"), ("encounter_details", "encounter_line"),
                                         ("denial", "denial"), ("payment", "payment"), ("claim_status_history", "claim_status_history"), ("appointment", "appointment")])
def test_row_counts_match_source(cur, view, source):
    cur.execute(f'SELECT (SELECT count(*) FROM canon_compat."{view}"), (SELECT count(*) FROM public."{source}" WHERE tenant_id = 1)')
    a, b = cur.fetchone()
    assert a == b > 0


def test_event_vocabulary_is_mapped(cur):
    cur.execute("SELECT DISTINCT event_type FROM canon_compat.claim_status_history")
    got = {r[0] for r in cur.fetchall()}
    assert {"accepted_277ca", "remit_835"} <= got and "acknowledged" not in got and "adjudicated" not in got


def test_one_recovery_payment_per_overturned_denial(cur):
    cur.execute("SELECT count(*), count(DISTINCT denial_id) FROM canon_compat.transactions")
    a, b = cur.fetchone()
    cur.execute("SELECT count(*) FROM public.denial WHERE tenant_id = 1 AND outcome = 'overturned'")
    assert a == b == cur.fetchone()[0]


def test_payer_turnaround_filled_except_self_pay(cur):
    cur.execute("SELECT payer_code, standard_turnaround_days FROM canon_compat.payer")
    got = dict(cur.fetchall())
    assert got.pop("SELF") is None
    assert all(v is not None and v > 0 for v in got.values()), got


def test_ar_exposes_every_snapshot_with_its_date(cur):
    cur.execute("SELECT count(DISTINCT as_of_date), min(as_of_date), max(snapshot_type) FROM canon_compat.ar")
    n, first, _ = cur.fetchone()
    assert n == 13 and first == dt.date(2025, 11, 30)
