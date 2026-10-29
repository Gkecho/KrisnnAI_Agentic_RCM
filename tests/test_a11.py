"""M17 tests: the A11 cash reconciliation agent in shadow mode, the deposit and posting feeds, and the Synthea book."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a11_cash import (
    ACTION_TYPES,
    DEPOSIT_EVENT,
    DEPOSIT_TASK,
    PAYMENT_EVENT,
    POSTING_TASK,
    UNAPPLIED_REVIEW,
    UNIDENTIFIED_REVIEW,
    A11CashAgent,
    Deposit,
    Payment,
    Posting,
    format_summary,
    kpis,
    latest,
    reconcile,
    summarize,
    sweep,
)
from krisnnai.agents.a11_cash import rules as r
from krisnnai.engine import NO_ACTION, replay, run
from krisnnai.engine.card import CARD_KEYS
from krisnnai.ingest.loader import ingest_path, parse_deposits, parse_postings
from krisnnai.ingest.x12 import X12Error
from krisnnai.match.engine import run_matching
from krisnnai.model import tenant_session
from krisnnai.synthea import build
from tests.fixtures import synthea_mini
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
PAID = date(2026, 6, 1)


def d(n: int) -> date:  # n days after the payment date
    return PAID + timedelta(days=n)


PAY = Payment("TRC1", "P1", D("1000.00"), PAID)
CLAIMS = {"A": D("600.00"), "B": D("400.00")}
GOOD_DEP = [Deposit("D1", d(2), D("1000.00"), "P1", "TRC1")]
GOOD_POST = [Posting("A", d(1), D("600.00")), Posting("B", d(2), D("400.00"))]


def kinds(deposits=GOOD_DEP, postings=GOOD_POST, as_of=d(10), claims=CLAIMS, pay=PAY):
    return [(g.kind, g.amount) for g in reconcile(pay, claims, deposits, postings, as_of)]


# ------------------------------------------------------------------------------------------- the rules


def test_a_payment_deposited_and_posted_in_full_is_reconciled():
    assert kinds() == []


def test_a_zero_dollar_remittance_has_nothing_to_reconcile():
    zero = Payment("TRC0", "P1", D("0.00"), PAID)
    assert kinds(deposits=[], postings=[], pay=zero, claims={"A": D("0")}) == []


def test_missing_deposit_only_once_it_is_due():
    assert kinds(deposits=[], as_of=d(4), postings=GOOD_POST) == []
    assert kinds(deposits=[], as_of=d(5), postings=GOOD_POST) == [(r.DEPOSIT_MISSING, D("1000.00"))]
    assert kinds(deposits=[Deposit("D1", d(9), D("1000.00"), "P1", "TRC1")], as_of=d(6)) == [
        (r.DEPOSIT_MISSING, D("1000.00"))]  # deposited on day 9: not known on day 6


def test_variance_and_duplicate_deposits_carry_the_difference():
    short = [Deposit("D1", d(2), D("985.00"), "P1", "TRC1")]
    assert kinds(deposits=short) == [(r.DEPOSIT_VARIANCE, D("15.00"))]
    twice = GOOD_DEP + [Deposit("D2", d(2), D("1000.00"), "P1", "TRC1")]
    assert kinds(deposits=twice) == [(r.DUPLICATE_DEPOSIT, D("1000.00"))]


def test_a_deposit_with_no_trace_is_matched_on_payer_amount_and_window():
    untraced = [Deposit("D9", d(3), D("1000.00"), "P1", None)]
    assert kinds(deposits=untraced) == []
    other_payer = [Deposit("D9", d(3), D("1000.00"), "P2", None)]
    assert kinds(deposits=other_payer) == [(r.DEPOSIT_MISSING, D("1000.00"))]
    too_late = [Deposit("D9", d(45), D("1000.00"), "P1", None)]
    assert kinds(deposits=too_late, as_of=d(50)) == [(r.DEPOSIT_MISSING, D("1000.00"))]


def test_not_posted_and_partial_posting_are_unapplied_cash_but_only_after_the_posting_window():
    part = [Posting("A", d(1), D("500.00"))]
    assert kinds(postings=part, as_of=d(2)) == []  # inside the posting window
    assert kinds(postings=part, as_of=d(4)) == [(r.NOT_POSTED, D("400.00")), (r.PARTIAL_POSTING, D("100.00"))]


def test_late_deposit_and_late_posting_are_kpis_not_actions():
    late_dep = [Deposit("D1", d(9), D("1000.00"), "P1", "TRC1")]
    late_post = [Posting("A", d(9), D("600.00")), Posting("B", d(1), D("400.00"))]
    gaps = reconcile(PAY, CLAIMS, late_dep, late_post, d(12))
    assert {g.kind for g in gaps} == {r.DEPOSIT_LATE, r.POSTING_LATE}
    assert not any(g.actionable for g in gaps)


def test_a_posting_dated_after_the_check_is_not_known():
    later = [Posting("A", d(8), D("600.00")), Posting("B", d(8), D("400.00"))]
    assert {k for k, _ in kinds(postings=later, as_of=d(6))} == {r.NOT_POSTED}


# ---------------------------------------------------------------------------------------- the parsers


def test_deposit_and_posting_parsers_read_rows_and_reject_bad_input():
    rows = parse_deposits("deposit_id,deposit_date,amount,payer_id,trace\nB1,2026-06-03,1000.00,P1,TRC1\nB2,2026-06-04,5.00,,\n")
    assert rows[0]["trace"] == "TRC1" and rows[1]["payer"] is None and rows[1]["trace"] is None
    with pytest.raises(X12Error):
        parse_deposits("deposit_id,amount\nB1,5\n")
    with pytest.raises(X12Error):
        parse_deposits("deposit_id,deposit_date,amount\nB1,not-a-date,5\n")
    posts = parse_postings("posting_id,payment_trace,claim_id,posted_on,posted_amount\nP1,TRC1,A,2026-06-02,600.00\n")
    assert posts[0]["amount"] == D("600.00") and posts[0]["role"] == "payment_poster"
    with pytest.raises(X12Error):
        parse_postings("posting_id,payment_trace\nP1,TRC1\n")


# ----------------------------------------------------------------------- sweeper + agent (hand book)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    c1 = b.claim("A", "P1", "700.00", date(2026, 5, 1), date(2026, 5, 3))
    c2 = b.claim("B", "P1", "500.00", date(2026, 5, 1), date(2026, 5, 3))
    pay = b.payment("P1", PAID, "TRC1", "1000.00")
    b.remit(pay, c1, "1", "600.00", "0.00", [("CO", "45", "100.00")])
    b.remit(pay, c2, "1", "400.00", "0.00", [("CO", "45", "100.00")])
    return b


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a11_cash")))


def go(b, start=d(5), end=d(40)):
    b.commit()
    sweep(b.engine, 1, start, end)
    return replay(b.engine, 1, A11CashAgent())


def test_a_payment_with_no_deposit_becomes_one_finance_task_with_the_dollars(book):
    book.posting("PO1", "TRC1", "A", d(1), "600.00")
    book.posting("PO2", "TRC1", "B", d(1), "400.00")
    go(book, end=d(5))
    (rec,) = records(book.engine)
    p = json.loads(rec.action_payload)
    assert rec.action_type == DEPOSIT_TASK and rec.outcome == "shadow" and p["owner"] == "finance"
    assert D(p["amount"]) == D("1000.00") and set(p["card"]) == set(CARD_KEYS)


def test_each_gap_goes_to_its_own_owner(tmp_path):
    engine = make_engine(tmp_path / "own.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    cs = {k: b.claim(k, "P1", "100.00", date(2026, 5, 1), date(2026, 5, 3)) for k in ("A", "B")}
    for trace, amount, claim, post in (("TA", "100.00", "A", None), ("TB", "100.00", "B", "60.00")):
        pay = b.payment("P1", PAID, trace, amount)
        b.remit(pay, cs[claim], "1", amount, "0.00", [("CO", "45", "10.00")])
        b.deposit("DEP" + trace, d(2), amount, "P1", trace)
        if post:
            b.posting("PO" + trace, trace, claim, d(1), post)
    go(b, end=d(5))
    got = {json.loads(x.action_payload)["trace"]: x.action_type for x in records(engine)}
    assert got == {"TA": POSTING_TASK, "TB": UNAPPLIED_REVIEW}  # nothing posted at all / posted 60 of 100


def test_an_unidentified_deposit_is_raised_once_with_its_amount(book):
    book.deposit("MYSTERY", d(0), "777.07", "P1", None)
    book.commit()
    first = sweep(book.engine, 1, d(5), d(40))
    assert first.events >= 1
    with tenant_session(book.engine, 1) as s:
        refs = [json.loads(p)["deposit_ref"] for p in s.scalars(
            select(m.Event.payload).where(m.Event.event_type == DEPOSIT_EVENT))]  # fmt: skip
    assert refs == ["MYSTERY"]
    replay(book.engine, 1, A11CashAgent())
    rec = [x for x in records(book.engine) if x.action_type == UNIDENTIFIED_REVIEW]
    assert len(rec) == 1 and json.loads(rec[0].action_payload)["amount"] == "777.07"


def test_a_gap_that_comes_clean_gets_one_closing_event_and_the_card_closes(book):
    book.posting("PO1", "TRC1", "A", d(1), "600.00")
    book.posting("PO2", "TRC1", "B", d(1), "400.00")
    book.commit()
    sweep(book.engine, 1, d(5), d(5))  # no deposit yet
    with tenant_session(book.engine, 1) as s:
        f = m.SourceFile(file_name="bank.csv", file_sha256="c" * 64, file_type="deposits", byte_size=1, status="loaded")
        s.add(f)
        s.flush()
        payer = s.scalars(select(m.Payer)).first()
        s.add(m.BankDeposit(source_file_id=f.id, deposit_ref="LATE", deposit_date=d(6), amount=D("1000.00"),
                            payer_id=payer.id, trace_ref="TRC1", method="ACH"))  # fmt: skip
        s.commit()
    sweep(book.engine, 1, d(7), d(7))
    with tenant_session(book.engine, 1) as s:
        gaps = [json.loads(p)["gaps"] for p in s.scalars(
            select(m.Event.payload).where(m.Event.event_type == PAYMENT_EVENT).order_by(m.Event.id))]  # fmt: skip
    assert gaps == [["deposit_missing"], []]
    replay(book.engine, 1, A11CashAgent())
    assert [x.action_type for x in records(book.engine)] == [DEPOSIT_TASK, NO_ACTION]
    assert all(a == NO_ACTION for a, _ in latest(book.engine, 1).values())


def test_a_rerun_adds_nothing_shadow_nothing_runs_and_tenants_are_isolated(book):
    book.commit()
    first = sweep(book.engine, 1, d(5), d(12))
    assert first.events == 2 and not first.skipped  # one payment: first check at day 5, repeated a week later
    assert sweep(book.engine, 1, d(5), d(12)).skipped
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == PAYMENT_EVENT))
    spy = SpyAdapter()
    res = run(book.engine, 1, A11CashAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, A11CashAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False
    assert records(book.engine, 2) == []
    assert all(a.endswith(("_task", "_review")) for a in ACTION_TYPES)
    assert not any(w in a for a in ACTION_TYPES for w in ("post_payment", "write", "refund", "adjust", "void"))


def test_kpis_count_days_to_deposit_and_post(book):
    book.deposit("D1", d(4), "1000.00", "P1", "TRC1")
    book.posting("PO1", "TRC1", "A", d(2), "600.00")
    book.posting("PO2", "TRC1", "B", d(10), "400.00")  # late
    book.commit()
    k = kpis(book.engine, 1, d(30))
    assert k["days_to_deposit"] == {"n": 1, "mean": 4.0, "median": 4}
    assert k["days_to_post"]["n"] == 2 and k["late_postings"] == ["TRC1|B"]


# ------------------------------------------------------------------------------------- Synthea book


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a11")
    raw = synthea_mini.write(root / "raw", n_claims=1200, n_patients=150, seed=5)
    as_of = date(2026, 6, 30)
    build(raw, root / "book", as_of, seed=7, cash=True)
    engine = make_engine(root / "db.sqlite")
    results = ingest_path(engine, 1, root / "book", SALT)
    run_matching(engine, 1)
    sweep(engine, 1, as_of - timedelta(days=7 * 70), as_of)
    replay(engine, 1, A11CashAgent())
    truth = defaultdict(list)
    for t in csv.DictReader((root / "book" / "cash_truth.csv").open()):
        truth[t["defect"]].append(t)
    return {"root": root, "engine": engine, "truth": truth, "results": results, "as_of": as_of}


def gaps_by_trace(engine):
    out = defaultdict(lambda: defaultdict(Decimal))
    for key, (action, p) in latest(engine, 1).items():
        for g in p.get("gaps", []):
            out[key][g["kind"]] += abs(Decimal(g["amount"]))
    return out


def test_deposits_and_postings_load_idempotently(syn):
    assert all(x.status == "loaded" for x in syn["results"])
    assert {"deposits", "postings"} <= {x.file_type for x in syn["results"]}
    assert all(x.status == "skipped" for x in ingest_path(syn["engine"], 1, syn["root"] / "book", SALT))


def test_every_planted_cash_defect_is_found_and_the_dollars_match(syn):
    found, truth = gaps_by_trace(syn["engine"]), syn["truth"]
    pairs = {"missing_deposit": r.DEPOSIT_MISSING, "deposit_variance": r.DEPOSIT_VARIANCE,
             "duplicate_deposit": r.DUPLICATE_DEPOSIT, "not_posted": r.NOT_POSTED,
             "partial_posting": r.PARTIAL_POSTING}  # fmt: skip
    for defect, kind in pairs.items():
        want: dict[str, Decimal] = defaultdict(Decimal)
        for t in truth[defect]:
            want[t["payment_trace"]] += Decimal(t["amount"])
        assert len(want) > 3, defect
        got = {trace: v[kind] for trace, v in found.items() if v.get(kind)}
        assert got == dict(want), defect


def test_every_unidentified_deposit_is_raised_and_nothing_else_is(syn):
    want = {t["key"] for t in syn["truth"]["unidentified_deposit"]}
    got = {k for k, (a, p) in latest(syn["engine"], 1).items() if p.get("kind") == "deposit" and a != NO_ACTION}
    assert want and got == want


def test_unapplied_cash_and_variance_totals_equal_the_answer_key(syn):
    s = summarize(syn["engine"], 1, syn["as_of"])
    t = syn["truth"]

    def total(*names):
        return sum((Decimal(x["amount"]) for n in names for x in t[n]), Decimal(0))

    assert s["unapplied_cash"] == total("not_posted", "partial_posting")
    assert s["variance"] == total("missing_deposit", "deposit_variance", "duplicate_deposit")
    assert "unapplied cash" in format_summary(s)


def test_the_days_to_deposit_and_post_kpis_find_the_planted_lags(syn):
    k = kpis(syn["engine"], 1, syn["as_of"])
    assert set(k["late_deposits"]) == {x["payment_trace"] for x in syn["truth"]["late_deposit"]}
    assert set(k["late_postings"]) == {f"{x['payment_trace']}|{x['claim_id']}" for x in syn["truth"]["late_posting"]}
    assert 1 <= k["days_to_deposit"]["median"] <= 3 and k["days_to_post"]["median"] <= 2


def test_the_tower_shows_a11_cards_and_cli_replays_in_shadow(syn, tmp_path, capsys):
    from krisnnai.agents.a14_tower.cards import open_cards

    with tenant_session(syn["engine"], 1) as s:
        day = s.scalars(
            select(m.Event.known_at)
            .join(m.DecisionRecord, m.DecisionRecord.event_id == m.Event.id)
            .where(m.DecisionRecord.agent_id == "a11_cash", m.DecisionRecord.action_type != NO_ACTION)
            .order_by(m.Event.known_at)
        ).first().date()
    assert [c for c in open_cards(syn["engine"], 1, day) if c["agent"] == "a11_cash"]
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a11", "replay", "--tenant", "1"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    raw = syn["root"] / "raw"
    a, b = tmp_path / "plain", tmp_path / "plain2"
    build(raw, a, syn["as_of"], seed=7)
    build(raw, b, syn["as_of"], seed=7, cash=False)
    assert not (a / "bank_deposits.csv").exists()
    digest = lambda x: {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(x.iterdir())}  # noqa: E731
    assert digest(a) == digest(b)
