"""M19 tests: the A12 patient balance worklist (staff-facing, shadow), its feeds, and the Synthea book."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnai.model as m
from krisnai import cli
from krisnai.agents.a12_patient import (
    ACTION_TYPES,
    CREDIT_REVIEW,
    DISPUTE_REVIEW,
    EVENT_TYPE,
    FOLLOWUP_TASK,
    SMALL_BALANCE_REVIEW,
    STATEMENT_TASK,
    A12PatientAgent,
    Payment,
    Statement,
    check,
    collections,
    explain,
    format_summary,
    latest,
    summarize,
    sweep,
)
from krisnai.agents.a12_patient import rules as r
from krisnai.engine import NO_ACTION, replay, run
from krisnai.engine.card import CARD_KEYS
from krisnai.ingest.loader import ingest_path, parse_patient_payments, parse_statements
from krisnai.ingest.x12 import X12Error
from krisnai.match.engine import run_matching
from krisnai.model import tenant_session
from krisnai.synthea import build
from tests.fixtures import synthea_mini
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
CONFIRMED = date(2026, 3, 1)


def at(n: int) -> date:  # n days after the share was confirmed
    return CONFIRMED + timedelta(days=n)


def kinds(owed="100.00", statements=(), payments=(), age=40):
    return [(g.kind, g.amount, g.stage) for g in check(D(owed), CONFIRMED, list(statements), list(payments), at(age))]


SENT = Statement(at(5), "sent")


# ------------------------------------------------------------------------------------------- the rules


def test_a_balance_paid_exactly_has_nothing_open():
    assert kinds(statements=[SENT], payments=[Payment(at(20), D("100.00"))]) == []


def test_no_statement_only_once_the_first_week_has_passed():
    assert kinds(age=6) == []
    assert kinds(age=7) == [(r.NO_STATEMENT, D("100.00"), None)]


def test_an_open_balance_ages_in_stages_at_30_60_and_90_days():
    assert kinds(statements=[SENT], age=29) == []
    assert kinds(statements=[SENT], age=30) == [(r.AGING, D("100.00"), 30)]
    assert kinds(statements=[SENT], age=60) == [(r.AGING, D("100.00"), 60)]
    assert kinds(statements=[SENT], age=95) == [(r.AGING, D("100.00"), 90)]


def test_a_partial_payment_leaves_the_rest_aging():
    assert kinds(statements=[SENT], payments=[Payment(at(10), D("40.00"))], age=45) == [(r.AGING, D("60.00"), 30)]


def test_a_dispute_stops_everything_else():
    held = [SENT, Statement(at(20), "disputed")]
    assert kinds(statements=held, age=70) == [(r.DISPUTE_HOLD, D("100.00"), None)]
    assert kinds(statements=[Statement(at(20), "hardship")], age=70) == [(r.DISPUTE_HOLD, D("100.00"), None)]


def test_a_credit_and_a_small_balance_are_their_own_items():
    assert kinds(statements=[SENT], payments=[Payment(at(10), D("112.50"))]) == [(r.CREDIT, D("12.50"), None)]
    assert kinds(owed="8.00", statements=[SENT], age=60) == [(r.SMALL, D("8.00"), None)]
    assert kinds(owed="8.00", age=60) == [(r.SMALL, D("8.00"), None)]  # a small balance beats a missing statement


def test_a_payment_plan_is_not_chased_and_nothing_dated_after_the_check_is_known():
    assert kinds(statements=[SENT, Statement(at(20), "plan")], age=70) == []
    later = [SENT, Statement(at(50), "disputed")]
    assert kinds(statements=later, age=40) == [(r.AGING, D("100.00"), 30)]  # the dispute is dated after the check
    assert kinds(statements=[SENT], payments=[Payment(at(50), D("100.00"))], age=40) == [(r.AGING, D("100.00"), 30)]


def test_the_explanation_names_the_codes_and_holds_no_identifiers():
    text = explain(D("85.00"), {"1": D("25.00"), "2": D("60.00")}, D("20.00"))
    assert "deductible" in text and "coinsurance" in text and "65.00" in text
    assert explain(D("10.00"), {}).startswith("Your insurance has processed")


# ---------------------------------------------------------------------------------------- the parsers


def test_parsers_read_rows_and_reject_bad_input():
    pay = parse_patient_payments("payment_id,claim_id,paid_on,amount\nP1,C1,2026-04-01,25.00\n")
    assert pay[0]["amount"] == D("25.00") and pay[0]["method"] == "CARD"
    st = parse_statements("statement_id,claim_id,sent_on,status\nS1,C1,2026-03-10,disputed\n")
    assert st[0]["status"] == "disputed" and st[0]["channel"] == "mail"
    with pytest.raises(X12Error):
        parse_statements("statement_id,claim_id,sent_on,status\nS1,C1,2026-03-10,maybe\n")
    with pytest.raises(X12Error):
        parse_patient_payments("payment_id,claim_id\nP1,C1\n")
    with pytest.raises(X12Error):
        parse_patient_payments("payment_id,claim_id,paid_on,amount\nP1,C1,not-a-date,5\n")


# ----------------------------------------------------------------------- sweeper + agent (hand book)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    c = b.claim("C1", "P1", "300.00", date(2026, 2, 20), date(2026, 2, 22))
    pay = b.payment("P1", CONFIRMED, "TRC1", "180.00")
    b.remit(pay, c, "1", "180.00", "120.00", [("CO", "45", "0.00"), ("PR", "2", "120.00")])
    return b


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a12_patient")))


def go(b, start=at(7), end=at(60)):
    b.commit()
    sweep(b.engine, 1, start, end)
    return replay(b.engine, 1, A12PatientAgent())


def test_a_confirmed_share_with_no_statement_becomes_a_staff_task_with_a_plain_explanation(book):
    go(book, end=at(7))
    (rec,) = records(book.engine)
    p = json.loads(rec.action_payload)
    assert rec.action_type == STATEMENT_TASK and rec.outcome == "shadow" and p["owner"] == "patient_billing"
    assert D(p["amount"]) == D("120.00") and "coinsurance" in p["explanation"] and p["staff_facing"] is True
    assert set(p["card"]) == set(CARD_KEYS) and any("nothing is sent" in line for line in p["card"]["why"])


def test_each_item_goes_to_its_own_action(tmp_path):
    engine = make_engine(tmp_path / "items.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    pay = b.payment("P1", CONFIRMED, "TRC1", "500.00")
    shares = {"AGED": "120.00", "SMALL": "6.00", "CREDIT": "50.00", "HELD": "80.00"}
    for sid, pr in shares.items():
        c = b.claim(sid, "P1", "200.00", date(2026, 2, 20), date(2026, 2, 22))
        b.remit(pay, c, "1", "100.00", pr, [("PR", "1", pr)])
        b.statement("S" + sid, sid, at(5))
    b.patient_payment("PP1", "CREDIT", at(10), "62.00")
    b.statement("SD", "HELD", at(20), status="disputed")
    go(b, start=at(45), end=at(45))
    got = {json.loads(x.action_payload)["claim"]: x.action_type for x in records(engine)}
    assert got == {"AGED": FOLLOWUP_TASK, "SMALL": SMALL_BALANCE_REVIEW, "CREDIT": CREDIT_REVIEW,
                   "HELD": DISPUTE_REVIEW}  # fmt: skip


def test_a_payment_closes_the_item_with_one_closing_event(book):
    book.statement("S1", "C1", at(5))
    book.commit()
    sweep(book.engine, 1, at(35), at(35))  # 30 days: aging
    with tenant_session(book.engine, 1) as s:
        f = m.SourceFile(file_name="pp.csv", file_sha256="f" * 64, file_type="patient_payments", byte_size=1,
                         status="loaded")  # fmt: skip
        s.add(f)
        s.flush()
        s.add(m.PatientPayment(source_file_id=f.id, payment_ref="PP1", claim_submitter_id="C1", paid_on=at(40),
                               amount=D("120.00"), method="CARD"))  # fmt: skip
        s.commit()
    sweep(book.engine, 1, at(42), at(42))
    with tenant_session(book.engine, 1) as s:
        kinds_seen = [json.loads(p)["kind"] for p in s.scalars(
            select(m.Event.payload).where(m.Event.event_type == EVENT_TYPE).order_by(m.Event.id))]  # fmt: skip
    assert kinds_seen == ["balance_aging", ""]
    replay(book.engine, 1, A12PatientAgent())
    assert [x.action_type for x in records(book.engine)] == [FOLLOWUP_TASK, NO_ACTION]
    assert all(a == NO_ACTION for a, _ in latest(book.engine, 1).values())


def test_a_rerun_adds_nothing_shadow_nothing_runs_and_tenants_are_isolated(book):
    book.commit()
    first = sweep(book.engine, 1, at(7), at(7))
    assert first.events == 1 and sweep(book.engine, 1, at(7), at(7)).skipped
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == EVENT_TYPE))
    spy = SpyAdapter()
    res = run(book.engine, 1, A12PatientAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, A12PatientAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False
    assert records(book.engine, 2) == []


def test_no_action_can_contact_a_patient_refund_or_write_off():
    assert all(a.endswith(("_task", "_review")) for a in ACTION_TYPES)
    banned = ("send", "text", "sms", "call", "email", "charge_card", "payment_link", "refund", "write_off", "collect")
    assert not any(w in a for a in ACTION_TYPES for w in banned)


def test_replay_is_deterministic(tmp_path):
    def once(name):
        engine = make_engine(tmp_path / name)
        b = Book(engine, 1)
        b.engine = engine
        c = b.claim("C1", "P1", "300.00", date(2026, 2, 20), date(2026, 2, 22))
        pay = b.payment("P1", CONFIRMED, "TRC1", "180.00")
        b.remit(pay, c, "1", "180.00", "120.00", [("PR", "2", "120.00")])
        b.commit()
        sweep(engine, 1, at(7), at(7))
        return [(i.outcome, i.fingerprint) for i in replay(engine, 1, A12PatientAgent())]

    assert once("a.sqlite") == once("b.sqlite")


# ------------------------------------------------------------------------------------- Synthea book


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a12")
    raw = synthea_mini.write(root / "raw", n_claims=1200, n_patients=150, seed=5)
    as_of = date(2026, 6, 30)
    build(raw, root / "book", as_of, seed=7, patient=True)
    engine = make_engine(root / "db.sqlite")
    results = ingest_path(engine, 1, root / "book", SALT)
    run_matching(engine, 1)
    sweep(engine, 1, as_of - timedelta(days=7 * 70), as_of, repeat_days=1)
    replay(engine, 1, A12PatientAgent())
    truth = {t["key"]: t for t in csv.DictReader((root / "book" / "patient_truth.csv").open())}
    return {"root": root, "engine": engine, "truth": truth, "results": results, "as_of": as_of}


def test_patient_feeds_load_idempotently(syn):
    assert all(x.status == "loaded" for x in syn["results"])
    assert {"patient_payments", "statements"} <= {x.file_type for x in syn["results"]}
    assert all(x.status == "skipped" for x in ingest_path(syn["engine"], 1, syn["root"] / "book", SALT))


def test_every_planted_outcome_is_found_with_its_dollars_and_nothing_else(syn):
    found = {}
    for claim, (action, p) in latest(syn["engine"], 1).items():
        if action != NO_ACTION:
            found[claim] = (p["kind"], Decimal(p["amount"]), p["stage"])
    want = {k: (t["defect"], Decimal(t["amount"]), int(t["detail"]) if t["detail"] else None)
            for k, t in syn["truth"].items()}  # fmt: skip
    assert len({v[0] for v in want.values()}) >= 4
    assert found == want


def test_collections_rate_and_open_balance_are_consistent_with_the_answer_key(syn):
    c = collections(syn["engine"], 1, syn["as_of"])
    assert c["owed"] > c["collected"] > 0 and c["open"] == c["owed"] - c["collected"]  # a credit counts as owed only
    s = summarize(syn["engine"], 1, syn["as_of"])
    assert "nothing is sent to patients" in format_summary(s)
    assert s["executed"] == 0


def test_the_tower_shows_a12_cards_and_cli_replays_in_shadow(syn, tmp_path, capsys):
    from krisnai.agents.a14_tower.cards import open_cards

    cards = [c for c in open_cards(syn["engine"], 1, syn["as_of"]) if c["agent"] == "a12_patient"]
    assert cards and {c["owner"] for c in cards} == {"patient_billing"}
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a12", "replay", "--tenant", "1"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    raw = syn["root"] / "raw"
    a, b = tmp_path / "plain", tmp_path / "plain2"
    build(raw, a, syn["as_of"], seed=7)
    build(raw, b, syn["as_of"], seed=7, patient=False)
    assert not (a / "statements.csv").exists()
    digest = lambda x: {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(x.iterdir())}  # noqa: E731
    assert digest(a) == digest(b)
