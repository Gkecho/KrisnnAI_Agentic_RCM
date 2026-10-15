"""M16 tests: the A2 authorization agent in shadow mode, the authorization feed, the sweeper and the Synthea book."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnai.model as m
from krisnai import cli
from krisnai.agents.a2_authorization import (
    ACTION_TYPES,
    EVENT_TYPE,
    EXCEPTION_REVIEW,
    REQUEST_TASK,
    A2AuthorizationAgent,
    Auth,
    check,
    format_summary,
    latest_by_appointment,
    pick,
    seed_defaults,
    summarize,
    sweep,
)
from krisnai.agents.a2_authorization import rules as r
from krisnai.engine import NO_ACTION, replay, run
from krisnai.engine.card import CARD_KEYS
from krisnai.ingest.loader import ingest_path, parse_authorizations
from krisnai.ingest.x12 import X12Error
from krisnai.match.engine import run_matching
from krisnai.model import tenant_session
from krisnai.synthea import build
from tests.fixtures import synthea_mini
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
VISIT = date(2026, 6, 20)


def d(n: int) -> date:  # n days relative to the visit
    return VISIT + timedelta(days=n)


def auth(status="approved", requested=-20, decided=-15, start=-30, end=60, approved=4, used=0, units_as_of=-3):
    return Auth(status, d(requested), d(decided) if decided is not None else None,
                d(start) if start is not None else None, d(end) if end is not None else None, approved, used,
                d(units_as_of) if units_as_of is not None else None)  # fmt: skip


def kinds(a, required=True, as_of=d(-2)):
    return [g.kind for g in check(VISIT, required, a, as_of)]


# ------------------------------------------------------------------------------------------- the rules


def test_a_valid_authorization_with_units_left_has_no_gap():
    assert kinds(auth()) == []


def test_not_required_means_nothing_to_check_even_with_no_request():
    assert kinds(None, required=False) == []


def test_no_request_for_a_required_service():
    assert kinds(None) == [r.NO_AUTH]
    assert kinds(auth(requested=-1), as_of=d(-5)) == [r.NO_AUTH]  # requested after the checkpoint: not known yet


def test_pending_is_only_late_after_seven_days_and_with_the_visit_close():
    pending = dict(status="requested", decided=None, start=None, end=None, approved=None, used=None, units_as_of=None)
    assert kinds(auth(requested=-12, **pending), as_of=d(-2)) == [r.PENDING_LATE]
    assert kinds(auth(requested=-5, **pending), as_of=d(-2)) == []  # asked too recently
    assert kinds(auth(requested=-20, **pending), as_of=d(-10)) == []  # the visit is still far away


def test_a_decision_after_the_checkpoint_is_not_known_yet():
    later = auth(status="denied", decided=-1, requested=-12)
    assert kinds(later, as_of=d(-3)) == [r.PENDING_LATE]  # as of day -3 it was still undecided, 9 days old, visit in 3
    assert kinds(later, as_of=d(-1)) == [r.DENIED]


def test_denied_expired_and_units():
    assert kinds(auth(status="denied")) == [r.DENIED]
    assert kinds(auth(end=-1)) == [r.EXPIRED]
    assert kinds(auth(start=3)) == [r.EXPIRED]
    assert kinds(auth(end=0)) == []  # valid through the visit day
    assert kinds(auth(approved=2, used=2)) == [r.UNITS]
    assert kinds(auth(approved=2, used=1)) == []
    assert kinds(auth(approved=2, used=2, units_as_of=-1), as_of=d(-5)) == []  # the count is dated after the checkpoint


def test_expired_comes_before_units_when_both_apply():
    assert kinds(auth(end=-2, approved=1, used=1)) == [r.EXPIRED, r.UNITS]


def test_pick_prefers_the_authorization_whose_window_holds_the_visit():
    old = auth(requested=-90, start=-120, end=-60)
    good = auth(requested=-30, start=-30, end=60)
    assert pick([old, good], VISIT, d(-2)) is good
    assert pick([], VISIT, d(-2)) is None
    only_later = auth(requested=-1)
    assert pick([only_later], VISIT, d(-5)) is None


# ----------------------------------------------------------------------------------------- the parser


def test_authorization_parser_reads_a_row_and_rejects_bad_input():
    head = "authorization_id,payer_id,patient_ref,cpt,status,requested_on,decided_on,units_approved,units_used,units_as_of"
    rows = parse_authorizations(f"{head}\nA1,P1,M1,71046,approved,2026-06-01,2026-06-03,2,0,2026-06-10\n", "salt")
    assert rows[0]["status"] == "approved" and rows[0]["approved"] == 2 and rows[0]["decided"] == date(2026, 6, 3)
    assert len(rows[0]["patient"]) == 32 and rows[0]["start"] is None
    with pytest.raises(X12Error):
        parse_authorizations("authorization_id,payer_id\nA1,P1\n", "salt")
    with pytest.raises(X12Error):
        parse_authorizations(f"{head}\nA1,P1,M1,71046,maybe,2026-06-01,,,,\n", "salt")
    with pytest.raises(X12Error):
        parse_authorizations(f"{head}\nA1,P1,M1,71046,approved,not-a-date,,,,\n", "salt")


# ----------------------------------------------------------------------- sweeper, seed, agent (hand book)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "71046", "100.00")
    b.require_auth("P1", "71046")
    return b


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a2_authorization")))


def go(b, start=date(2026, 6, 1), end=date(2026, 6, 30)):
    b.commit()
    sweep(b.engine, 1, start, end)
    return replay(b.engine, 1, A2AuthorizationAgent())


def test_sweeper_only_raises_for_a_payer_and_cpt_that_needs_authorization(book):
    book.appointment("NEEDS", "P1", VISIT, date(2026, 6, 1), cpt="71046")
    book.appointment("PLAIN", "P1", VISIT, date(2026, 6, 1), cpt="99213")
    book.commit()
    first = sweep(book.engine, 1, date(2026, 6, 1), date(2026, 6, 30))
    assert first.events == 2 and not first.skipped  # the 7-day and 2-day checkpoint of NEEDS only
    assert sweep(book.engine, 1, date(2026, 6, 1), date(2026, 6, 30)).skipped
    with tenant_session(book.engine, 1) as s:
        refs = {json.loads(p)["appt"] for p in s.scalars(select(m.Event.payload).where(m.Event.event_type == EVENT_TYPE))}
    assert refs == {"NEEDS"}


def test_seed_loads_the_default_requirements_once_for_every_payer(tmp_path):
    engine = make_engine(tmp_path / "seed.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.payer("P1"), b.payer("P2")
    b.commit()
    with tenant_session(engine, 1) as s:
        assert seed_defaults(s) == 6
        s.commit()
    with tenant_session(engine, 1) as s:
        assert seed_defaults(s) == 0


def test_each_gap_goes_to_its_own_action(tmp_path):
    engine = make_engine(tmp_path / "gaps.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "71046", "100.00")
    b.require_auth("P1", "71046")
    cases = {"NONE": None, "DENIED": dict(status="denied", decided=date(2026, 6, 2), requested=date(2026, 6, 1)),
             "OK": dict(status="approved", decided=date(2026, 6, 2), requested=date(2026, 6, 1),
                        start=date(2026, 5, 20), end=date(2026, 8, 1), approved=4, used=0)}  # fmt: skip
    for n, (ref, spec) in enumerate(cases.items(), start=10):
        p = b._add(m.PatientRef(ref_hash=bytes([n]) * 32))
        b.appointment(ref, "P1", VISIT, date(2026, 6, 1), cpt="71046", patient=p)
        if spec:
            b.authorization("AU" + ref, "P1", "71046", patient=p, **spec)
    go(b)
    got = {json.loads(x.action_payload)["appt"]: x.action_type for x in records(engine)}
    assert got == {"NONE": REQUEST_TASK, "DENIED": EXCEPTION_REVIEW, "OK": NO_ACTION}


def test_shadow_mode_nothing_runs_and_cards_have_the_standard_shape(book):
    book.appointment("A1", "P1", VISIT, date(2026, 6, 1), cpt="71046")
    book.commit()
    sweep(book.engine, 1, date(2026, 6, 13), date(2026, 6, 13))
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == EVENT_TYPE))
    spy = SpyAdapter()
    res = run(book.engine, 1, A2AuthorizationAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, A2AuthorizationAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False
    (rec,) = records(book.engine)
    p = json.loads(rec.action_payload)
    assert rec.action_type == REQUEST_TASK and set(p["card"]) == set(CARD_KEYS) and p["owner"] == "front_desk"
    assert all(a.endswith(("_task", "_review")) for a in ACTION_TYPES)


def test_replay_is_deterministic_and_tenants_are_isolated(tmp_path):
    def once(name):
        engine = make_engine(tmp_path / name)
        b = Book(engine, 1)
        b.engine = engine
        b.fee("P1", "71046", "100.00")
        b.require_auth("P1", "71046")
        b.appointment("A1", "P1", VISIT, date(2026, 6, 1), cpt="71046")
        go(b)
        return engine, [(i.outcome, i.fingerprint) for i in replay(engine, 1, A2AuthorizationAgent())]

    (e1, a), (_, b_) = once("a.sqlite"), once("b.sqlite")
    assert a == b_ and records(e1, 2) == []


# ------------------------------------------------------------------------------------- Synthea book


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a2")
    raw = synthea_mini.write(root / "raw", n_claims=1500, n_patients=150, seed=5)
    build(raw, root / "book", date(2026, 6, 30), seed=7, eligibility=True, authorization=True)
    engine = make_engine(root / "db.sqlite")
    results = ingest_path(engine, 1, root / "book", SALT)
    run_matching(engine, 1)
    with tenant_session(engine, 1) as s:
        seed_defaults(s)
        s.commit()
    sweep(engine, 1, date(2025, 3, 1), date(2026, 6, 30))
    replay(engine, 1, A2AuthorizationAgent())
    truth = defaultdict(set)
    rows = list(csv.DictReader((root / "book" / "auth_truth.csv").open()))
    for t in rows:
        truth[t["defect"]].add(t["appointment_id"])
    return {"root": root, "engine": engine, "truth": truth, "rows": rows, "results": results}


def test_authorizations_load_idempotently(syn):
    assert all(x.status == "loaded" for x in syn["results"])
    assert "authorizations" in {x.file_type for x in syn["results"]}
    again = ingest_path(syn["engine"], 1, syn["root"] / "book", SALT)
    assert all(x.status == "skipped" for x in again)


def test_every_planted_authorization_defect_is_found_and_nothing_else(syn):
    final = latest_by_appointment(syn["engine"], 1)
    pairs = {"no_authorization": r.NO_AUTH, "expired_authorization": r.EXPIRED, "pending_late": r.PENDING_LATE,
             "units_exhausted": r.UNITS}  # fmt: skip
    for defect, kind in pairs.items():
        found = {a for a, v in final.items() if kind in v["gaps"]}
        assert len(syn["truth"][defect]) > 2, defect
        assert found == syn["truth"][defect], defect


def test_every_authorization_denial_was_flagged_before_the_visit(syn):
    truth = list(csv.DictReader((syn["root"] / "book" / "ground_truth.csv").open()))
    planted = {t["claim_id"]: t["appointment_id"] for t in syn["rows"]
               if t["defect"] in ("no_authorization", "expired_authorization")}  # fmt: skip
    denied = {t["claim_id"] for t in truth if t["issue_type"] == "denial" and t["carc"] == "197"}
    assert planted and set(planted) <= denied  # each planted lapse really became a CARC 197 denial
    final = latest_by_appointment(syn["engine"], 1)
    assert all(planted[c] in final and final[planted[c]]["gaps"] for c in planted)


def test_turnaround_and_covered_rate(syn):
    s = summarize(syn["engine"], 1)
    t = s["turnaround"]
    assert t["decided"] > 10 and 2 <= t["median_days"] <= 6 and t["pending"] == len(syn["truth"]["pending_late"])
    defects = sum(len(v) for v in syn["truth"].values())
    assert s["required_appointments"] - s["covered"] == defects
    assert "covered" in format_summary(s)


def test_the_tower_shows_a2_cards_until_the_visit_date_passes(syn):
    from krisnai.agents.a14_tower.cards import open_cards

    with tenant_session(syn["engine"], 1) as s:
        day = s.scalars(
            select(m.Event.known_at)
            .join(m.DecisionRecord, m.DecisionRecord.event_id == m.Event.id)
            .where(m.DecisionRecord.agent_id == "a2_authorization", m.DecisionRecord.action_type != NO_ACTION)
            .order_by(m.Event.known_at)
        ).first().date()
    cards = [c for c in open_cards(syn["engine"], 1, day) if c["agent"] == "a2_authorization"]
    assert cards and all(date.fromisoformat(c["deadline"]) >= day for c in cards)


def test_cli_a2_replays_in_shadow_and_default_output_is_unchanged(syn, tmp_path, capsys):
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a2", "replay", "--tenant", "1"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    raw = syn["root"] / "raw"
    a, b = tmp_path / "plain", tmp_path / "plain2"
    build(raw, a, date(2026, 6, 30), seed=7)
    build(raw, b, date(2026, 6, 30), seed=7, authorization=False)
    assert not (a / "authorizations.csv").exists()
    digest = lambda x: {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(x.iterdir())}  # noqa: E731
    assert digest(a) == digest(b)
    with pytest.raises(ValueError):
        build(raw, tmp_path / "bad", date(2026, 6, 30), seed=7, authorization=True)  # needs --eligibility
