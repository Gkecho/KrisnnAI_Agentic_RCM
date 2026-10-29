"""M21 tests: the A15 investigator (shadow) on hand-built books: variance, causes, upstream tags, sweeper, agent, ledger."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a14_tower.cards import open_cards
from krisnnai.agents.a15_investigator import (
    ACTION_TYPES,
    INVESTIGATION_REVIEW,
    A15InvestigatorAgent,
    ledger,
    slices,
    summarize,
    sweep,
)
from krisnnai.agents.a15_lite import load_snapshot
from krisnnai.agents.upstream import upstream_flags
from krisnnai.engine import NO_ACTION, replay, run
from krisnnai.engine.card import CARD_KEYS
from krisnnai.model import tenant_session
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import make_engine

D = Decimal
E = date(2026, 9, 1)  # recent window: paid in (Jul 7, Sep 1]; baseline: paid in (Jan 12, Jul 7]


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "100.00")
    return b


def pay(b, sid, paid_on, paid="100.00", status="1", cas=(), pr="0.00", cpt="99213", payer="P1"):
    dos = paid_on - timedelta(days=30)
    claim = b.claim(sid, payer, "150.00", dos, dos + timedelta(days=1), cpt=cpt)
    p = b.payment(payer, paid_on, "T" + sid, paid)
    b.remit(p, claim, status, paid, pr, list(cas), cpt=cpt)
    return claim


def baseline(b, n=10, payer="P1"):
    for i in range(n):
        pay(b, f"B{i}", date(2026, 3, 2) + timedelta(days=i), payer=payer)


def recent(b, paid=6, denied=4, carc="50", start=date(2026, 8, 1), prefix="R"):
    for i in range(paid):
        pay(b, f"{prefix}{i}", start + timedelta(days=i))
    for i in range(denied):
        pay(b, f"{prefix}D{i}", start + timedelta(days=paid + i), "0.00", "4", [("CO", carc, "100.00")])


def flagged(b, as_of=E):
    b.commit()
    return {x.key: x for x in slices(load_snapshot(b.engine, 1, as_of), as_of)}


# ------------------------------------------------------------------------------------------- variance


def test_realisation_fall_dollars_and_causes_on_paper(book):
    baseline(book)
    recent(book)
    found = flagged(book)
    assert set(found) == {"P1", "P1|99213"}
    x = found["P1"]
    assert (x.baseline, x.recent, x.drop, x.impact) == (D(1), D("0.6"), D("0.4"), D("400.00"))
    assert (x.lines_recent, x.lines_baseline, x.expected_recent) == (10, 10, D("1000.00"))
    assert sum((s.expected - s.actual for s in x.shortfall_lines), D(0)) == D("400.00")


def test_thresholds_need_enough_lines_dollars_and_a_real_fall(book):
    baseline(book)
    recent(book, paid=6, denied=1)  # 7 lines in the recent window: under the minimum
    assert flagged(book) == {}


def test_a_fall_under_five_points_is_not_flagged(tmp_path):
    engine = make_engine(tmp_path / "c.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "100.00")
    baseline(b)
    recent(b, paid=9, denied=0)
    pay(b, "R9", date(2026, 8, 20), "51.00", cas=[("CO", "45", "99.00")])  # 100 allowed, 51 paid: 4.9 points
    assert flagged(b) == {}


def test_reversals_are_not_priced(book):
    baseline(book)
    recent(book, paid=10, denied=0)
    pay(book, "X1", date(2026, 8, 25), "-100.00", "22")  # a reversal of a payment is not a shortfall
    assert flagged(book) == {}


def test_denial_cause_carries_category_carc_and_one_line_per_claim(book):
    baseline(book)
    recent(book, carc="197")
    book.commit()
    snap = load_snapshot(book.engine, 1, E)
    from krisnnai.agents.a15_investigator.causes import explain
    from krisnnai.agents.a15_lite import detect

    why = explain(slices(snap, E)[0], detect(snap), {})
    (top,) = why["causes"]
    assert (top["cause"], top["dollars"], top["lines"], top["carcs"]) == ("denial:authorization", "400.00", 4, {"197": 4})
    assert why["upstream"] == {"none": "400.00"} and why["shortfall"] == "400.00"


def test_underpayment_is_its_own_cause_and_unexplained_is_reported_not_guessed(book):
    baseline(book)
    for i in range(3):
        pay(book, f"U{i}", date(2026, 8, 1) + timedelta(days=i), "80.00", cas=[("CO", "45", "70.00")])
    recent(book, paid=7, denied=0, prefix="G", start=date(2026, 8, 10))
    book.commit()
    from krisnnai.agents.a15_investigator.causes import explain
    from krisnnai.agents.a15_lite import detect

    snap = load_snapshot(book.engine, 1, E)
    got = {x.key: x for x in slices(snap, E)}["P1"]
    why = explain(got, detect(snap), {})
    assert [(c["cause"], c["dollars"], c["lines"]) for c in why["causes"]] == [("underpayment", "60.00", 3)]
    # with no finding to attribute the shortfall to, it is reported as unexplained, never guessed
    blind = explain(got, [], {"U0": {"A10"}})
    assert [(c["cause"], c["dollars"]) for c in blind["causes"]] == [("unexplained", "60.00")]
    assert blind["upstream"] == {"A10": "20.00", "none": "40.00"}
    assert D(why["shortfall"]) == sum(D(c["dollars"]) for c in why["causes"])


# ------------------------------------------------------------------------------------------- upstream


def test_upstream_flag_counts_only_when_known_before_the_claim_was_billed(book):
    c1 = pay(book, "C1", date(2026, 8, 1))
    c2 = pay(book, "C2", date(2026, 8, 2))
    for claim, offset in ((c1, -3), (c2, 3)):  # A4 flagged C1 three days before it was billed, C2 three days after
        ev = book.event(claim.submitted_on + timedelta(days=offset), "837P.claim", st02="x" + claim.claim_submitter_id,
                        gs06="x" + claim.claim_submitter_id)  # fmt: skip
        book._add(m.DecisionRecord(
            event_id=ev, agent_id="a4_coding", agent_version="0.1", trigger_type="837P.claim", mode="shadow",
            action_type="a4_coding_review", action_payload=json.dumps({"claim": claim.claim_submitter_id}),
            autonomy_level=0, confidence=D("0.8"), materiality_amount=D("1"), rules_fired="[]",
            input_snapshot="{}", outcome="shadow",
        ))  # fmt: skip
    book.commit()
    assert upstream_flags(book.engine, 1) == {"C1": {"A4"}}  # C2 was flagged after billing: not preventable
    assert upstream_flags(book.engine, 1, date(2026, 6, 1)) == {}  # nothing was known yet at that date


# ------------------------------------------------------------------------------------------- sweeper, agent


def test_sweep_raises_first_flag_changes_and_one_closing_event_and_is_idempotent(book):
    baseline(book)
    recent(book)
    book.commit()
    start = E
    res = sweep(book.engine, 1, start, start, 28)
    assert (res.events, res.skipped) == (2, False)  # P1 and P1|99213
    assert sweep(book.engine, 1, start, start, 28).skipped is True
    # 28 days on the recent window holds the same payments minus the oldest: an unchanged fall adds nothing
    res2 = sweep(book.engine, 1, start + timedelta(days=28), start + timedelta(days=28), 28)
    assert res2.events == 0 or res2.events == 2  # unchanged (0) or the slice's fall moved or cleared (2)
    with tenant_session(book.engine, 1) as s:
        events = [json.loads(e) for e in s.scalars(select(m.Event.payload).where(m.Event.event_type == "revenue.variance"))]
    assert {e["key"] for e in events} == {"P1", "P1|99213"} and all(e["flagged"] for e in events[:2])
    assert events[0]["causes"][0]["cause"] == "denial:medical_necessity" and events[0]["impact"] == "400.00"


def test_agent_one_review_per_flagged_slice_closes_when_the_slice_clears(book):
    baseline(book)
    recent(book)
    # the payer fixed it: much later, everything pays in full again
    recent(book, paid=10, denied=0, start=date(2026, 11, 10), prefix="F")
    book.commit()
    sweep(book.engine, 1, E, date(2026, 12, 1), 28)  # Sep 1 flags; Dec 1 recent window is all full payment
    replay(book.engine, 1, A15InvestigatorAgent())
    with tenant_session(book.engine, 1) as s:
        recs = list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a15_investigator")))
    actions = {r.action_type for r in recs}
    assert actions <= {INVESTIGATION_REVIEW, NO_ACTION} and INVESTIGATION_REVIEW in actions and NO_ACTION in actions
    review = next(json.loads(r.action_payload) for r in recs if r.action_type == INVESTIGATION_REVIEW)
    assert set(review["card"]) >= set(CARD_KEYS) and review["owner"] == "revenue_assurance_lead"
    assert "not proof of cause" in review["suggestion_only"]
    s_ = summarize(book.engine, 1)
    assert s_["slices"] == [] and s_["impact"] == D(0)  # cleared by the later closing event


def test_shadow_nothing_runs_replay_is_deterministic_and_the_action_is_a_review(book):
    baseline(book)
    recent(book)
    book.commit()
    sweep(book.engine, 1, E, E, 28)
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == "revenue.variance"))
    spy = SpyAdapter()
    agent = A15InvestigatorAgent()
    res = run(book.engine, 1, agent, event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, agent, event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False
    assert ACTION_TYPES == (INVESTIGATION_REVIEW,) and INVESTIGATION_REVIEW.endswith("_review")
    first = [(i.outcome, i.fingerprint) for i in replay(book.engine, 1, A15InvestigatorAgent())]
    second = [(i.outcome, i.fingerprint) for i in replay(book.engine, 1, A15InvestigatorAgent())]
    assert first == second


def test_tenants_are_isolated_and_the_tower_lists_the_card(book, tmp_path):
    baseline(book)
    recent(book)
    book.commit()
    sweep(book.engine, 1, E, E, 28)
    replay(book.engine, 1, A15InvestigatorAgent())
    assert summarize(book.engine, 2)["slices"] == []
    cards = [c for c in open_cards(book.engine, 1, E) if c["agent"] == "a15_investigator"]
    assert sorted(c["claim"] for c in cards) == ["P1", "P1|99213"]
    assert all(c["owner"] == "revenue_assurance_lead" and c["action_type"] == INVESTIGATION_REVIEW for c in cards)


# ------------------------------------------------------------------------------------------- ledger


def test_ledger_counts_later_payment_on_detected_claims_once(book):
    detected = date(2026, 2, 1)
    k1 = pay(book, "K1", date(2026, 1, 10), "90.00", cas=[("CO", "45", "50.00"), ("PR", "2", "10.00")], pr="10.00")
    d1 = pay(book, "D1", date(2026, 1, 20), "0.00", "4", [("CO", "50", "100.00")])
    pay(book, "D2", date(2026, 1, 21), "0.00", "4", [("CO", "16", "100.00")])
    # D1 is paid after the detection date (an appeal): 90.00 received; D2 is never paid
    p = book.payment("P1", date(2026, 3, 1), "TREAPPEAL", "90.00")
    book.remit(p, d1, "1", "90.00", "0.00", [("CO", "45", "60.00")])
    book.commit()
    x = ledger(book.engine, 1, detected, date(2026, 4, 1))
    rows = {r["type"]: r for r in x["rows"]}
    assert rows["denial"]["detected"] == 2 and rows["denial"]["recovered"] == 1
    assert x["recovered_amount"] == D("90.00") and rows["denial"]["recovered_amount"] == D("90.00")
    assert x["detected_amount"] == D("200.00") and k1 is not None  # two denied claims at the contract
    assert ledger(book.engine, 1, detected, detected)["recovered_amount"] == D("0.00")
    with pytest.raises(ValueError):
        ledger(book.engine, 1, date(2026, 4, 1), detected)


def test_cli_sweep_replay_and_ledger(book, capsys):
    baseline(book)
    recent(book)
    book.commit()
    url = str(book.engine.url)
    assert cli.main(["--db-url", url, "investigate", "sweep", "--tenant", "1", "--from", "2026-09-01",
                     "--to", "2026-09-01"]) == 0  # fmt: skip
    assert "2 variance events added" in capsys.readouterr().out
    assert cli.main(["--db-url", url, "investigate", "replay", "--tenant", "1"]) == 0
    out = capsys.readouterr().out
    assert "nothing recovered" in out and "denial:medical_necessity" in out
    assert cli.main(["--db-url", url, "investigate", "ledger", "--tenant", "1", "--detected-on", "2026-09-01",
                     "--through", "2026-09-30"]) == 0  # fmt: skip
    assert "not proof the work caused it" in capsys.readouterr().out
