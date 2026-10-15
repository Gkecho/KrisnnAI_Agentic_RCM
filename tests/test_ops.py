"""M22 tests: the inbox, the load gate, daily vs backfill equivalence, incremental replay, the crosswalk and the CLI."""

from __future__ import annotations

import shutil
from collections import Counter
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

import krisnai.model as m
from krisnai import cli
from krisnai.agents.a8_denial import A8DenialAgent
from krisnai.engine import replay
from krisnai.engine.decision_record import fingerprint
from krisnai.ingest.loader import ingest_file, ingest_path
from krisnai.model import tenant_session
from krisnai.ops import check_gate, last_run, run_period, scan, watermark
from krisnai.ops.registry import grid_start, steps
from krisnai.synthea import build
from tests.fixtures import make_synthetic as ms, synthea_mini
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

AS_OF = ms.AS_OF
START = AS_OF - timedelta(days=120)


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    root = tmp_path_factory.mktemp("ops_data")
    ms.generate(root, seed=5, n_claims=80)
    return root


SYN_AS_OF = date(2026, 6, 30)


@pytest.fixture(scope="module")
def book(tmp_path_factory):
    """A Synthea-style book whose claims are known on their submission dates (the plain synthetic set stamps them all
    on one day, so it cannot be split by date)."""
    root = tmp_path_factory.mktemp("ops_book")
    raw = synthea_mini.write(root / "raw", n_claims=200, n_patients=30, seed=5)
    build(raw, root / "book", SYN_AS_OF, seed=7, documentation=True)
    return root / "book"


def fresh_inbox(data, tmp_path, name="inbox"):
    dest = tmp_path / name
    shutil.copytree(data, dest, ignore=shutil.ignore_patterns("ground_truth.csv"))
    return dest


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return Counter(
            (r.agent_id, r.action_type, fingerprint(r)) for r in s.scalars(select(m.DecisionRecord))
        )


def payloads(engine, tenant=1, skip=("a14_tower",)):
    """What each decision said, without event ids: sweep events are inserted in a different order by a daily run and a
    backfill, so ids (and the fingerprints that include them) differ while the decisions themselves are identical."""
    with tenant_session(engine, tenant) as s:
        return Counter(
            (r.agent_id, r.action_type, r.action_payload, str(r.materiality_amount))
            for r in s.scalars(select(m.DecisionRecord)) if r.agent_id not in skip
        )


# ------------------------------------------------------------------------------------------------ the inbox


def test_scan_orders_reference_then_claims_then_acks_then_payments_then_feeds(data):
    files = scan(data)
    csv_pos = {p.name: i for i, p in enumerate(files) if p.suffix.lower() == ".csv"}
    fee = [i for n, i in csv_pos.items() if "fee" in n.lower()]
    visits = [i for n, i in csv_pos.items() if "visit" in n.lower()]
    x12 = [p for p in files if p.suffix.lower() != ".csv"]
    assert fee and visits and max(fee) < min(i for i, p in enumerate(files) if p in x12)  # reference data first
    order = {"HC": 1, "FA": 2, "HN": 2, "HP": 3}
    gs = [order[p.read_text(encoding="ascii")[:400].split("GS*")[1][:2]] for p in x12]
    assert gs == sorted(gs)  # claims, then acknowledgements, then payments
    assert min(visits) > max(i for i, p in enumerate(files) if p in x12)  # PM feeds after the EDI they point at


def test_daily_archives_files_and_a_rerun_does_nothing(data, tmp_path):
    engine = make_engine(tmp_path / "a.sqlite")
    inbox = fresh_inbox(data, tmp_path)
    n_files = len(scan(inbox))
    rep = run_period(engine, 1, SALT, AS_OF, inbox=inbox, archive=tmp_path / "archive", start=START)
    assert rep.status == "ok" and rep.gate == "passed"
    assert (rep.files_loaded, rep.files_failed) == (n_files, 0) and rep.events_added > 0
    assert scan(inbox) == [] and len(list((tmp_path / "archive" / AS_OF.isoformat()).iterdir())) == n_files
    assert watermark(engine, 1) == AS_OF
    again = run_period(engine, 1, SALT, AS_OF, inbox=inbox, archive=tmp_path / "archive")
    assert (again.status, again.files_loaded, again.events_added) == ("ok", 0, 0)
    assert sum(v["records"] for v in again.steps.values()) == 0  # nothing new to decide
    assert last_run(engine, 1).mode == "daily"


