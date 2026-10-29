"""M11 tests: the A14 control tower (cross-agent inbox, cash forecast, signals) and its daily shadow agent."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnnai.agents.a14_tower.forecast as fc
import krisnnai.agents.a14_tower.signals as sg
import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a5_prevention import A5PreventionAgent
from krisnnai.agents.a6_submission import A6SubmissionAgent
from krisnnai.agents.a6_submission import seed_defaults as seed_a6
from krisnnai.agents.a7_ar import A7ArAgent
from krisnnai.agents.a7_ar import sweep as a7_sweep
from krisnnai.agents.a8_denial import A8DenialAgent
from krisnnai.agents.a8_denial import seed_defaults as seed_a8
from krisnnai.agents.a14_tower import (
    ACTION_TYPES,
    EVENT_TYPE,
    A14TowerAgent,
    backtest,
    compute_tower,
    format_summary,
    format_tower,
    open_cards,
    summarize,
    sweep,
)
from krisnnai.engine import NO_ACTION, fingerprint, replay, run
from krisnnai.ingest.loader import ingest_path
from krisnnai.match.engine import run_matching
from krisnnai.model import tenant_session
from tests.fixtures import make_synthetic as ms
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
TODAY = date(2026, 6, 1)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    return b


def add_claim(b, sid, submitted, dos=None, payer="P1", charge="100.00", dx=True):
    """A one-line claim submitted (and known) on `submitted`, with a diagnosis unless dx is False."""
    c = b.claim(sid, payer, charge, dos or submitted - timedelta(days=10), submitted)
    if dx:
        b._add(m.ClaimDx(claim_id=c.id, seq=1, dx_qualifier="ABK", dx_code="M5450"))
        line = b.s.scalars(select(m.ClaimLine).where(m.ClaimLine.claim_id == c.id)).one()
        line.diagnosis_pointer = "1"
    return c


def pay(b, claim, known, amount="100.00", payer="P1"):
    p = b.payment(payer, known, "T" + claim.claim_submitter_id + known.isoformat(), amount)
    b.remit(p, claim, "1", amount, "0.00", [])


def history(b, payer="P1", n=6, days=10, submitted=date(2026, 1, 1)):
    """n mature claims, each paid `days` days after submission: the payer's days-to-pay curve is a step at `days`."""
    for i in range(n):
        pay(b, add_claim(b, f"H{payer}{i}", submitted, payer=payer), submitted + timedelta(days=days), payer=payer)


def go(b):
    b.commit()
    return b.engine


def tower_forecast(engine, as_of):
    with tenant_session(engine, 1) as s:
        return fc.forecast(s, as_of)


def seed_all(engine):
    with tenant_session(engine, 1) as s:
        seed_a6(s)
        seed_a8(s)
        s.commit()


# --------------------------------------------------------------------------------------------- forecast


def test_forecast_worked_out_on_paper(book):
    history(book)  # q = (6 + 1) / (6 + 2) = 0.875, every payment on day 10
    add_claim(book, "FRESH", date(2026, 5, 28))  # age 4: due in week 1
    add_claim(book, "STUCK", date(2026, 4, 22))  # age 40: older than anything the payer ever paid
    e = go(book)
    f = tower_forecast(e, TODAY)
    w1 = f["weeks"][0]
    assert f["claims_open"] == 2 and w1["expected"] == D("87.50")  # 100 billed x 0.875; the stuck claim adds nothing
    assert [w["expected"] for w in f["weeks"][1:]] == [D("0.00")] * 3 and f["later"]["expected"] == D("0.00")
    sd = (D(100) ** 2 * D("0.875") * D("0.125")).sqrt()
    assert abs(w1["low"] - (D("87.5") - fc.Z80 * sd)) < D("0.01") and abs(w1["high"] - (D("87.5") + fc.Z80 * sd)) < D("0.01")
    assert w1["low"] <= w1["expected"] <= w1["high"] and f["next_28_days"]["expected"] == w1["expected"]


