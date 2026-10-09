"""M7 tests: the A8 denial agent in shadow mode, on the synthetic history and on hand-built cases."""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

import krisnai.model as m
from krisnai import cli
from krisnai.agents.a8_denial import (
    ACTION_TYPES,
    DEFAULT_ROUTES,
    A8DenialAgent,
    format_summary,
    load_routes,
    seed_defaults,
    summarize,
)
from krisnai.engine import approve, list_requests, replay, run, set_policy
from krisnai.ingest.loader import ingest_path
from krisnai.match import run_matching
from krisnai.model import tenant_session
from tests.fixtures import make_synthetic as ms
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal


def seed(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        n = seed_defaults(s)
        s.commit()
    return n


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).order_by(m.DecisionRecord.id)))


def payloads(engine, tenant=1):
    return [json.loads(r.action_payload) for r in records(engine, tenant)]


# ---------------------------------------------------------------------------- synthetic history replay


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a8")
    ms.generate(root / "data", seed=5, n_claims=200)
    engine = make_engine(root / "db.sqlite")
    ingest_path(engine, 1, root / "data", SALT)
    run_matching(engine, 1)
    seed(engine)
    items = replay(engine, 1, A8DenialAgent())
    with open(root / "data" / "ground_truth.csv", newline="", encoding="utf8") as f:
        truth = [g for g in csv.DictReader(f) if g["issue_type"] in ("denial", "timely_filing")]
    return {"engine": engine, "items": items, "truth": truth, "root": root}


def test_replay_assigns_category_owner_and_deadline_to_every_planted_denial(syn, capsys):
    recs = records(syn["engine"])
    pays = {p["claim"]: p for p in payloads(syn["engine"])}
    truth = {g["claim_id"]: g for g in syn["truth"]}
    assert len(recs) == len(truth) == 23 and set(pays) == set(truth)
    owner_of = {c: o for c, _, o, _, _ in DEFAULT_ROUTES}
    for claim, g in truth.items():
        p = pays[claim]
        assert p["owner"] == owner_of[g["carc"]] and p["carcs"][0] == g["carc"]
        assert p["category"] and p["disposition"] and date.fromisoformat(p["deadline"])
        assert not p["unrouted"]
    print("\n" + format_summary(summarize(syn["engine"], 1)))


def test_replay_executes_nothing_and_records_in_shadow(syn):
    assert {r.outcome for r in records(syn["engine"])} == {"shadow"}
    assert {r.mode for r in records(syn["engine"])} == {"shadow"}
    assert {r.action_type for r in records(syn["engine"])} <= set(ACTION_TYPES)
    assert summarize(syn["engine"], 1)["totals"]["executed"] == 0


def test_replay_twice_is_identical(syn):
    again = replay(syn["engine"], 1, A8DenialAgent())
    assert [(i.event_id, i.fingerprint) for i in again] == [(i.event_id, i.fingerprint) for i in syn["items"]]
    assert len(records(syn["engine"])) == 23


def test_each_decision_prices_the_denial_like_the_leakage_report(syn):
    """A15 and A8 must agree on the dollars of a full denial."""
    from krisnai.agents.a15_lite import run_a15

    res = run_a15(syn["engine"], 1, ms.AS_OF, syn["root"] / "a15")
    a15 = {f.claim: f.expected_amount for f in res.findings if f.type in ("denial", "timely_filing")}
    a8 = {p["claim"]: D(p["amount_at_risk"]) for p in payloads(syn["engine"])}
    assert a8 == a15


def test_appealable_denials_carry_a_stub_draft_and_the_prompt_is_recorded(syn):
    appeals = [(r, json.loads(r.action_payload)) for r in records(syn["engine"]) if r.action_type == "a8_appeal_task"]
    for rec, p in appeals:
        assert p["appeal_draft"].startswith("stub-answer-") and rec.model_id == "stub" and len(rec.prompt_hash) == 64
    fixes = [r for r in records(syn["engine"]) if r.action_type == "a8_fix_task"]
    assert fixes and all(r.model_id is None for r in fixes)  # only appealable denials use the model