def test_a_bad_file_goes_to_rejected_with_its_reason_and_the_gate_holds_the_run(data, tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    inbox = fresh_inbox(data, tmp_path)
    (inbox / "claims_bad.x12").write_text("this is not an x12 file", encoding="ascii")
    rep = run_period(engine, 1, SALT, AS_OF, inbox=inbox, archive=tmp_path / "archive", start=START)
    assert rep.files_failed == 1 and rep.status == "gated" and rep.gate == "failed"
    assert any("failed to load" in r for r in rep.reasons)
    bad = tmp_path / "rejected" / AS_OF.isoformat() / "claims_bad.x12"
    assert bad.exists() and bad.with_name("claims_bad.x12.reason.txt").read_text().strip()
    assert rep.steps == {} and records(engine) == Counter()  # no agent ran
    assert watermark(engine, 1) is None and last_run(engine, 1).status == "gated"
    # the operator accepts the failure: the same day now runs
    (inbox / "claims_bad2.x12").write_text("still not an x12 file", encoding="ascii")
    ok = run_period(engine, 1, SALT, AS_OF, inbox=inbox, archive=tmp_path / "archive", start=START, allow_failed=True)
    assert ok.status == "ok" and watermark(engine, 1) == AS_OF


def test_the_gate_names_a_payment_that_does_not_reconcile(tmp_path):
    engine = make_engine(tmp_path / "g.sqlite")
    b = Book(engine, 1)
    claim = b.claim("C1", "P1", "150.00", date(2026, 1, 5), date(2026, 1, 6))
    pay = b.payment("P1", date(2026, 2, 1), "T1", "100.00")  # the bank paid 100.00 ...
    b.remit(pay, claim, "1", "90.00", "10.00", [("CO", "45", "50.00")])  # ... the remits add up to 90.00
    b.commit()
    gate = check_gate(engine, 1, date(2026, 3, 1), files_failed=0)
    assert not gate.passed and any(r.startswith("payment_total") for r in gate.reasons)


# ------------------------------------------------------------------------------- incremental equals one-shot


def test_registry_covers_every_agent_once_and_the_grid_is_stable():
    names = [s.name for s in steps()]
    assert sorted(names, key=lambda n: int(n[1:])) == [f"a{i}" for i in range(1, 16)] and len(set(names)) == 15
    d = date(2026, 3, 3)
    assert grid_start(d, 7).toordinal() % 7 == 0 and 0 <= (grid_start(d, 7) - d).days < 7
    assert grid_start(grid_start(d, 28), 28) == grid_start(d, 28)  # on the grid already: unchanged


def test_two_daily_runs_equal_one_backfill(book, tmp_path):
    a = make_engine(tmp_path / "daily.sqlite")
    b = make_engine(tmp_path / "back.sqlite")
    for eng, name in ((a, "ia"), (b, "ib")):
        ingest_path(eng, 1, fresh_inbox(book, tmp_path, name), SALT)
    first, mid = SYN_AS_OF - timedelta(days=300), SYN_AS_OF - timedelta(days=120)
    r1 = run_period(a, 1, SALT, mid, mode="daily", start=first)
    r2 = run_period(a, 1, SALT, SYN_AS_OF, mode="daily")  # starts the day after the watermark
    rb = run_period(b, 1, SALT, SYN_AS_OF, mode="backfill", start=first, step_days=28)
    assert (r1.status, r2.status, rb.status) == ("ok", "ok", "ok")
    ra, rbb = payloads(a), payloads(b)  # the tower writes its own daily events by design (see daily.TOWER_DAYS)
    assert sum(ra.values()) > 0 and {k[0] for k in ra} >= {"a3_documentation", "a11_cash", "a7_ar", "a15_investigator"}
    assert ra == rbb


def test_replay_only_new_makes_exactly_the_missing_records(book, tmp_path):
    a = make_engine(tmp_path / "x.sqlite")
    b = make_engine(tmp_path / "y.sqlite")
    for eng, name in ((a, "xa"), (b, "xb")):
        ingest_path(eng, 1, fresh_inbox(book, tmp_path, name), SALT)
    cut = datetime.combine(SYN_AS_OF - timedelta(days=100), time.max)
    first = replay(a, 1, A8DenialAgent(), until=cut)
    rest = replay(a, 1, A8DenialAgent(), only_new=True)
    full = replay(b, 1, A8DenialAgent())
    assert len(first) + len(rest) == len(full) and rest and first
    assert payloads(a, skip=()) == payloads(b, skip=())
    assert replay(a, 1, A8DenialAgent(), only_new=True) == []  # a second pass finds nothing left


# ------------------------------------------------------------------------------------------------ crosswalk


def _visits_csv(path, rows):
    path.write_text(
        "visit_id,payer_id,provider_npi,patient_ref,dos,cpt,units\n"
        + "\n".join(f"{v},P1,1000000001,{pat},2026-01-05,99213,1" for v, pat in rows) + "\n",
        encoding="ascii",
    )


def test_crosswalk_merges_two_member_ids_into_one_patient(tmp_path):
    engine = make_engine(tmp_path / "c.sqlite")
    (tmp_path / "patient_crosswalk.csv").write_text("member_id,master_id\nM1,MASTER9\nM2,MASTER9\n", encoding="ascii")
    _visits_csv(tmp_path / "visits1.csv", [("V1", "M1"), ("V2", "M2"), ("V3", "M3")])
    assert ingest_file(engine, 1, tmp_path / "patient_crosswalk.csv", SALT).status == "loaded"
    assert ingest_file(engine, 1, tmp_path / "visits1.csv", SALT).status == "loaded"
    with tenant_session(engine, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.PatientRef)) == 2  # MASTER9 and M3
        refs = {v.visit_ref: v.patient_ref_id for v in s.scalars(select(m.Visit))}
    assert refs["V1"] == refs["V2"] != refs["V3"]


