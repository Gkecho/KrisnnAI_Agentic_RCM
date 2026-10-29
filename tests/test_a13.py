"""M18 tests: the A13 credentialing agent in shadow mode, the enrollment and screening feeds, and the Synthea book."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a13_credentialing import (
    ACTION_TYPES,
    ENROLLMENT_EVENT,
    ENROLLMENT_TASK,
    EXCEPTION_REVIEW,
    SCREENING_EVENT,
    A13CredentialingAgent,
    Enroll,
    Service,
    check_enrollment,
    check_screening,
    cycle_time,
    format_summary,
    latest,
    latest_known,
    summarize,
    sweep,
)
from krisnnai.agents.a13_credentialing import rules as r
from krisnnai.engine import NO_ACTION, replay, run
from krisnnai.engine.card import CARD_KEYS
from krisnnai.ingest.loader import ingest_path, parse_enrollments, parse_screenings
from krisnnai.ingest.x12 import X12Error
from krisnnai.match.engine import run_matching
from krisnnai.model import tenant_session
from krisnnai.synthea import build
from tests.fixtures import synthea_mini
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
TODAY = date(2026, 6, 30)


def d(n: int) -> date:  # n days from the check date
    return TODAY + timedelta(days=n)


def active(expires: int | None = 300, status_on: int = -400) -> Enroll:
    return Enroll("active", d(-450), d(-420), d(expires) if expires is not None else None, d(status_on))


def svc(*offsets: int, amount="90.00") -> list[Service]:
    return [Service(d(o), D(amount)) for o in offsets]


def kinds(enroll, services=(), as_of=TODAY):
    return [(g.kind, g.amount) for g in check_enrollment(enroll, list(services), as_of)]


# ------------------------------------------------------------------------------------------- the rules


def test_an_active_enrollment_with_a_long_expiry_is_clean():
    assert kinds(active(), svc(-5, -20)) == []


def test_no_record_is_claim_risk_only_when_there_were_services():
    assert kinds(None, svc(-5, -40)) == [(r.BILLING_WITHOUT, D("180.00"))]
    assert kinds(None, []) == []
    assert kinds(None, svc(-120)) == []  # nothing in the last 90 days


def test_expired_counts_only_services_after_the_expiry():
    e = Enroll("expired", d(-450), d(-420), d(-30), d(-30))
    assert kinds(e, svc(-45, -10, -2)) == [(r.EXPIRED, D("180.00"))]  # -45 was while it was valid
    assert kinds(e, svc(-45)) == []


def test_an_active_status_past_its_expiry_date_is_expired_too():
    assert kinds(active(expires=-3), svc(-1)) == [(r.EXPIRED, D("90.00"))]


def test_expiring_soon_inside_the_warning_window_and_on_the_day():
    assert kinds(active(expires=90)) == [(r.EXPIRING, D("0"))]
    assert kinds(active(expires=91)) == []
    assert kinds(active(expires=0)) == [(r.EXPIRING, D("0"))]  # expires today: not yet expired


def test_denied_and_terminated_count_only_work_after_the_refusal():
    denied = Enroll("denied", d(-120), None, None, d(-20))
    assert kinds(denied, svc(-40, -10)) == [(r.BILLING_WITHOUT, D("90.00"))]
    assert kinds(denied, svc(-40)) == []


def test_pending_is_chased_after_ninety_days_not_before():
    assert kinds(Enroll("pending", d(-89), None, None, d(-89))) == []
    assert kinds(Enroll("pending", d(-90), None, None, d(-90))) == [(r.PENDING_LONG, D("0"))]


def test_latest_known_status_wins_and_a_future_status_is_not_known():
    old = Enroll("active", None, d(-300), d(10), d(-300))
    new = Enroll("expired", None, None, d(10), d(5))
    assert latest_known([old, new], TODAY) is old
    assert latest_known([old, new], d(6)) is new
    assert latest_known([], TODAY) is None


def test_screening_excluded_stale_and_never():
    assert [g.kind for g in check_screening("excluded", d(-5), TODAY)] == [r.EXCLUDED]
    assert [g.kind for g in check_screening("clear", d(-35), TODAY)] == []
    assert [g.kind for g in check_screening("clear", d(-36), TODAY)] == [r.STALE_SCREEN]
    assert [g.kind for g in check_screening(None, None, TODAY)] == [r.STALE_SCREEN]


# ---------------------------------------------------------------------------------------- the parsers


def test_parsers_read_rows_and_reject_bad_status_or_dates():
    rows = parse_enrollments(
        "enrollment_id,provider_npi,payer_id,status,status_on,expires_on\nE1,1000000001,P1,active,2026-01-01,2027-01-01\n"
    )
    assert rows[0]["status"] == "active" and rows[0]["expires"] == date(2027, 1, 1) and rows[0]["submitted"] is None
    with pytest.raises(X12Error):
        parse_enrollments("enrollment_id,provider_npi,payer_id,status,status_on\nE1,1,P1,maybe,2026-01-01\n")
    with pytest.raises(X12Error):
        parse_enrollments("enrollment_id,provider_npi\nE1,1\n")
    shots = parse_screenings("screening_id,provider_npi,screened_on,result\nS1,1000000001,2026-06-01,clear\n")
    assert shots[0]["result"] == "clear" and shots[0]["source"] == "OIG"
    with pytest.raises(X12Error):
        parse_screenings("screening_id,provider_npi,screened_on,result\nS1,1,2026-06-01,unknown\n")


# ----------------------------------------------------------------------- sweeper + agent (hand book)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "100.00")
    b.screening("S0", b.provider.npi, d(-10))
    return b


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a13_credentialing")))


def go(b, start=d(-7), end=TODAY):
    b.commit()
    sweep(b.engine, 1, start, end)
    return replay(b.engine, 1, A13CredentialingAgent())


def test_a_lapsed_enrollment_with_services_becomes_a_compliance_review_with_the_dollars(book):
    npi = book.provider.npi
    book.enrollment("E1", npi, "P1", "active", d(-400), effective=d(-400), expires=d(-20))
    book.enrollment("E2", npi, "P1", "expired", d(-20), expires=d(-20))
    book.service("V1", npi, "P1", d(-10))
    book.service("V2", npi, "P1", d(-3))
    go(book)
    mine = [x for x in records(book.engine) if json.loads(x.action_payload).get("key") == f"{npi}|P1"]
    rec = mine[-1]
    p = json.loads(rec.action_payload)
    assert rec.action_type == EXCEPTION_REVIEW and rec.outcome == "shadow" and p["owner"] == "compliance_owner"
    assert D(p["amount"]) == D("200.00") and set(p["card"]) == set(CARD_KEYS)


def test_a_current_enrollment_and_screening_raise_nothing(book):
    npi = book.provider.npi
    book.enrollment("E1", npi, "P1", "active", d(-400), effective=d(-400), expires=d(400))
    book.service("V1", npi, "P1", d(-3))
    go(book)
    assert records(book.engine) == []


def test_expiring_enrollment_and_stale_screening_are_tasks_for_credentialing(tmp_path):
    engine = make_engine(tmp_path / "t.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    npi = b.provider.npi
    b.enrollment("E1", npi, "P1", "active", d(-400), effective=d(-400), expires=d(30))
    b.screening("S1", npi, d(-60))
    go(b, start=TODAY)
    got = {json.loads(x.action_payload)["key"]: x.action_type for x in records(engine)}
    assert got == {f"{npi}|P1": ENROLLMENT_TASK, npi: ENROLLMENT_TASK}


def test_an_excluded_provider_goes_to_the_compliance_owner(tmp_path):
    engine = make_engine(tmp_path / "x.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.screening("S1", b.provider.npi, d(-5), "excluded")
    go(b, start=TODAY)
    (rec,) = records(engine)
    assert rec.action_type == EXCEPTION_REVIEW and json.loads(rec.action_payload)["kind"] == "screening"


def test_a_renewed_enrollment_gets_one_closing_event_and_the_card_closes(tmp_path):
    engine = make_engine(tmp_path / "c.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    npi = b.provider.npi
    b.screening("S1", npi, d(-5))
    b.enrollment("E1", npi, "P1", "active", d(-400), effective=d(-400), expires=d(20))
    b.commit()
    sweep(engine, 1, TODAY, TODAY)  # expiring in 20 days
    with tenant_session(engine, 1) as s:  # the renewal arrives: a new status row with a far expiry
        f = m.SourceFile(file_name="renew.csv", file_sha256="e" * 64, file_type="enrollments", byte_size=1, status="loaded")
        s.add(f)
        s.flush()
        prov = s.scalars(select(m.Provider)).first()
        payer = s.scalars(select(m.Payer)).first()
        s.add(m.Enrollment(source_file_id=f.id, enrollment_ref="E2", provider_id=prov.id, payer_id=payer.id,
                           status="active", submitted_on=d(-5), effective_on=d(1), expires_on=d(800),
                           status_on=d(1)))  # fmt: skip
        s.commit()
    sweep(engine, 1, d(2), d(2))
    with tenant_session(engine, 1) as s:
        gaps = [json.loads(p)["gaps"] for p in s.scalars(
            select(m.Event.payload).where(m.Event.event_type == ENROLLMENT_EVENT).order_by(m.Event.id))]  # fmt: skip
    assert gaps == [["expiring_soon"], []]
    replay(engine, 1, A13CredentialingAgent())
    assert all(a == NO_ACTION for a, _ in latest(engine, 1).values())


def test_a_rerun_adds_nothing_shadow_nothing_runs_and_tenants_are_isolated(book):
    npi = book.provider.npi
    book.enrollment("E1", npi, "P1", "active", d(-400), effective=d(-400), expires=d(10))
    book.commit()
    assert sweep(book.engine, 1, TODAY, TODAY).events == 1 and sweep(book.engine, 1, TODAY, TODAY).skipped
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == ENROLLMENT_EVENT))
    spy = SpyAdapter()
    res = run(book.engine, 1, A13CredentialingAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, A13CredentialingAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False
    assert records(book.engine, 2) == [] and SCREENING_EVENT == "provider.screening_check"
    assert all(a.endswith(("_task", "_review")) for a in ACTION_TYPES)


def test_replay_is_deterministic(tmp_path):
    def once(name):
        engine = make_engine(tmp_path / name)
        b = Book(engine, 1)
        b.engine = engine
        b.fee("P1", "99213", "100.00")
        b.enrollment("E1", b.provider.npi, "P1", "active", d(-400), effective=d(-400), expires=d(-5))
        b.service("V1", b.provider.npi, "P1", d(-2))
        b.commit()
        sweep(engine, 1, TODAY, TODAY)
        return [(i.outcome, i.fingerprint) for i in replay(engine, 1, A13CredentialingAgent())]

    assert once("a.sqlite") == once("b.sqlite")


# ------------------------------------------------------------------------------------- Synthea book


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a13")
    raw = synthea_mini.write(root / "raw", n_claims=1500, n_patients=150, seed=5)
    as_of = date(2026, 6, 30)
    build(raw, root / "book", as_of, seed=7, documentation=True, enrollment=True)
    engine = make_engine(root / "db.sqlite")
    results = ingest_path(engine, 1, root / "book", SALT)
    run_matching(engine, 1)
    sweep(engine, 1, as_of - timedelta(days=7 * 70), as_of)
    replay(engine, 1, A13CredentialingAgent())
    truth = list(csv.DictReader((root / "book" / "credentialing_truth.csv").open()))
    return {"root": root, "engine": engine, "truth": truth, "results": results, "as_of": as_of}


def test_enrollments_and_screenings_load_idempotently(syn):
    assert all(x.status == "loaded" for x in syn["results"])
    assert {"enrollments", "screenings"} <= {x.file_type for x in syn["results"]}
    assert all(x.status == "skipped" for x in ingest_path(syn["engine"], 1, syn["root"] / "book", SALT))


def test_every_planted_credentialing_defect_is_found_and_nothing_else(syn):
    found: dict[tuple[str, str], Decimal] = {}
    for key, (action, p) in latest(syn["engine"], 1).items():
        if action == NO_ACTION:
            continue
        for g in p["gaps"]:
            found[(key, g["kind"])] = Decimal(g["amount"])
    want = {(t["key"], t["defect"]): Decimal(t["amount"]) for t in syn["truth"]}
    assert len(want) >= 4
    assert found == want


def test_lapses_produced_real_carc_185_denials_and_the_dollars_at_risk_add_up(syn):
    truth = list(csv.DictReader((syn["root"] / "book" / "ground_truth.csv").open()))
    assert any(t["issue_type"] == "denial" and t["carc"] == "185" for t in truth)
    s = summarize(syn["engine"], 1)
    expect = sum((Decimal(t["amount"]) for t in syn["truth"]), Decimal(0))
    assert s["at_risk"] == expect and "claim payment at risk" in format_summary(s)
    assert cycle_time(syn["engine"], 1)["n"] > 5


def test_the_tower_shows_a13_cards_and_cli_replays_in_shadow(syn, tmp_path, capsys):
    from krisnnai.agents.a14_tower.cards import open_cards

    cards = [c for c in open_cards(syn["engine"], 1, syn["as_of"]) if c["agent"] == "a13_credentialing"]
    assert cards and {c["owner"] for c in cards} <= {"credentialing", "compliance_owner"}
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a13", "replay", "--tenant", "1"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    raw = syn["root"] / "raw"
    a, b = tmp_path / "plain", tmp_path / "plain2"
    build(raw, a, syn["as_of"], seed=7)
    build(raw, b, syn["as_of"], seed=7, enrollment=False)
    assert not (a / "enrollments.csv").exists()
    digest = lambda x: {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(x.iterdir())}  # noqa: E731
    assert digest(a) == digest(b)
    with pytest.raises(ValueError):
        build(raw, tmp_path / "bad", syn["as_of"], seed=7, enrollment=True)  # needs --documentation