def test_forecast_leaves_out_paid_and_rejected_claims_and_does_not_see_the_future(book):
    history(book)
    paid = add_claim(book, "PAID", date(2026, 5, 20))
    pay(book, paid, date(2026, 5, 28))
    bounced = add_claim(book, "BOUNCED", date(2026, 5, 28))
    book.ack_277ca(bounced, "A3", date(2026, 5, 30), code="21")
    later = add_claim(book, "LATER", date(2026, 5, 28))
    pay(book, later, date(2026, 6, 10))  # paid after the forecast date: unknown on 06-01
    add_claim(book, "NEXT", date(2026, 6, 5))  # not submitted yet on 06-01
    e = go(book)
    f = tower_forecast(e, TODAY)
    assert f["claims_open"] == 1  # only LATER; PAID, BOUNCED and NEXT are out
    assert f["weeks"][0]["expected"] == D("87.50")
    with tenant_session(e, 1) as s:
        assert fc.actual_cash(s, ["LATER"], TODAY, TODAY + timedelta(days=28)) == D("100.00")


def test_a_payer_with_no_history_gets_a_flat_ramp_not_a_guess_of_zero(book):
    add_claim(book, "NEW1", date(2026, 5, 22))  # age 10 of a 60-day ramp; no paid claims at all
    f = tower_forecast(go(book), TODAY)
    assert f["weeks"][0]["expected"] > 0 and f["next_28_days"]["expected"] > f["weeks"][0]["expected"]


def test_backtest_scores_a_forecast_against_what_was_paid(book):
    history(book)
    for sid in ("A", "B"):  # both paid on day 10, 20 days after the 05-01 forecast date... 05-11 is inside the window
        pay(book, add_claim(book, sid, date(2026, 5, 1)), date(2026, 5, 11))
    e = go(book)
    bt = backtest(e, 1, [date(2026, 5, 3)])
    (row,) = bt["rows"]
    assert row["claims"] == 2 and row["actual"] == D("200.00") and row["forecast"] == D("175.00")
    assert bt["wape"] == D("0.1250") and bt["coverage"] in (D("0.00"), D("1.00"))


# ---------------------------------------------------------------------------------------------- signals


def test_backlog_growth_needs_both_a_share_and_a_count():
    assert sg.backlog_growth(10, 5)["fired"] and sg.backlog_growth(6, 0)["fired"]
    assert not sg.backlog_growth(12, 8)["fired"] and not sg.backlog_growth(30, 28)["fired"]


def test_a_payer_slowdown_fires_only_with_enough_claims_on_both_sides(book):
    def batch(prefix, n, submitted, days):
        for i in range(n):
            pay(book, add_claim(book, f"{prefix}{i}", submitted), submitted + timedelta(days=days))

    batch("OLD", 5, date(2026, 2, 1), 20)  # baseline window: paid 02-21, 20 days
    batch("NEW", 5, date(2026, 4, 15), 40)  # recent window: paid 05-25, 40 days
    e = go(book)
    with tenant_session(e, 1) as s:
        sig = sg.payer_slowdowns(s, TODAY)
    assert sig["fired"] and sig["items"][0]["payer"] == "P1" and sig["items"][0]["slower_by_days"] == 20

    thin = Book(e, 2, tag="b")  # tenant 2: only 4 recent claims, so no signal
    for i in range(5):
        pay(thin, add_claim(thin, f"O{i}", date(2026, 2, 1)), date(2026, 2, 21))
    for i in range(4):
        pay(thin, add_claim(thin, f"N{i}", date(2026, 4, 15)), date(2026, 5, 25))
    thin.commit()
    with tenant_session(e, 2) as s:
        assert not sg.payer_slowdowns(s, TODAY)["fired"]


def test_a_rejection_spike_compares_recent_claims_with_the_weeks_before(book):
    for i in range(20):  # baseline window (03-19, 05-18]: 1 of 20 rejected
        c = add_claim(book, f"B{i}", date(2026, 4, 1) + timedelta(days=i))
        if i == 0:
            book.ack_277ca(c, "A3", date(2026, 4, 5))
    for i in range(10):  # recent window (05-18, 06-01]: 3 of 10 rejected
        c = add_claim(book, f"R{i}", date(2026, 5, 20) + timedelta(days=i))
        if i < 3:
            book.ack_277ca(c, "A3", date(2026, 5, 29))
    e = go(book)
    with tenant_session(e, 1) as s:
        sig = sg.rejection_spike(s, TODAY)
    assert sig["fired"] and "30.0%" in sig["detail"] and "5.0%" in sig["detail"]


# ------------------------------------------------------------------------------- cross-agent decision inbox


