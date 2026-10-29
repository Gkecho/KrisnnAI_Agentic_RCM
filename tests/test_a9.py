"""M15 tests: the A9 denial prevention learning agent, learned rules in A5, and the forward and attribution reports."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a1_clearance import A1ClearanceAgent
from krisnnai.agents.a1_clearance import sweep as a1_sweep
from krisnnai.agents.a3_documentation import A3DocumentationAgent
from krisnnai.agents.a3_documentation import sweep as a3_sweep
from krisnnai.agents.a5_prevention import A5PreventionAgent
from krisnnai.agents.a9_learning import (
    ACTION_TYPES,
    APPROVED,
    EVENT_TYPE,
    REJECTED,
    RULE_REVIEW,
    A9LearningAgent,
    DecisionError,
    attribution,
    clusters,
    decide,
    forward,
    format_summary,
    proposals,
    sweep,
)
from krisnnai.engine import NO_ACTION, replay, run
from krisnnai.engine.card import CARD_KEYS
from krisnnai.ingest.loader import ingest_path
from krisnnai.match.engine import run_matching
from krisnnai.model import tenant_session
from krisnnai.synthea import build
from tests.fixtures import synthea_mini
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
DAY = date(2026, 6, 30)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "100.00")
    b.fee("P2", "99213", "100.00")
    return b


def filed(b, payer, n, denied, carc="16", cpt="99213", start=date(2026, 3, 1), prefix="C"):
    """n claims for a payer; the first `denied` are denied with `carc`, the rest are paid in full."""
    claims = []
    for i in range(n):
        dos = date.fromordinal(start.toordinal() + i)
        c = b.claim(f"{prefix}{payer}{i:03d}", payer, "150.00", dos, dos, cpt=cpt)
        pay = b.payment(payer, date.fromordinal(dos.toordinal() + 20), f"T{prefix}{payer}{i:03d}",
                        "0.00" if i < denied else "90.00")  # fmt: skip
        if i < denied:
            b.remit(pay, c, "4", "0.00", "0.00", [("CO", carc, "150.00")], cpt=cpt)
        else:
            b.remit(pay, c, "1", "90.00", "10.00", [("CO", "45", "50.00"), ("PR", "2", "10.00")], cpt=cpt)
        claims.append(c)
    return claims


def found(engine, day=DAY):
    with tenant_session(engine, 1) as s:
        return {c.key: c for c in clusters(s, day)}


# ------------------------------------------------------------------------------------------- clusters


def test_a_payer_that_keeps_denying_one_cpt_with_one_carc_is_a_cluster(book):
    filed(book, "P1", 10, 6)
    book.commit()
    c = found(book.engine)["P1|99213|16"]
    assert (c.n_denials, c.n_adjudicated, c.rate) == (6, 10, D("0.6"))


def test_few_denials_or_a_low_rate_are_not_clusters(book):
    filed(book, "P1", 10, 4)  # 4 denials: below the minimum count
    filed(book, "P2", 40, 6, prefix="Z")  # 6 denials but only 15%
    book.commit()
    assert found(book.engine) == {}


def test_contractual_adjustments_and_patient_share_are_not_denials(book):
    filed(book, "P1", 10, 0)  # ten paid claims, all with CARC 45 and PR 2
    book.commit()
    assert found(book.engine) == {}


def test_the_cluster_is_point_in_time(book):
    filed(book, "P1", 10, 6, start=date(2026, 3, 1))
    book.commit()
    early = found(book.engine, date(2026, 3, 25))  # most denials are paid out of the future
    assert early == {} or early["P1|99213|16"].n_denials < 6
    assert found(book.engine, DAY)["P1|99213|16"].n_denials == 6


def test_a_weaker_cpt_on_the_same_denied_claims_is_a_shadow_not_a_second_cluster(tmp_path):
    engine = make_engine(tmp_path / "shadow.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    cs = filed(b, "P1", 10, 6)
    for c in cs[:6]:  # the six denied claims also carry 93000, which is also billed alone on paid claims
        b._add(m.ClaimLine(claim_id=c.id, line_number=2, cpt="93000", charge=D("10"), units=D("1"), unit_basis="UN",
                           service_date=c.service_date))  # fmt: skip
    filed(b, "P1", 10, 0, cpt="93000", start=date(2026, 5, 1), prefix="X")
    b.commit()
    keys = set(found(engine))
    assert "P1|99213|16" in keys and "P1|93000|16" not in keys  # 6 of 16 = 37%: the weaker one is the same defect


# ------------------------------------------------------------------------------------- sweeper + agent


def test_sweeper_raises_one_event_per_new_cluster_and_a_rerun_adds_nothing(book):
    filed(book, "P1", 10, 6)
    book.commit()
    first = sweep(book.engine, 1, date(2026, 4, 1), DAY)
    assert first.events == 1 and not first.skipped
    assert sweep(book.engine, 1, date(2026, 4, 1), DAY).skipped
    again = sweep(book.engine, 1, date(2026, 4, 2), DAY)  # a different window: the cluster was already raised
    assert again.events == 0


def go(b):
    b.commit()
    sweep(b.engine, 1, date(2026, 4, 1), DAY)
    return replay(b.engine, 1, A9LearningAgent())


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a9_learning")))


def test_the_proposal_carries_the_rule_the_measured_effect_and_a_card_for_the_manager(book):
    filed(book, "P1", 10, 6)
    filed(book, "P1", 10, 0, cpt="93000", start=date(2026, 5, 1), prefix="K")
    go(book)
    (rec,) = records(book.engine)
    p = json.loads(rec.action_payload)
    assert rec.action_type == RULE_REVIEW and rec.outcome == "shadow"
    assert (p["payer"], p["cpt"], p["carc"], p["n_denials"], p["n_adjudicated"]) == ("P1", "99213", "16", 6, 10)
    assert D(p["rate"]) == D("0.6") and D(p["recall"]) == D("1") and p["flagged_by_a5"] == 0
    assert p["owner"] == "practice_manager" and set(p["card"]) == set(CARD_KEYS)
    assert D(p["dollars"]) == D("540.00")  # six claims at 100.00 allowed, less the 10% patient share seen on paid ones


def test_a_pattern_a5_already_flags_gets_no_new_rule(book):
    filed(book, "P1", 10, 6)
    book.commit()
    with tenant_session(book.engine, 1) as s:  # the pattern is already an approved rule, so A5 flags every such claim
        payer = s.scalars(select(m.Payer).where(m.Payer.payer_id_code == "P1")).one()
        s.add(m.LearnedRule(rule_key="P1|99213|16", payer_id=payer.id, cpt="99213", carc="16",
                            proposed_on=date(2026, 1, 1), status="approved", n_denials=6, n_adjudicated=10,
                            denial_rate=D("0.6"), approved_by="Test Manager", decided_on=date(2026, 1, 2)))  # fmt: skip
        s.commit()
    replay(book.engine, 1, A5PreventionAgent())  # A5 now flags the claims
    with tenant_session(book.engine, 1) as s:  # the same pattern raised again, as if it were new
        sf = s.scalars(select(m.SourceFile)).first()
        s.add(m.Event(source_file_id=sf.id, event_type=EVENT_TYPE, isa13="20260630", gs06="9", st02="9",
                      seq_in_file=1, known_at=datetime(2026, 6, 30),
                      payload=json.dumps({"rule_key": "P1|99213|16", "payer": "P1", "cpt": "99213", "carc": "16",
                                          "due_on": "2026-06-30"})))  # fmt: skip
        s.commit()
    replay(book.engine, 1, A9LearningAgent())
    (rec,) = records(book.engine)
    assert rec.action_type == NO_ACTION and json.loads(rec.action_payload)["reason"] == "not_already_flagged"


def test_shadow_mode_nothing_runs_and_the_action_is_a_review(book):
    filed(book, "P1", 10, 6)
    book.commit()
    sweep(book.engine, 1, date(2026, 4, 1), DAY)
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == EVENT_TYPE))
    spy = SpyAdapter()
    res = run(book.engine, 1, A9LearningAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, A9LearningAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False
    assert ACTION_TYPES == (RULE_REVIEW,) and RULE_REVIEW.endswith("_review")


def test_replay_is_deterministic_and_tenants_are_isolated(tmp_path):
    def once(name):
        engine = make_engine(tmp_path / name)
        b = Book(engine, 1)
        b.engine = engine
        b.fee("P1", "99213", "100.00")
        filed(b, "P1", 10, 6)
        b.commit()
        sweep(engine, 1, date(2026, 4, 1), DAY)
        return engine, [(i.outcome, i.fingerprint) for i in replay(engine, 1, A9LearningAgent())]

    (e1, a), (_, b_) = once("a.sqlite"), once("b.sqlite")
    assert a == b_ and records(e1, 2) == []


# ------------------------------------------------------------------------------ approval and A5 use


def test_a_person_must_be_named_and_the_proposal_must_exist(book):
    filed(book, "P1", 10, 6)
    go(book)
    with pytest.raises(DecisionError):
        decide(book.engine, 1, "P1|99213|16", APPROVED, "   ")
    with pytest.raises(DecisionError):
        decide(book.engine, 1, "P9|99213|16", APPROVED, "Test Manager")
    out = decide(book.engine, 1, "P1|99213|16", APPROVED, "Test Manager", date(2026, 7, 1))
    assert out["status"] == APPROVED and out["by"] == "Test Manager"
    (item,) = proposals(book.engine, 1)
    assert item["status"] == "approved" and item["approved_by"] == "Test Manager"


def a5_flags(engine):
    replay(engine, 1, A5PreventionAgent())
    out = {}
    with tenant_session(engine, 1) as s:
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a5_prevention")):
            p = json.loads(rec.action_payload)
            out[p["claim"]] = [f["rule"] for f in p.get("failed_rules", [])]
    return out


def test_only_an_approved_rule_changes_a5_and_a5_is_unchanged_before_that(tmp_path):
    def fresh(name):
        engine = make_engine(tmp_path / name)
        b = Book(engine, 1)
        b.engine = engine
        b.fee("P1", "99213", "100.00")
        filed(b, "P1", 10, 6)
        sweep_dates = (date(2026, 4, 1), DAY)
        b.commit()
        sweep(engine, 1, *sweep_dates)
        replay(engine, 1, A9LearningAgent())
        return engine

    before = a5_flags(fresh("before.sqlite"))
    assert all("learned_pattern" not in rules for rules in before.values())

    proposed = fresh("proposed.sqlite")  # proposed, not decided: no effect
    assert a5_flags(proposed) == before

    rejected = fresh("rejected.sqlite")
    decide(rejected, 1, "P1|99213|16", REJECTED, "Test Manager")
    assert a5_flags(rejected) == before

    approved = fresh("approved.sqlite")
    decide(approved, 1, "P1|99213|16", APPROVED, "Test Manager")
    after = a5_flags(approved)
    assert after and all("learned_pattern" in rules for rules in after.values())  # every P1 + 99213 claim is flagged


# ------------------------------------------------------------------------------------ forward test


def test_forward_test_counts_flagged_hits_and_misses_on_claims_filed_after_the_proposal(book):
    filed(book, "P1", 10, 6)  # history that produces the proposal
    # claims filed after the proposal (unknown to the sweeps, which stop on June 30): 5 carry the CPT and 2 are
    # denied with CARC 16; one more CARC 16 denial is on another CPT, which the rule would not have flagged
    filed(book, "P1", 5, 2, start=date(2026, 7, 5), prefix="F")
    filed(book, "P1", 1, 1, cpt="93000", start=date(2026, 7, 20), prefix="G")
    go(book)
    decide(book.engine, 1, "P1|99213|16", APPROVED, "Test Manager", date(2026, 7, 1))
    with tenant_session(book.engine, 1) as s:  # the rule was proposed on the last day of June
        s.scalars(select(m.LearnedRule)).first().proposed_on = date(2026, 6, 30)
        s.commit()
    (r,) = forward(book.engine, 1, date(2026, 9, 30))
    assert (r["flagged"], r["hits"], r["all_denials"]) == (5, 2, 3)
    assert D(r["precision"]) == D("0.4") and D(r["recall"]).quantize(D("0.01")) == D("0.67")


# --------------------------------------------------------------------------------------- Synthea book


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a9")
    raw = synthea_mini.write(root / "raw", n_claims=1200, n_patients=150, seed=5)
    build(raw, root / "book", DAY, seed=7, documentation=True, eligibility=True,
          denial_patterns=["SYNMEDICARE:99213:16:0.7:2025-11-01"])  # fmt: skip
    engine = make_engine(root / "db.sqlite")
    ingest_path(engine, 1, root / "book", SALT)
    run_matching(engine, 1)
    replay(engine, 1, A5PreventionAgent())
    a1_sweep(engine, 1, date(2025, 3, 1), DAY)
    replay(engine, 1, A1ClearanceAgent())
    a3_sweep(engine, 1, date(2025, 3, 1), DAY)
    replay(engine, 1, A3DocumentationAgent())
    sweep(engine, 1, date(2025, 3, 1), DAY, every_days=14)
    replay(engine, 1, A9LearningAgent())
    return {"root": root, "engine": engine}


@pytest.mark.slow
def test_the_planted_pattern_is_the_only_proposal(syn):
    keys = [p["rule_key"] for p in proposals(syn["engine"], 1)]
    assert keys == ["SYNMEDICARE|99213|16"]
    assert "proposed" in format_summary(proposals(syn["engine"], 1), 1) or "SYNMEDICARE" in format_summary(
        proposals(syn["engine"], 1), 1)


@pytest.mark.slow
def test_after_approval_a5_flags_the_pattern_and_the_forward_test_measures_it(syn):
    engine = syn["engine"]
    truth = list(csv.DictReader((syn["root"] / "book" / "pattern_truth.csv").open()))
    assert len(truth) >= 10
    decide(engine, 1, "SYNMEDICARE|99213|16", APPROVED, "Test Manager", DAY)
    (r,) = forward(engine, 1, DAY)
    assert r["hits"] >= 5 and D(r["precision"]) > D("0.4") and D(r["recall"]) > D("0.8")
    assert D(r["dollars_held"]) > 0


@pytest.mark.slow
def test_attribution_sends_coverage_denials_to_a1_and_documents_the_rest(syn):
    a = attribution(syn["engine"], 1, DAY)
    truth = list(csv.DictReader((syn["root"] / "book" / "ground_truth.csv").open()))
    coverage = [t for t in truth if t["issue_type"] == "denial" and t["carc"] in ("27", "31")]
    assert coverage and a["by_source"]["a1"]["denials"] >= len(coverage)
    assert a["total_denials"] >= sum(v["denials"] for k, v in a["by_source"].items() if k == "none")
    assert set(a["by_source"]) <= {"a1", "a3", "a5", "none"}


@pytest.mark.slow
def test_cli_a9_replays_in_shadow_and_a_decision_needs_a_name(syn, tmp_path, capsys):
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a9", "replay", "--tenant", "1"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        cli.main(["--db-url", url, "a9", "approve", "--tenant", "1", "--rule", "NOPE|1|2", "--by", "X"])
    with pytest.raises(SystemExit):  # argparse: --by is required
        cli.main(["--db-url", url, "a9", "approve", "--tenant", "1", "--rule", "SYNMEDICARE|99213|16"])


def test_default_synthea_output_is_unchanged_without_a_pattern(syn, tmp_path):
    raw = syn["root"] / "raw"
    a, b = tmp_path / "a", tmp_path / "b"
    build(raw, a, DAY, seed=7)
    build(raw, b, DAY, seed=7, denial_patterns=[])
    assert not (a / "pattern_truth.csv").exists()
    digest = lambda d: {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(d.iterdir())}  # noqa: E731
    assert digest(a) == digest(b)