def test_the_prompt_holds_no_patient_identifiers(syn):
    members = set()
    with open(syn["root"] / "data" / "visits.csv", newline="", encoding="utf8") as f:
        members = {row["patient_ref"] for row in csv.DictReader(f)}
    blob = " ".join(json.dumps(p) for p in payloads(syn["engine"]))
    assert not any(mem in blob for mem in members)
    agent = A8DenialAgent()
    with tenant_session(syn["engine"], 1) as s:
        for e in s.scalars(select(m.Event).where(m.Event.event_type == "835.remit")):
            if agent.wants(e):
                ctx = agent.context_pack(s, e, e.known_at)
                prompt = agent.model_prompt(ctx, [])
                if prompt:
                    assert not any(mem in prompt for mem in members) and "SYNC" not in prompt
                    break


# ------------------------------------------------------------------------------------ hand-built cases


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.fee("P1", "99213", "100.00")
    jan = date(2026, 1, 5)
    k = b.claim("K1", "P1", "150.00", jan, jan)
    pay = b.payment("P1", jan, "T1", "90.00")
    b.remit(pay, k, "1", "90.00", "10.00", [("CO", "45", "50.00"), ("PR", "2", "10.00")])  # teaches the 10% share
    b.paid_event_pay = pay
    b.engine = engine
    return b


def run_events(b, agent=None):
    """Commit the book, seed routing and run A8 on every event in time order, shadow."""
    b.commit()
    seed(b.engine)
    return replay(b.engine, 1, agent or A8DenialAgent())


def only(engine):
    (p,) = payloads(engine)
    (r,) = records(engine)
    return r, p


def test_a_paid_in_full_remit_and_a_plain_payment_do_not_trigger(book):
    book.payment("P1", date(2026, 1, 9), "T2", "0.00")
    assert run_events(book) == []
    assert records(book.engine) == []


def test_denial_routes_to_coding_as_an_appeal_with_a_deadline(book):
    d = book.claim("D1", "P1", "150.00", date(2026, 1, 5), date(2026, 1, 5))
    pay = book.payment("P1", date(2026, 2, 1), "T3", "0.00")
    book.remit(pay, d, "4", "0.00", "0.00", [("CO", "50", "150.00")])
    run_events(book)
    rec, p = only(book.engine)
    assert rec.action_type == "a8_appeal_task"
    assert (p["owner"], p["category"], p["disposition"], p["trigger"]) == (
        "coding",
        "medical_necessity",
        "appealable",
        "denial",
    )
    assert p["deadline"] == (date(2026, 2, 1) + timedelta(days=180)).isoformat()
    assert D(p["amount_at_risk"]) == D("90.00")  # 100 allowed less the 10% share learned from K1
    assert (p["win_basis"], p["win_probability"]) == ("history wins=0 n=0", "0.5000")  # no history: one half
    assert D(p["expected_recovery"]) == D("45.00")


def test_a_denied_line_inside_a_paid_claim_is_caught(book):
    c = book.claim("L1", "P1", "200.00", date(2026, 1, 5), date(2026, 1, 5))
    pay = book.payment("P1", date(2026, 2, 1), "T4", "90.00")
    book.remit(pay, c, "1", "90.00", "10.00", [], lines=[
        ("99213", "150.00", "90.00", [("CO", "45", "50.00"), ("PR", "2", "10.00")]),
        ("97110", "50.00", "0.00", [("CO", "16", "50.00")]),
    ])  # fmt: skip
    run_events(book)
    rec, p = only(book.engine)
    assert (p["trigger"], p["owner"], p["disposition"], rec.action_type) == (
        "denial_line",
        "billing",
        "correctable",
        "a8_fix_task",
    )
    assert p["cpts"] == ["97110"] and D(p["amount_at_risk"]) == D("50.00") and p["pricing_basis"] == "billed_fallback"


