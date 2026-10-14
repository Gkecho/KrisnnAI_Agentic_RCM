"""M12 tests: the A10 contract and underpayment agent in shadow mode, on hand-built payments and the Synthea book."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnai.model as m
from krisnai import cli
from krisnai.agents.a10_underpay import (
    ACTION_TYPES,
    CONTRACT_CHECK_TASK,
    DISPUTE_REVIEW,
    A10UnderpaymentAgent,
    cause_of,
    format_patterns,
    format_summary,
    patterns,
    summarize,
)
from krisnai.engine import NO_ACTION, replay, run
from krisnai.engine.card import CARD_KEYS
from krisnai.ingest.loader import ingest_path
from krisnai.match.engine import run_matching
from krisnai.model import tenant_session
from krisnai.synthea import build
from tests.fixtures import synthea_mini
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
JAN10, JUN1, JUN10 = date(2026, 1, 10), date(2026, 6, 1), date(2026, 6, 10)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "100.00")
    return b


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a10_underpay")))


def go(b):
    b.commit()
    return replay(b.engine, 1, A10UnderpaymentAgent())


def pay(b, sid, paid, pr, cas, cpt="99213", status="1", known=JUN10, dos=JAN10):
    claim = b.claim(sid, "P1", "150.00", dos, JUN1)
    p = b.payment("P1", known, "T" + sid, paid)
    b.remit(p, claim, status, paid, pr, cas, cpt=cpt)
    return claim


def only(engine):
    (rec,) = records(engine)
    return rec, json.loads(rec.action_payload)


# ------------------------------------------------------------------------------------ the contract check


def test_a_payment_that_matches_the_contract_needs_no_action(book):
    pay(book, "C1", "90.00", "10.00", [("CO", "45", "50.00"), ("PR", "2", "10.00")])  # 100 allowed = 90 + 10
    go(book)
    rec, _ = only(book.engine)
    assert rec.action_type == NO_ACTION


def test_a_payment_short_of_the_contract_gets_one_dispute_review_for_the_exact_gap(book):
    pay(book, "C1", "65.00", "10.00", [("CO", "45", "75.00"), ("PR", "2", "10.00")])  # allowed 100, paid 65 + 10
    go(book)
    rec, p = only(book.engine)
    assert rec.action_type == DISPUTE_REVIEW and rec.outcome == "shadow"
    assert p["total_gap"] == "25.00" and p["causes"] == ["contract_pricing"] and p["owner"] == "finance"
    assert p["pricing_basis"] == "fee_schedule" and p["deadline"] == "2026-12-07"  # payment + 180 days
    assert set(p["card"]) == set(CARD_KEYS) and Decimal(p["card"]["expected_value"]) == D("25.00")


def test_the_patient_share_already_taken_off_the_line_is_not_counted_as_a_gap(book):
    pay(book, "C1", "80.00", "20.00", [("CO", "45", "50.00"), ("PR", "2", "20.00")])  # 80 + 20 = 100
    go(book)
    assert only(book.engine)[0].action_type == NO_ACTION


def test_a_fee_row_that_was_not_yet_effective_at_the_service_date_is_not_used(tmp_path):
    engine = make_engine(tmp_path / "pit.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "100.00", effective=date(2026, 6, 1))  # after the January visit
    pay(b, "C1", "40.00", "10.00", [("CO", "45", "100.00"), ("PR", "2", "10.00")])
    go(b)
    rec, _ = only(b.engine)
    assert rec.action_type == NO_ACTION  # against the June 100.00 row this would be a 50.00 gap; it is not used


# ------------------------------------------------------------------------------- no contract: payer history


def test_without_a_fee_row_a_big_gap_against_payer_history_is_a_contract_check_not_a_dispute(book):
    for i in range(3):  # history: this payer pays 80 per unit for 97110
        pay(book, f"H{i}", "72.00", "8.00", [("CO", "45", "70.00"), ("PR", "2", "8.00")], cpt="97110")
    pay(book, "BIG", "30.00", "8.00", [("CO", "45", "112.00"), ("PR", "2", "8.00")], cpt="97110", known=date(2026, 6, 20))
    go(book)
    flagged = [json.loads(r.action_payload) for r in records(book.engine) if r.action_type != NO_ACTION]
    assert [r.action_type for r in records(book.engine) if r.action_type != NO_ACTION] == [CONTRACT_CHECK_TASK]
    assert flagged[0]["pricing_basis"] == "fallback" and flagged[0]["card"]["expected_value"] == "0.00"


def test_without_a_fee_row_a_small_gap_against_payer_history_is_ignored(book):
    for i in range(3):
        pay(book, f"H{i}", "72.00", "8.00", [("CO", "45", "70.00"), ("PR", "2", "8.00")], cpt="97110")
    pay(book, "SMALL", "66.00", "8.00", [("CO", "45", "76.00"), ("PR", "2", "8.00")], cpt="97110", known=date(2026, 6, 20))
    go(book)
    assert all(r.action_type == NO_ACTION for r in records(book.engine))


# --------------------------------------------------------------------------------------------- the cause


def test_cause_comes_from_the_carc_on_the_short_line():
    pr = ("PR", "2", D("10"))
    assert cause_of([("CO", "45", D("50")), pr]) == ("contract_pricing", True)
    assert cause_of([("CO", "45", D("50")), ("CO", "4", D("20"))]) == ("modifiers", True)
    assert cause_of([("CO", "97", D("20")), ("CO", "45", D("5"))]) == ("bundling_ncci", True)
    assert cause_of([("CO", "45", D("5")), ("CO", "999", D("20"))]) == ("data_coding", False)


def test_an_unrecognised_cause_lowers_confidence(book):
    pay(book, "C1", "55.00", "10.00", [("CO", "45", "30.00"), ("CO", "999", "20.00"), ("PR", "2", "10.00")])
    go(book)
    rec, p = only(book.engine)
    assert rec.action_type == DISPUTE_REVIEW and p["causes"] == ["data_coding"]
    assert rec.confidence == D("0.6000")


# ---------------------------------------------------------------------------------------- scope and engine


def test_denials_and_reversals_are_left_to_a8(book):
    pay(book, "DEN", "0.00", "0.00", [("CO", "16", "150.00")], status="4")
    pay(book, "REV", "-90.00", "0.00", [("CO", "45", "10.00")], status="22", known=date(2026, 6, 15))
    assert go(book) == []
    assert records(book.engine) == []


def test_shadow_mode_nothing_runs_and_a_rerun_creates_nothing(book):
    pay(book, "C1", "65.00", "10.00", [("CO", "45", "75.00"), ("PR", "2", "10.00")])
    book.commit()
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == "835.remit"))
    spy = SpyAdapter()
    res = run(book.engine, 1, A10UnderpaymentAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, A10UnderpaymentAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == []
    assert again.created is False and again.record_id == res.record_id and len(records(book.engine)) == 1


def test_replay_is_deterministic(tmp_path):
    def run_once(name):
        engine = make_engine(tmp_path / name)
        b = Book(engine, 1)
        b.engine = engine
        b.fee("P1", "99213", "100.00")
        pay(b, "C1", "65.00", "10.00", [("CO", "45", "75.00"), ("PR", "2", "10.00")])
        pay(b, "C2", "90.00", "10.00", [("CO", "45", "50.00"), ("PR", "2", "10.00")], known=date(2026, 6, 12))
        b.commit()
        return [(i.outcome, i.fingerprint) for i in replay(engine, 1, A10UnderpaymentAgent())]

    assert run_once("a.sqlite") == run_once("b.sqlite")


def test_no_action_type_can_submit_write_off_refund_or_change_a_code():
    assert all(a.endswith(("_task", "_review")) for a in ACTION_TYPES)
    assert not any(w in a for a in ACTION_TYPES for w in ("write_off", "refund", "adjust", "code", "void", "submit"))


def test_tenant_isolation_a_second_tenant_sees_none_of_it(book):
    pay(book, "C1", "65.00", "10.00", [("CO", "45", "75.00"), ("PR", "2", "10.00")])
    go(book)
    assert len(records(book.engine, 1)) == 1 and records(book.engine, 2) == []


# ------------------------------------------------------------------------------------ the Synthea book


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a10")
    raw = synthea_mini.write(root / "raw", n_claims=900, n_patients=120, seed=5)
    cut = "SYNMEDICARE:99213:2026-01-01:12"
    report = build(raw, root / "book", date(2026, 6, 30), seed=7, rate_cuts=[cut])
    engine = make_engine(root / "db.sqlite")
    ingest_path(engine, 1, root / "book", SALT)
    run_matching(engine, 1)
    items = replay(engine, 1, A10UnderpaymentAgent())
    return {"root": root, "engine": engine, "report": report, "items": items,
            "truth": list(csv.DictReader((root / "book" / "ground_truth.csv").open()))}  # fmt: skip


def flagged_lines(engine):
    out = {}
    for r in records(engine):
        if r.action_type == NO_ACTION:
            continue
        p = json.loads(r.action_payload)
        for ln in p["lines"]:
            out[(p["claim"], ln["line_number"])] = Decimal(ln["gap"])
    return out


def test_every_planted_underpayment_is_found_with_the_planted_gap_and_nothing_else(syn):
    truth = {
        (t["claim_id"], int(t["line_no"])): Decimal(t["expected_amount"])
        for t in syn["truth"] if t["issue_type"] == "underpayment"
    }  # fmt: skip
    found = flagged_lines(syn["engine"])
    assert len(truth) > 20
    assert found == truth  # same lines, same dollars to the cent: nothing missed, nothing extra
    assert all(r.outcome in ("shadow", "no_action") for r in records(syn["engine"]))


def test_the_planted_payer_rate_change_comes_out_as_one_pattern(syn):
    items = patterns(syn["engine"], 1)
    top = [p for p in items if p["payer"] == "SYNMEDICARE" and p["cpt"] == "99213"]
    assert len(top) == 1 and top[0]["lines"] >= 10
    assert abs(Decimal(top[0]["median_gap_pct"]) - D("0.12")) <= D("0.001")  # the planted 12% cut
    assert top[0]["cause"] == "contract_pricing"
    text = format_patterns(items, 1)
    assert "rate change" in text and "SYNMEDICARE" in text


def test_the_summary_and_the_a15_diagnostic_agree_on_the_dollars(syn, tmp_path, capsys):
    summary = summarize(syn["engine"], 1)
    truth_total = sum(
        (Decimal(t["expected_amount"]) for t in syn["truth"] if t["issue_type"] == "underpayment"), Decimal(0)
    )
    assert summary["totals"]["short"] == truth_total and summary["totals"]["executed"] == 0
    assert "short-paid" in format_summary(summary)
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a10", "patterns", "--tenant", "1"]) == 0
    assert "A10 patterns" in capsys.readouterr().out


def test_a14_tower_lists_a10_cards_in_the_decision_inbox(syn):
    from krisnai.agents.a14_tower.cards import open_cards

    cards = open_cards(syn["engine"], 1, date(2026, 6, 30))
    mine = [c for c in cards if c["agent"] == "a10_underpay"]
    assert mine and all(set(c["card"]) == set(CARD_KEYS) and c["owner"] == "finance" for c in mine)
    by_claim = defaultdict(int)
    for c in mine:
        by_claim[c["claim"]] += 1
    assert max(by_claim.values()) == 1  # one open card per claim