def build_inbox_book(book, later=False):
    """One open item for each agent, raised before 06-01. `later` adds events after 06-01 that resolve all four."""
    flag = add_claim(book, "FLAG", date(2026, 5, 10), dx=False)  # A5: no diagnosis
    returned = add_claim(book, "RET", date(2026, 5, 10), dos=date(2026, 4, 28))  # A6: returned by the 277CA
    book.ack_277ca(returned, "A3", date(2026, 5, 12), code="21")
    old = add_claim(book, "OLD", date(2026, 3, 1))  # A7: unpaid for 92 days
    denied = add_claim(book, "DEN", date(2026, 4, 1))  # A8: denied on 05-05
    book.remit(book.payment("P1", date(2026, 5, 5), "TD", "0.00"), denied, "4", "0.00", "0.00", [("CO", "16", "100.00")])
    if later:
        for claim, day in ((flag, date(2026, 6, 5)), (old, date(2026, 6, 6)), (denied, date(2026, 6, 7))):
            pay(book, claim, day)  # paid, paid, paid
        add_claim(book, "RET", date(2026, 6, 3), dos=date(2026, 4, 28))  # re-filed after the rejection
    e = go(book)
    seed_all(e)
    for agent in (A5PreventionAgent(), A6SubmissionAgent(), A8DenialAgent()):
        replay(e, 1, agent)
    a7_sweep(e, 1, TODAY, TODAY)
    replay(e, 1, A7ArAgent())
    return e


def test_every_agent_shows_up_in_one_ranked_inbox_with_the_same_shape(book):
    e = build_inbox_book(book)
    cards = open_cards(e, 1, TODAY)
    assert {c["agent"] for c in cards} == {"a5_prevention", "a6_submission", "a7_ar", "a8_denial"}
    assert [c["priority"] for c in cards] == sorted((c["priority"] for c in cards), reverse=True)
    keys = {"title", "why", "priority", "expected_value", "deadline", "owner", "next_steps", "evidence"}
    assert all(set(c["card"]) == keys and c["overdue"] in (True, False) for c in cards)
    text = json.dumps(cards, default=str).lower()
    assert "ref_hash" not in text and "member" not in text


def test_an_item_leaves_the_inbox_when_it_is_resolved_and_not_before(book):
    e = build_inbox_book(book, later=True)
    assert len(open_cards(e, 1, TODAY)) == 4  # point in time: nothing that happened later is visible on 06-01
    assert len(open_cards(e, 1, date(2026, 6, 4))) == 3  # RET was re-filed on 06-03
    assert open_cards(e, 1, date(2026, 6, 10)) == []  # paid, paid, paid and re-filed: all closed


def test_backlog_adds_up_and_a_deadline_critical_item_is_never_muted(book):
    cards = open_cards(build_inbox_book(book), 1, TODAY)
    b = sg.backlog(cards)
    assert b["items"] == len(cards) == sum(g["items"] for g in b["by_owner"].values())
    assert b["dollars"] == sum(c["expected_value"] for c in cards) and b["overdue"] >= 1
    sig = sg.deadline_critical(cards)
    assert sig["fired"] and all(i["deadline"] for i in sig["items"])


# -------------------------------------------------------------------------------------------- agent


def test_sweep_adds_one_event_per_day_once(book):
    e = go(book)
    first = sweep(e, 1, date(2026, 6, 1), date(2026, 6, 3))
    again = sweep(e, 1, date(2026, 6, 1), date(2026, 6, 3))
    overlap = sweep(e, 1, date(2026, 6, 3), date(2026, 6, 5))
    assert (first.events, again.skipped, overlap.events) == (3, True, 2)
    with tenant_session(e, 1) as s:
        assert s.scalar(select(m.Event.id).where(m.Event.event_type == EVENT_TYPE).limit(1)) is not None


def test_a_quiet_day_proposes_nothing(book):
    history(book)
    e = go(book)
    sweep(e, 1, TODAY, TODAY)
    (item,) = replay(e, 1, A14TowerAgent())
    with tenant_session(e, 1) as s:
        rec = s.scalars(select(m.DecisionRecord)).one()
    assert rec.action_type == NO_ACTION and item.outcome == NO_ACTION


def test_a_firing_signal_proposes_one_escalation_review_for_the_operations_leader(book):
    e = build_inbox_book(book)
    sweep(e, 1, TODAY, TODAY)
    (item,) = replay(e, 1, A14TowerAgent())
    with tenant_session(e, 1) as s:
        rec = s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a14_tower")).one()
    p = json.loads(rec.action_payload)
    assert rec.action_type == "a14_escalation_review" and item.outcome == "shadow"
    assert p["card"]["owner"] == "operations_leader" and {s["signal"] for s in p["signals"]} >= {"deadline_critical"}
    assert p["overdue"] >= 1 and p["top_cards"] and "patient" not in rec.action_payload.lower()
    assert ACTION_TYPES == ("a14_escalation_review",)