def test_without_a_crosswalk_member_ids_stay_separate_and_bad_rows_are_rejected(tmp_path):
    engine = make_engine(tmp_path / "d.sqlite")
    _visits_csv(tmp_path / "visits2.csv", [("V1", "M1"), ("V2", "M2")])
    ingest_file(engine, 1, tmp_path / "visits2.csv", SALT)
    with tenant_session(engine, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.PatientRef)) == 2
    (tmp_path / "crosswalk_bad.csv").write_text("member_id,master_id\nM1,A\nM1,B\n", encoding="ascii")
    res = ingest_file(engine, 1, tmp_path / "crosswalk_bad.csv", SALT)
    assert res.status == "failed" and "two different master ids" in res.reason
    (tmp_path / "crosswalk_bad2.csv").write_text("member_id,master_id\nM1,\n", encoding="ascii")
    assert ingest_file(engine, 1, tmp_path / "crosswalk_bad2.csv", SALT).status == "failed"


# ------------------------------------------------------------------------------------------------------ CLI


def test_cli_daily_status_and_backfill(data, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SALT_A", SALT)
    engine = make_engine(tmp_path / "cli.sqlite")
    url = str(engine.url)
    inbox = fresh_inbox(data, tmp_path)
    assert cli.main(["--db-url", url, "ops", "status", "--tenant", "1"]) == 0
    assert "none" in capsys.readouterr().out
    rc = cli.main(["--db-url", url, "ops", "backfill", "--inbox", str(inbox), "--from", START.isoformat(),
                   "--to", AS_OF.isoformat(), "--tenant", "1", "--go-live", (AS_OF - timedelta(days=7)).isoformat()])
    out = capsys.readouterr().out
    assert rc == 0 and "backfill run to" in out and "since go-live" in out
    assert cli.main(["--db-url", url, "ops", "status", "--tenant", "1"]) == 0
    assert str(AS_OF) in capsys.readouterr().out
    rc = cli.main(["--db-url", url, "ops", "daily", "--inbox", str(inbox), "--as-of", AS_OF.isoformat(),
                   "--tenant", "1"])  # an empty inbox: still ok, nothing to load
    assert rc == 0 and "0 loaded" in capsys.readouterr().out