def test_takeback_and_recoupment(book):
    c = book.claim("TB", "P1", "150.00", date(2026, 1, 5), date(2026, 1, 5))
    pay = book.payment("P1", date(2026, 3, 1), "T5", "0.00", plb=[("WO", "-75.00"), ("FB", "-5.00")])
    book.remit(pay, c, "22", "-90.00", "0.00", [("CO", "45", "50.00")])
    run_events(book)
    by_trigger = {
        p["trigger"]: (r.action_type, p) for r, p in zip(records(book.engine), payloads(book.engine), strict=True)
    }
    action, tb = by_trigger["takeback"]
    assert (action, tb["owner"], D(tb["amount_at_risk"])) == ("a8_takeback_review", "billing", D("90.00"))
    action, rc = by_trigger["recoupment"]
    assert (action, rc["owner"], D(rc["amount_at_risk"]), rc["carcs"]) == (
        "a8_recoupment_review",
        "billing",
        D("75.00"),
        ["WO"],
    )
    # the forward-balance PLB (FB) is not a recoupment, and a takeback needs no appeal arithmetic
    assert tb["win_probability"] == "1.0000"


def test_an_unknown_carc_is_flagged_unrouted(book):
    d = book.claim("U1", "P1", "150.00", date(2026, 1, 5), date(2026, 1, 5))
    book.remit(book.payment("P1", date(2026, 2, 1), "T6", "0.00"), d, "4", "0.00", "0.00", [("CO", "999", "150.00")])
    run_events(book)
    rec, p = only(book.engine)
    assert (p["unrouted"], p["category"], p["owner"], p["disposition"]) == (
        True,
        "unrouted",
        "billing",
        "write_off_review",
    )
    assert rec.confidence == D("0.5000")
    assert json.loads(rec.rules_fired)[1] == {
        "rule": "routing_found",
        "result": False,
        "detail": "CARC ['999'] has a row in carc_route",
    }


def test_the_payer_appeal_window_comes_from_the_table(book):
    d = book.claim("W1", "P1", "150.00", date(2026, 1, 5), date(2026, 1, 5))
    book.remit(book.payment("P1", date(2026, 2, 1), "T7", "0.00"), d, "4", "0.00", "0.00", [("CO", "16", "150.00")])
    book.commit()
    with tenant_session(book.engine, 1) as s:
        s.add(m.PayerAppealWindow(payer_id=s.scalars(select(m.Payer)).first().id, appeal_days=30))
        s.commit()
    seed(book.engine)
    replay(book.engine, 1, A8DenialAgent())
    assert only(book.engine)[1]["deadline"] == "2026-03-03"  # Feb 1 + 30 days


def test_win_rate_uses_only_outcomes_known_at_the_time(book):
    """Three earlier P1 denials for CARC 16; one is paid on Feb 10. A denial on Feb 5 cannot see that win; one on Feb 12 can."""
    for i, day in enumerate((date(2026, 2, 1), date(2026, 2, 2), date(2026, 2, 3)), start=1):
        c = book.claim(f"H{i}", "P1", "150.00", date(2026, 1, 5), date(2026, 1, 5))
        book.remit(book.payment("P1", day, f"TH{i}", "0.00"), c, "4", "0.00", "0.00", [("CO", "16", "150.00")])
    h1 = book.s.scalars(select(m.Claim).where(m.Claim.claim_submitter_id == "H1")).one()
    early = book.claim("E1", "P1", "150.00", date(2026, 1, 5), date(2026, 1, 5))
    book.remit(
        book.payment("P1", date(2026, 2, 5), "TE1", "0.00"), early, "4", "0.00", "0.00", [("CO", "16", "150.00")]
    )
    book.remit(
        book.payment("P1", date(2026, 2, 10), "TWIN", "90.00"), h1, "1", "90.00", "10.00", [("PR", "2", "10.00")]
    )
    late = book.claim("E2", "P1", "150.00", date(2026, 1, 5), date(2026, 1, 5))
    book.remit(
        book.payment("P1", date(2026, 2, 12), "TE2", "0.00"), late, "4", "0.00", "0.00", [("CO", "16", "150.00")]
    )
    run_events(book)
    by_claim = {p["claim"]: p for p in payloads(book.engine)}
    assert by_claim["E1"]["win_basis"] == "history wins=0 n=3" and by_claim["E1"]["win_probability"] == "0.2000"  # 1/5
    assert by_claim["E2"]["win_basis"] == "history wins=1 n=4" and by_claim["E2"]["win_probability"] == "0.3333"  # 2/6
    assert by_claim["H1"]["win_basis"] == "history wins=0 n=0"  # the first ever sees no history