def test_shadow_never_reaches_an_adapter_and_a_rerun_creates_nothing(book):
    e = build_inbox_book(book)
    sweep(e, 1, TODAY, TODAY)
    with tenant_session(e, 1) as s:
        event_id = s.scalars(select(m.Event).where(m.Event.event_type == EVENT_TYPE)).one().id
    spy = SpyAdapter()
    res = run(e, 1, A14TowerAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(e, 1, A14TowerAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False and again.record_id == res.record_id


def test_replay_is_deterministic(book):
    e = build_inbox_book(book)
    sweep(e, 1, TODAY, TODAY + timedelta(days=1))
    first = replay(e, 1, A14TowerAgent())
    second = replay(e, 1, A14TowerAgent())
    assert [i.fingerprint for i in first] == [i.fingerprint for i in second] and len(first) == 2
    with tenant_session(e, 1) as s:
        assert all(fingerprint(r) for r in s.scalars(select(m.DecisionRecord)))


def test_another_tenants_work_never_reaches_the_tower(book):
    e = build_inbox_book(book)
    other = Book(e, 2, tag="z")
    other.commit()
    assert open_cards(e, 2, TODAY) == [] and open_cards(e, 1, TODAY)
    assert compute_tower(e, 2, TODAY, backtest_weeks=0)["backlog"]["items"] == 0


# --------------------------------------------------------------------------------------- synthetic


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a14")
    ms.generate(root / "data", seed=5, n_claims=200, n_open=200)
    engine = make_engine(root / "db.sqlite")
    ingest_path(engine, 1, root / "data", SALT)
    run_matching(engine, 1)
    seed_all(engine)
    with tenant_session(engine, 1) as s:
        from krisnnai.agents.a5_prevention import seed_defaults as seed_a5

        seed_a5(s)
        s.commit()
    for agent in (A5PreventionAgent(), A6SubmissionAgent(), A8DenialAgent()):
        replay(engine, 1, agent)
    a7_sweep(engine, 1, date(2026, 3, 1), ms.AS_OF)
    replay(engine, 1, A7ArAgent())
    return {"root": root, "engine": engine}


@pytest.mark.slow
def test_the_forecast_is_close_on_synthetic_history_and_the_tower_reads_every_agent(syn, capsys):
    e = syn["engine"]
    t = compute_tower(e, 1, ms.AS_OF)
    print("\n" + format_tower(t))
    bt = t["backtest"]
    assert bt["dates"] == 8 and bt["wape"] < D("0.15") and bt["coverage"] >= D("0.50")  # 400 claims of history
    assert t["data_sufficient"] and t["forecast"]["claims_open"] > 0 and t["forecast"]["next_28_days"]["expected"] > 0
    assert {c["agent"] for c in open_cards(e, 1, ms.AS_OF)} == {"a5_prevention", "a6_submission", "a7_ar", "a8_denial"}
    assert t["backlog"]["items"] == len(open_cards(e, 1, ms.AS_OF)) and t["top_cards"]
    assert set(t["gaps"]) and "kpis" in t and t["headline"]["clean_claim_rate"] is not None


@pytest.mark.slow
def test_cli_tower_and_a14_replay_run_in_shadow(syn, capsys):
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "tower", "--tenant", "1", "--as-of", "2026-06-30", "--backtest-weeks", "0"]) == 0
    assert "RCM control tower" in capsys.readouterr().out
    assert cli.main(["--db-url", url, "tower", "--tenant", "1", "--as-of", "2026-06-30", "--backtest-weeks", "0",
                     "--json"]) == 0  # fmt: skip
    assert json.loads(capsys.readouterr().out)["tenant_id"] == 1
    assert cli.main(["--db-url", url, "a14", "sweep", "--tenant", "1", "--from", "2026-06-20", "--to", "2026-06-30"]) == 0
    assert "11 daily tower events added" in capsys.readouterr().out
    assert cli.main(["--db-url", url, "a14", "replay", "--tenant", "1"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    summary = summarize(syn["engine"], 1)
    print(format_summary(summary))
    assert summary["days"] == 11 and summary["executed"] == 0
