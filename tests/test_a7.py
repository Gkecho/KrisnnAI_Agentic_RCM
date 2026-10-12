"""M9 tests: the A7 AR follow-up agent in shadow mode, on hand-built claims and on the synthetic open-AR set."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

import krisnai.model as m
from krisnai import cli
from krisnai.agents.a7_ar import (
    ACTION_TYPES,
    EVENT_TYPE,
    A7ArAgent,
    aging_bucket,
    format_inbox,
    format_summary,
    inbox,
    summarize,
    sweep,
    timing,
)
from krisnai.engine import NO_ACTION, fingerprint, replay, run
from krisnai.ingest.loader import ingest_path
from krisnai.match.engine import run_matching
from krisnai.model import tenant_session
from tests.fixtures import make_synthetic as ms
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
TODAY = date(2026, 6, 30)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    return b


def events(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return [(e.id, e.known_at.date(), json.loads(e.payload)) for e in
                s.scalars(select(m.Event).where(m.Event.event_type == EVENT_TYPE).order_by(m.Event.id))]  # fmt: skip


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).order_by(m.DecisionRecord.id)))


def by_claim(engine, tenant=1):
    """Latest record per claim."""
    return {json.loads(r.action_payload)["claim"]: r for r in records(engine, tenant)}


def go(b, start=TODAY, end=TODAY, every=7):
    b.commit()
    sweep(b.engine, 1, start, end, every)
    return replay(b.engine, 1, A7ArAgent())


def pay(b, claim, known, amount="100.00"):
    p = b.payment("P1", known, "T" + claim.claim_submitter_id, amount)
    b.remit(p, claim, "1", amount, "0.00", [])


# ------------------------------------------------------------------------------------------- sweeper


def test_sweep_raises_an_event_only_for_an_overdue_claim_nobody_has_answered(book):
    book.claim("OPEN1", "P1", "150.00", date(2026, 2, 1), date(2026, 3, 1))  # 121 days, no answer
    paid = book.claim("PAID1", "P1", "150.00", date(2026, 2, 1), date(2026, 3, 1))
    pay(book, paid, date(2026, 3, 20))
    book.claim("NEW1", "P1", "150.00", date(2026, 6, 1), date(2026, 6, 20))  # 10 days: not due yet
    book.commit()
    res = sweep(book.engine, 1, TODAY, TODAY)
    assert res.events == 1 and not res.skipped
    ((_, known, payload),) = events(book.engine)
    assert payload["claim"] == "OPEN1" and known == TODAY and payload["age_days"] == 121 and payload["round"] == 1
    assert "patient" not in json.dumps(payload).lower()


def test_sweep_twice_adds_nothing_and_an_open_claim_comes_back_every_14_days(book):
    book.claim("OPEN1", "P1", "150.00", date(2026, 2, 1), date(2026, 3, 1))
    book.commit()
    first = sweep(book.engine, 1, date(2026, 6, 1), TODAY, 7)
    again = sweep(book.engine, 1, date(2026, 6, 1), TODAY, 7)
    assert first.events == 3 and again.skipped and again.events == 0
    assert [(k, p["round"]) for _, k, p in events(book.engine)] == [
        (date(2026, 6, 1), 1), (date(2026, 6, 15), 2), (date(2026, 6, 29), 3)
    ]  # fmt: skip
    overlap = sweep(book.engine, 1, date(2026, 6, 15), TODAY, 7)  # a different sweep that overlaps the first
    assert overlap.events == 0 and len(events(book.engine)) == 3


def test_a_payers_own_history_sets_the_expected_date(book):
    for i in range(5):  # five P1 claims, each paid 10 days after submission
        c = book.claim(f"H{i}", "P1", "100.00", date(2026, 1, 1), date(2026, 1, 10))
        pay(book, c, date(2026, 1, 20))
    book.claim("LATE1", "P1", "150.00", date(2026, 5, 1), date(2026, 6, 10))  # 20 days old
    pid = book.payers["P1"].id
    book.commit()
    with tenant_session(book.engine, 1) as s:
        assert timing.expected_days(s, pid, date(2026, 6, 30)) == (10, "history n=5")
        assert timing.expected_days(s, pid, date(2026, 1, 15))[1].startswith("default")  # payments not known yet
    sweep(book.engine, 1, TODAY, TODAY)
    raised = events(book.engine)
    assert [p["claim"] for _, _, p in raised] == ["LATE1"] and raised[0][2]["expected_days"] == 10


# ------------------------------------------------------------------------------------------- agent


def test_an_acknowledged_unpaid_claim_gets_a_status_check_card(book):
    c = book.claim("S1", "P1", "150.00", date(2026, 4, 20), date(2026, 5, 10))  # 51 days
    book.ack_277ca(c, "A2", date(2026, 5, 12))
    go(book)
    rec = by_claim(book.engine)["S1"]
    p = json.loads(rec.action_payload)
    assert rec.action_type == "a7_status_check_task" and p["issue"] == "no_response" and p["owner"] == "billing"
    assert p["aging_bucket"] == "31-60" and p["amount"] == "150.00" and p["pricing_basis"] == "billed_fallback"
    card = p["card"]
    assert set(card) == {"title", "why", "priority", "expected_value", "deadline", "owner", "next_steps", "evidence"}
    assert "S1" in card["title"] and card["next_steps"] and any("usually pays" in w for w in card["why"])
    assert [e["rule"] for e in card["evidence"]] == [
        "claim_open", "past_expected_date", "acknowledged", "amount_priced", "history_sufficient"
    ]  # fmt: skip


def test_a_claim_returned_by_the_277ca_goes_to_resubmit_review(book):
    c = book.claim("R1", "P1", "150.00", date(2026, 4, 20), date(2026, 5, 10))
    book.ack_277ca(c, "A3", date(2026, 5, 12))
    go(book)
    p = json.loads(by_claim(book.engine)["R1"].action_payload)
    assert by_claim(book.engine)["R1"].action_type == "a7_resubmit_review" and p["issue"] == "returned_by_277ca"
    assert any("277CA returned" in w for w in p["card"]["why"])


def test_a_very_old_unanswered_claim_goes_to_the_ar_lead(book):
    book.claim("E1", "P1", "150.00", date(2026, 2, 1), date(2026, 3, 1))  # 121 days
    go(book)
    rec = by_claim(book.engine)["E1"]
    assert rec.action_type == "a7_escalate_review" and json.loads(rec.action_payload)["owner"] == "ar_lead"
    assert json.loads(rec.action_payload)["aging_bucket"] == "90+"


def test_a_claim_the_payer_already_answered_is_not_a7s_and_a_later_payment_does_not_leak(book):
    answered = book.claim("A1", "P1", "150.00", date(2026, 4, 20), date(2026, 5, 10))
    pay(book, answered, date(2026, 6, 10))
    book.event(date(2026, 6, 20), EVENT_TYPE, st02="x", gs06="x",
               payload={"claim_id": answered.id, "claim": "A1", "payer_id": answered.payer_id, "due_on": "2026-06-20",
                        "age_days": 41, "expected_days": 30, "round": 1})  # fmt: skip
    later = book.claim("L1", "P1", "150.00", date(2026, 4, 20), date(2026, 5, 10))
    pay(book, later, date(2026, 7, 15))  # paid after the sweep date: unknown on 06-30
    go(book)
    recs = by_claim(book.engine)
    assert recs["A1"].action_type == NO_ACTION and "not an A7 claim" in recs["A1"].action_payload
    assert recs["L1"].action_type == "a7_status_check_task"


def test_priority_ranks_dollars_and_filing_risk_and_the_inbox_lists_each_claim_once(book):
    book.claim("BIG", "P1", "900.00", date(2026, 4, 1), date(2026, 5, 1))
    book.claim("SMALL", "P1", "100.00", date(2026, 4, 1), date(2026, 5, 1))
    book.claim("RISKY", "P1", "300.00", date(2025, 7, 10), date(2026, 5, 1))  # filing limit 2026-07-10: 10 days left
    book.claim("SAFE", "P1", "300.00", date(2026, 4, 1), date(2026, 5, 1))
    go(book, date(2026, 6, 1), TODAY)
    cards = inbox(book.engine, 1)
    assert [c["claim"] for c in cards][:2] == ["BIG", "RISKY"] and [c["claim"] for c in cards][-1] == "SMALL"
    priority = {c["claim"]: c["priority"] for c in cards}
    assert priority["RISKY"] > priority["SAFE"]
    assert len(cards) == len({c["claim"] for c in cards}) == 4  # several follow-up rounds, one card per claim
    assert len(records(book.engine)) > 4
    text = format_inbox(cards, 1)
    assert "4 claims to work" in text and "BIG" in text


def test_a_claim_paid_after_its_card_was_raised_leaves_the_inbox(book):
    c = book.claim("W1", "P1", "150.00", date(2026, 3, 20), date(2026, 4, 20))  # 42 days old on 06-01
    book.claim("W2", "P1", "150.00", date(2026, 3, 20), date(2026, 4, 20))
    pay(book, c, date(2026, 6, 10))
    go(book, date(2026, 6, 1), date(2026, 6, 1))  # both unpaid on 06-01, so both get a card
    assert {c["claim"] for c in inbox(book.engine, 1, as_of=date(2026, 6, 5))} == {"W1", "W2"}
    assert {c["claim"] for c in inbox(book.engine, 1)} == {"W2"}  # W1 has been paid since


def test_aging_buckets():
    days = (0, 30, 31, 60, 61, 90, 91)
    assert [aging_bucket(d) for d in days] == ["0-30", "0-30", "31-60", "31-60", "61-90", "61-90", "90+"]


# ------------------------------------------------------------------------------------ engine guarantees


def test_shadow_never_reaches_an_adapter_and_a_rerun_creates_nothing(book):
    book.claim("S1", "P1", "150.00", date(2026, 4, 20), date(2026, 5, 10))
    book.commit()
    sweep(book.engine, 1, TODAY, TODAY)
    ((eid, _, _),) = events(book.engine)
    spy = SpyAdapter()
    res = run(book.engine, 1, A7ArAgent(), eid, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == []
    again = run(book.engine, 1, A7ArAgent(), eid, adapters={a: spy for a in ACTION_TYPES})
    assert again.created is False and again.record_id == res.record_id and len(records(book.engine)) == 1


def test_no_action_type_can_resubmit_write_off_or_change_a_code():
    banned = ("write_off", "refund", "adjust", "code", "void") + ("submit",)
    assert all(not any(b in a.replace("resubmit_review", "") for b in banned) for a in ACTION_TYPES)
    assert all(a.endswith(("_task", "_review")) for a in ACTION_TYPES)


def test_replay_is_deterministic(book):
    book.claim("P1x", "P1", "150.00", date(2026, 4, 20), date(2026, 5, 10))
    book.claim("P2x", "P1", "150.00", date(2026, 2, 1), date(2026, 3, 1))
    first = go(book, date(2026, 6, 1), TODAY)
    second = replay(book.engine, 1, A7ArAgent())
    assert [i.fingerprint for i in first] == [i.fingerprint for i in second] and len(first) >= 2
    with tenant_session(book.engine, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.DecisionRecord)) == len(first)
        assert all(fingerprint(r) for r in s.scalars(select(m.DecisionRecord)))


def test_history_and_events_do_not_cross_tenants(book):
    for i in range(5):  # tenant 1: P1 pays in 10 days
        c = book.claim(f"H{i}", "P1", "100.00", date(2026, 1, 1), date(2026, 1, 10))
        pay(book, c, date(2026, 1, 20))
    book.claim("X1", "P1", "150.00", date(2026, 5, 1), date(2026, 6, 10))  # 20 days
    book.commit()
    b2 = Book(book.engine, 2, tag="b")  # tenant 2: same claim, no history, so the 30-day default applies
    b2.claim("X1", "P1", "150.00", date(2026, 5, 1), date(2026, 6, 10))
    b2.commit()
    sweep(book.engine, 1, TODAY, TODAY)
    sweep(book.engine, 2, TODAY, TODAY)
    assert len(events(book.engine, 1)) == 1 and events(book.engine, 2) == []  # 20 days < the default 30
    replay(book.engine, 1, A7ArAgent())
    assert replay(book.engine, 2, A7ArAgent()) == [] and len(records(book.engine, 2)) == 0


def test_records_and_cards_carry_no_patient_identifier(book):
    book.claim("PHI1", "P1", "150.00", date(2026, 4, 20), date(2026, 5, 10))
    go(book)
    (rec,) = records(book.engine)
    text = (rec.input_snapshot + rec.action_payload).lower()
    assert "ref_hash" not in text and "patient" not in text and "member" not in text


# ------------------------------------------------------------------------------------ synthetic open AR


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a7")
    ms.generate(root / "data", seed=5, n_claims=200, n_open=24)
    engine = make_engine(root / "db.sqlite")
    ingest_path(engine, 1, root / "data", SALT)
    run_matching(engine, 1)
    return {"root": root, "engine": engine, "truth": root / "data" / "open_ar.csv"}


def test_generator_adds_nothing_by_default_and_leaves_the_base_files_alone(tmp_path):
    plain, extra = tmp_path / "plain", tmp_path / "extra"
    ms.generate(plain, seed=5, n_claims=60)
    ms.generate(extra, seed=5, n_claims=60, n_open=10)
    assert not (plain / "open_ar.csv").exists() and (extra / "open_ar.csv").exists()

    def digest(path):
        return hashlib.md5(path.read_bytes()).hexdigest()

    assert all(digest(f) == digest(extra / f.name) for f in plain.iterdir())


def test_every_unpaid_synthetic_claim_reaches_the_inbox_and_nothing_executes(syn, capsys):
    url = str(syn["engine"].url)
    sweep_args = ["--db-url", url, "a7", "sweep", "--tenant", "1", "--from", "2026-03-01", "--to", "2026-06-30"]
    assert cli.main(sweep_args) == 0
    assert "follow-up events added" in capsys.readouterr().out
    assert cli.main(["--db-url", url, "a7", "replay", "--tenant", "1"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    assert cli.main(["--db-url", url, "a7", "inbox", "--tenant", "1", "--top", "5"]) == 0
    assert "A7 inbox" in capsys.readouterr().out

    truth = list(csv.DictReader(syn["truth"].open()))
    cards = {c["claim"]: c for c in inbox(syn["engine"], 1)}
    summary = summarize(syn["engine"], 1)
    print(format_summary(summary))
    print(format_inbox(list(cards.values())[:5], 1))
    assert len(truth) == 24 and set(cards) <= {t["claim_id"] for t in truth}  # only unpaid claims, never a paid one
    age = {t["claim_id"]: (TODAY - date.fromisoformat(t["submitted"])).days for t in truth}
    # every claim old enough to be overdue for any payer (longest typical wait ~49 days, plus one sweep step) has a card
    assert {c for c, a in age.items() if a >= 56} <= set(cards) and len(cards) >= 18
    assert summary["executed"] == 0
    for t in truth:
        if t["claim_id"] in cards and t["returned"] == "Y":
            assert cards[t["claim_id"]]["action"] == "a7_resubmit_review"
    ranked = [c["priority"] for c in inbox(syn["engine"], 1)]
    assert ranked == sorted(ranked, reverse=True)
