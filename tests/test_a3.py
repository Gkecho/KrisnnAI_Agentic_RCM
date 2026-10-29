"""M13 tests: the A3 documentation completeness agent in shadow mode, rules, sweeper, loader and the Synthea book."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a3_documentation import (
    ACTION_TYPES,
    CHARGE_REVIEW,
    EVENT_TYPE,
    MISSING_NOTE_TASK,
    NOTE_QUERY_TASK,
    SIGNATURE_TASK,
    A3DocumentationAgent,
    Note,
    charge_lag,
    check,
    format_summary,
    open_visits,
    summarize,
    sweep,
)
from krisnnai.agents.a3_documentation import rules as r
from krisnnai.engine import NO_ACTION, replay, run
from krisnnai.engine.card import CARD_KEYS
from krisnnai.ingest.loader import ingest_path, parse_charges, parse_notes
from krisnnai.ingest.x12 import X12Error
from krisnnai.match.engine import run_matching
from krisnnai.model import tenant_session
from krisnnai.synthea import build
from tests.fixtures import synthea_mini
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
DOS = date(2026, 6, 1)


def day(n: int) -> date:  # n days after the service
    return date.fromordinal(DOS.toordinal() + n)


def note(signed: int | None = 1, elements=("assessment", "plan"), minutes=None, started=0) -> Note:
    return Note(day(started), day(signed) if signed is not None else None, minutes, tuple(elements))


# ------------------------------------------------------------------------------------------- the rules


def kinds(**kw) -> list[str]:
    args = {"service_date": DOS, "cpt": "99213", "note": note(), "charge_dates": [day(1)], "billed": False,
            "as_of": day(10)}  # fmt: skip
    args.update(kw)
    return [g.kind for g in check(**args)]


def test_a_complete_signed_charged_visit_has_no_gap():
    assert kinds() == []


def test_no_note_only_once_it_is_due():
    assert kinds(note=None, charge_dates=[], as_of=day(2)) == []
    assert kinds(note=None, charge_dates=[], as_of=day(3)) == [r.NO_NOTE]


def test_unsigned_note_only_once_it_is_due_and_a_later_signature_is_not_known_yet():
    assert kinds(note=note(signed=None), as_of=day(2)) == []
    assert kinds(note=note(signed=None), as_of=day(4)) == [r.UNSIGNED]
    assert kinds(note=note(signed=8), as_of=day(5)) == [r.UNSIGNED]  # signed on day 8: unknown on day 5
    assert kinds(note=note(signed=8), as_of=day(9)) == []


def test_missing_required_elements_and_timed_service_minutes():
    assert kinds(note=note(elements=("assessment",))) == [r.MISSING_ELEMENTS]
    assert kinds(cpt="71046", note=note(elements=("procedure_note",)), charge_dates=[day(1)]) == []
    assert kinds(cpt="97110", note=note(elements=("procedure_note",), minutes=None)) == [r.MISSING_MINUTES]
    assert kinds(cpt="97110", note=note(elements=("procedure_note",), minutes=30)) == []


def test_documented_visit_without_a_charge_is_a_missed_charge_unless_the_claim_is_out():
    assert kinds(charge_dates=[], as_of=day(10)) == [r.NO_CHARGE]
    assert kinds(charge_dates=[], billed=True) == []
    assert kinds(charge_dates=[], as_of=day(3)) == []  # not late yet
    assert kinds(charge_dates=[day(12)], as_of=day(10)) == [r.NO_CHARGE]  # entered later: not known on day 10


def test_a_late_charge_is_reported_as_lag_but_is_not_work_for_a_person():
    gaps = check(DOS, "99213", note(), [day(6)], False, day(10))
    assert [g.kind for g in gaps] == [r.CHARGE_LAG] and not gaps[0].actionable


def test_gaps_come_out_money_first_then_missing_note_then_signature_then_content():
    gaps = kinds(note=note(signed=None, elements=("plan",)), charge_dates=[], as_of=day(10))
    assert gaps == [r.NO_CHARGE, r.UNSIGNED, r.MISSING_ELEMENTS]


# ------------------------------------------------------------------------------------ the sweeper + agent


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "100.00")
    return b


def events(engine):
    with tenant_session(engine, 1) as s:
        return [json.loads(p) for p in s.scalars(
            select(m.Event.payload).where(m.Event.event_type == EVENT_TYPE).order_by(m.Event.id))]  # fmt: skip


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a3_documentation")))


def go(b, start=day(10), end=day(10), every=7):
    b.commit()
    sweep(b.engine, 1, start, end, every)
    return replay(b.engine, 1, A3DocumentationAgent())


def test_no_note_sweeps_to_a_provider_task_with_the_visit_valued(book):
    book.visit("V1", "P1", DOS)
    go(book)
    (rec,) = records(book.engine)
    p = json.loads(rec.action_payload)
    assert rec.action_type == MISSING_NOTE_TASK and rec.outcome == "shadow"
    assert p["owner"] == "provider" and D(p["amount"]) == D("100.00")  # fee row; no payment history, so no share
    assert set(p["card"]) == set(CARD_KEYS)


def test_documented_unbilled_visit_goes_to_the_biller_as_a_charge_review(book):
    book.visit("V1", "P1", DOS)
    book.note("V1", DOS, DOS)
    go(book)
    (rec,) = records(book.engine)
    assert rec.action_type == CHARGE_REVIEW and json.loads(rec.action_payload)["owner"] == "biller"


def test_each_gap_goes_to_its_own_owner_and_action(book):
    book.visit("V1", "P1", DOS)  # note never signed
    book.note("V1", DOS, None)
    book.charge("C1", "V1", day(1))
    book.visit("V2", "P1", DOS)  # plan missing
    book.note("V2", DOS, DOS, elements="assessment")
    book.charge("C2", "V2", day(1))
    book.visit("V3", "P1", DOS)  # no note at all
    book.charge("C3", "V3", day(1))
    go(book)
    got = {json.loads(x.action_payload)["visit"]: x.action_type for x in records(book.engine)}
    assert got == {"V1": SIGNATURE_TASK, "V2": NOTE_QUERY_TASK, "V3": MISSING_NOTE_TASK}


def test_a_note_query_for_missing_elements_names_the_element_and_never_a_code(book):
    book.visit("V1", "P1", DOS)
    book.note("V1", DOS, DOS, elements="assessment")
    book.charge("C1", "V1", day(1))
    go(book)
    (rec,) = records(book.engine)
    assert rec.action_type == NOTE_QUERY_TASK
    text = json.dumps(json.loads(rec.action_payload)["card"])
    assert "plan" in text and "99213" not in json.loads(rec.action_payload)["card"]["next_steps"][-1]


def test_a_visit_that_comes_clean_gets_one_closing_event_and_its_card_closes(book):
    book.visit("V1", "P1", DOS)
    book.commit()
    sweep(book.engine, 1, day(10), day(10))  # gap: no note
    with tenant_session(book.engine, 1) as s:  # the provider writes and signs the note, a charge is keyed
        f = m.SourceFile(file_name="late.csv", file_sha256="b" * 64, file_type="notes", byte_size=1, status="loaded")
        s.add(f)
        s.flush()
        s.add(m.VisitNote(source_file_id=f.id, visit_ref="V1", note_date=day(11), signed_date=day(11),
                          elements="assessment,plan"))  # fmt: skip
        s.add(m.Charge(source_file_id=f.id, charge_ref="C1", visit_ref="V1", cpt="99213", units=D(1),
                       entered_date=day(11)))  # fmt: skip
        s.commit()
    sweep(book.engine, 1, day(12), day(12))
    evs = events(book.engine)
    assert [e["gaps"] for e in evs] == [["no_note"], []]  # raised, then closed
    replay(book.engine, 1, A3DocumentationAgent())
    assert open_visits(book.engine, 1) == {}
    assert [x.action_type for x in records(book.engine)] == [MISSING_NOTE_TASK, NO_ACTION]


def test_an_open_gap_comes_back_every_seven_days_and_a_rerun_adds_nothing(book):
    book.visit("V1", "P1", DOS)
    book.commit()
    first = sweep(book.engine, 1, day(10), day(31), every_days=7)
    assert first.events == 4 and not first.skipped  # days 10, 17, 24, 31: each is 7 days after the last
    again = sweep(book.engine, 1, day(10), day(31), every_days=7)
    assert again.skipped and again.events == 0


def test_shadow_mode_nothing_runs_and_the_action_types_are_tasks_or_reviews(book):
    book.visit("V1", "P1", DOS)
    book.commit()
    sweep(book.engine, 1, day(10), day(10))
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == EVENT_TYPE))
    spy = SpyAdapter()
    res = run(book.engine, 1, A3DocumentationAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, A3DocumentationAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False
    assert all(a.endswith(("_task", "_review")) for a in ACTION_TYPES)
    assert not any(w in a for a in ACTION_TYPES for w in ("write_off", "refund", "adjust", "code", "void", "submit"))


def test_tenant_isolation(book):
    book.visit("V1", "P1", DOS)
    go(book)
    assert len(records(book.engine, 1)) == 1 and records(book.engine, 2) == []


# ------------------------------------------------------------------------------------------- the loader


def test_notes_and_charges_parsers_read_the_columns_and_reject_bad_input():
    rows = parse_notes("visit_id,note_date,signed_date,minutes,elements\nV1,2026-06-01,,30,\"assessment, plan\"\n")
    assert rows == [{"ref": "V1", "note_date": date(2026, 6, 1), "signed": None, "minutes": 30,
                     "elements": "assessment,plan"}]  # fmt: skip
    assert parse_charges("charge_id,visit_id,cpt,units,entered_date\nC1,V1,99213,1,2026-06-02\n")[0]["units"] == D(1)
    with pytest.raises(X12Error):
        parse_notes("visit_id,note_date\nV1,2026-06-01\n")
    with pytest.raises(X12Error):
        parse_charges("charge_id,visit_id,cpt,units,entered_date\nC1,V1,99213,1,not-a-date\n")


# --------------------------------------------------------------------------------------- Synthea book


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a3")
    raw = synthea_mini.write(root / "raw", n_claims=900, n_patients=120, seed=5)
    build(raw, root / "book", date(2026, 6, 30), seed=7, documentation=True)
    engine = make_engine(root / "db.sqlite")
    results = ingest_path(engine, 1, root / "book", SALT)
    run_matching(engine, 1)
    sweep(engine, 1, date(2026, 4, 1), date(2026, 6, 30))
    replay(engine, 1, A3DocumentationAgent())
    truth = defaultdict(set)
    for t in csv.DictReader((root / "book" / "doc_truth.csv").open()):
        truth[t["defect"]].add(t["visit_id"])
    return {"root": root, "engine": engine, "truth": truth, "results": results}


def test_notes_charges_and_all_visits_load_idempotently(syn):
    assert all(x.status == "loaded" for x in syn["results"])
    types = {x.file_type for x in syn["results"]}
    assert {"notes", "charges", "visits"} <= types
    again = ingest_path(syn["engine"], 1, syn["root"] / "book", SALT)
    assert all(x.status == "skipped" for x in again)


def test_every_planted_documentation_defect_is_found_and_nothing_else(syn):
    open_ = open_visits(syn["engine"], 1)
    found = defaultdict(set)
    for ref, gap_kinds in open_.items():
        for k in gap_kinds:
            found[k].add(ref)
    pairs = {"missing_note": "no_note", "unsigned_note": "unsigned_note", "missing_element": "missing_elements",
             "missed_charge": "no_charge"}  # fmt: skip
    for defect, kind in pairs.items():
        assert len(syn["truth"][defect]) > 5
        assert found[kind] == syn["truth"][defect], defect


def test_charge_lag_kpi_matches_the_planted_lags(syn):
    lag = charge_lag(syn["engine"], 1, date(2026, 6, 30))
    assert set(lag["late_visits"]) == syn["truth"]["charge_lag"] and lag["median_days"] <= 2


def test_missed_charge_dollars_equal_the_unbilled_visit_dollars_in_the_a15_truth(syn):
    summary = summarize(syn["engine"], 1, date(2026, 6, 30))
    truth_rows = list(csv.DictReader((syn["root"] / "book" / "doc_truth.csv").open()))
    expect = sum((D(t["expected_amount"]) for t in truth_rows if t["defect"] == "missed_charge"), D(0))
    assert summary["totals"]["missed_charge"] == expect and summary["totals"]["executed"] == 0
    assert "charge lag" in format_summary(summary)


def test_a15_still_finds_exactly_the_planted_unbilled_visits_when_all_visits_are_loaded(syn):
    truth = list(csv.DictReader((syn["root"] / "book" / "ground_truth.csv").open()))
    planted = {t["visit_id"] for t in truth if t["issue_type"] == "unbilled_visit"}
    with tenant_session(syn["engine"], 1) as s:
        n_visits = s.scalar(select(func.count()).select_from(m.Visit))
    assert n_visits > len(planted) * 5
    from krisnnai.agents.a15_lite.detect import detect
    from krisnnai.agents.a15_lite.snapshot import load_snapshot

    snap = load_snapshot(syn["engine"], 1, date(2026, 6, 30))
    found = {f.visit for f in detect(snap) if f.type == "unbilled_visit"}
    assert found == planted


def test_the_tower_shows_a3_cards_keyed_by_visit(syn):
    from krisnnai.agents.a14_tower.cards import open_cards

    mine = [c for c in open_cards(syn["engine"], 1, date(2026, 6, 30)) if c["agent"] == "a3_documentation"]
    assert mine and {c["owner"] for c in mine} <= {"provider", "biller"}
    assert len({c["claim"] for c in mine}) == len(mine)  # one card per visit


def test_cli_a3_runs_in_shadow_and_default_synthea_output_is_unchanged(syn, tmp_path, capsys):
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a3", "replay", "--tenant", "1", "--as-of", "2026-06-30"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    raw = syn["root"] / "raw"
    a, b = tmp_path / "plain", tmp_path / "plain2"
    build(raw, a, date(2026, 6, 30), seed=7)
    build(raw, b, date(2026, 6, 30), seed=7, documentation=False)
    assert not (a / "notes.csv").exists()
    digest = lambda d: {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(d.iterdir())}  # noqa: E731
    assert digest(a) == digest(b)