# --------------------------------------------------------------------------- rule 4 and the engine policy


def test_a8_can_only_propose_tasks_and_reviews():
    assert set(ACTION_TYPES) == {"a8_fix_task", "a8_appeal_task", "a8_write_off_review", "a8_takeback_review",
                                 "a8_recoupment_review"}  # fmt: skip
    for forbidden in ("write_off", "refund", "change_code", "resubmit", "submit"):
        assert not any(
            a.endswith(forbidden) or forbidden + "_" in a.replace("a8_write_off_review", "") for a in ACTION_TYPES
        )


def test_even_a_live_level_4_policy_cannot_make_replay_act(syn):
    spy = SpyAdapter()
    with tenant_session(syn["engine"], 1) as s:
        for a in ACTION_TYPES:
            set_policy(s, a, mode="live", autonomy_level=4, max_amount=D("100000"))
        s.commit()
    replay(syn["engine"], 1, A8DenialAgent())  # replay takes no adapters and is always shadow
    assert spy.calls == [] and {r.outcome for r in records(syn["engine"])} == {"shadow"}


def test_a_live_level_3_policy_waits_for_a_named_approval(book):
    d = book.claim("A1", "P1", "150.00", date(2026, 1, 5), date(2026, 1, 5))
    book.remit(book.payment("P1", date(2026, 2, 1), "T9", "0.00"), d, "4", "0.00", "0.00", [("CO", "16", "150.00")])
    book.commit()
    seed(book.engine)
    with tenant_session(book.engine, 1) as s:
        set_policy(s, "a8_fix_task", mode="live", autonomy_level=3, approver_role="billing_manager")
        s.commit()
        event_id = s.scalars(select(m.Event).where(m.Event.event_type == "835.remit")).all()[-1].id
    spy = SpyAdapter()
    res = run(book.engine, 1, A8DenialAgent(), event_id, adapters={"a8_fix_task": spy})
    assert res.outcome == "pending_approval" and spy.calls == []
    assert list_requests(book.engine, 1)[0]["action_type"] == "a8_fix_task"
    approve(book.engine, 1, res.approval_id, "Pat", "billing_manager", adapters={"a8_fix_task": spy})
    assert len(spy.calls) == 1 and spy.calls[0][1]["owner"] == "billing"


# ---------------------------------------------------------------------------------- tables and tenancy


def test_seeding_is_idempotent_and_keeps_local_edits(tmp_path):
    engine = make_engine(tmp_path / "s.sqlite")
    assert seed(engine) == len(DEFAULT_ROUTES) and seed(engine) == 0
    with tenant_session(engine, 1) as s:
        row = s.scalars(select(m.CarcRoute).where(m.CarcRoute.carc_code == "16")).one()
        row.owner = "front_desk"
        s.commit()
    seed(engine)
    with tenant_session(engine, 1) as s:
        assert load_routes(s)["16"].owner == "front_desk"


def test_another_tenants_routing_is_not_used(tmp_path):
    engine = make_engine(tmp_path / "t.sqlite")
    seed(engine, 2)  # only tenant 2 has a routing table
    with tenant_session(engine, 1) as s:
        assert load_routes(s) == {}
        assert s.scalar(select(func.count()).select_from(m.CarcRoute)) == 0
    with tenant_session(engine, 2) as s:
        assert len(load_routes(s)) == len(DEFAULT_ROUTES)


def test_cli_seed_and_replay(syn, tmp_path, capsys):
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a8", "seed", "--tenant", "1"]) == 0
    assert "0 routing rows added" in capsys.readouterr().out
    assert cli.main(["--db-url", url, "a8", "replay", "--tenant", "1"]) == 0
    out = capsys.readouterr().out
    assert "shadow: nothing executed" in out and "23 decisions, 0 executed" in out
