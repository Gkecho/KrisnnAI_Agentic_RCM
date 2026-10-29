"""M20 tests: the A4 coding audit (shadow, suggestions only) on documented elements, and the Synthea book."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a4_coding import (
    ACTION_TYPES,
    CODING_REVIEW,
    COULD_BE_HIGHER,
    UNSUPPORTED,
    A4CodingAgent,
    check,
    format_variance,
    supported_level,
    variance,
)
from krisnnai.agents.a4_coding import config as cfg
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
DOS = date(2026, 5, 4)
BASE = {"assessment", "plan"}
EXTRA = set(cfg.EXTRA)


# ------------------------------------------------------------------------------------------- the rules


def test_level_support_comes_from_named_elements():
    assert supported_level("established", BASE) == "99213"
    assert supported_level("established", BASE | EXTRA) == "99214"
    assert supported_level("new", BASE | {"history_detailed"}) == "99203"  # one of the two is not enough
    assert supported_level("new", BASE | EXTRA) == "99204"


def test_a_billed_level_that_the_note_supports_is_not_flagged():
    assert check("99213", BASE, True) == (None, "judged")
    assert check("99214", BASE | EXTRA, True) == (None, "judged")


def test_overcoding_and_undercoding_are_findings_with_the_documented_level():
    finding, reason = check("99214", BASE, True)
    assert reason == "judged" and (finding.kind, finding.billed, finding.documented) == (UNSUPPORTED, "99214", "99213")
    assert finding.missing == cfg.EXTRA
    finding, _ = check("99213", BASE | EXTRA, True)
    assert (finding.kind, finding.billed, finding.documented) == (COULD_BE_HIGHER, "99213", "99214")
    assert check("99204", BASE, True)[0].documented == "99203"  # the new-patient family is kept apart


def test_unsigned_missing_baseline_and_non_levelled_codes_are_not_judged():
    assert check("99214", BASE | EXTRA, False) == (None, "no_signed_note")
    assert check("99214", None, True) == (None, "no_signed_note")
    assert check("99214", {"plan"}, True) == (None, "baseline_missing")  # incomplete notes are A3's finding
    assert check("93000", BASE, True) == (None, "not_levelled")
    assert check("99283", BASE, True) == (None, "not_levelled")


# ----------------------------------------------------------------------- agent (hand-built book)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "92.00")
    b.fee("P1", "99214", "130.00")
    return b


def level_claim(b, sid, cpt, elements, signed=True):
    c = b.claim(sid, "P1", "150.00", DOS, date(2026, 5, 6), cpt=cpt)
    b.visit("V" + sid, "P1", DOS, cpt=cpt)
    b.note("V" + sid, DOS, DOS if signed else None, elements=elements)
    return c


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a4_coding")))


def go(b):
    b.commit()
    return replay(b.engine, 1, A4CodingAgent())


def test_an_unsupported_level_becomes_one_coder_review_with_the_dollar_difference(book):
    book.claim("C1", "P1", "180.00", DOS, date(2026, 5, 6), cpt="99214")
    book.visit("V1", "P1", DOS, cpt="99214")
    book.note("V1", DOS, DOS, elements="assessment,plan")
    go(book)
    (rec,) = records(book.engine)
    p = json.loads(rec.action_payload)
    assert rec.action_type == CODING_REVIEW and rec.outcome == "shadow" and p["owner"] == "coder"
    assert p["risk"] == "compliance" and D(p["difference"]) == D("38.00")  # 130.00 - 92.00 at this payer's contract
    f = p["findings"][0]
    assert (f["kind"], f["billed"], f["documented"]) == (UNSUPPORTED, "99214", "99213")
    assert set(p["card"]) == set(CARD_KEYS) and any("certified coder decides" in line for line in p["card"]["why"])


def test_an_under_coded_level_is_a_revenue_signal_not_a_compliance_one(book):
    level_claim(book, "C2", "99213", "assessment,plan,history_detailed,exam_expanded")
    go(book)
    (rec,) = records(book.engine)
    p = json.loads(rec.action_payload)
    assert p["risk"] == "revenue" and p["findings"][0]["kind"] == COULD_BE_HIGHER and D(p["difference"]) == D("38.00")


def test_a_supported_claim_is_no_action_and_an_unsigned_note_is_left_alone(book):
    level_claim(book, "C3", "99214", "assessment,plan,history_detailed,exam_expanded")
    level_claim(book, "C4", "99214", "assessment,plan", signed=False)
    go(book)
    assert {r.action_type for r in records(book.engine)} == {NO_ACTION}


def test_shadow_mode_nothing_runs_and_no_action_can_change_a_code(book):
    level_claim(book, "C5", "99214", "assessment,plan")
    book.commit()
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == "837P.claim"))
    spy = SpyAdapter()
    res = run(book.engine, 1, A4CodingAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, A4CodingAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False
    assert ACTION_TYPES == (CODING_REVIEW,) and CODING_REVIEW.endswith("_review")
    banned = ("change", "set_code", "update", "recode", "apply", "modifier", "submit", "hold", "write")
    assert not any(w in a for a in ACTION_TYPES for w in banned)
    p = json.loads(records(book.engine)[0].action_payload)
    assert "suggested_code" not in p and "new_cpt" not in p  # nothing in the payload is a value to apply


def test_replay_is_deterministic_and_tenants_are_isolated(tmp_path):
    def once(name):
        engine = make_engine(tmp_path / name)
        b = Book(engine, 1)
        b.engine = engine
        b.fee("P1", "99213", "92.00")
        b.fee("P1", "99214", "130.00")
        level_claim(b, "C1", "99214", "assessment,plan")
        b.commit()
        return engine, [(i.outcome, i.fingerprint) for i in replay(engine, 1, A4CodingAgent())]

    (e1, a), (_, b_) = once("a.sqlite"), once("b.sqlite")
    assert a == b_ and records(e1, 2) == []


# ------------------------------------------------------------------------------------- Synthea book


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a4")
    raw = synthea_mini.write(root / "raw", n_claims=2000, n_patients=200, seed=5)
    as_of = date(2026, 6, 30)
    build(raw, root / "book", as_of, seed=7, documentation=True, coding=True)
    engine = make_engine(root / "db.sqlite")
    ingest_path(engine, 1, root / "book", SALT)
    run_matching(engine, 1)
    replay(engine, 1, A4CodingAgent())
    truth = list(csv.DictReader((root / "book" / "coding_truth.csv").open()))
    return {"root": root, "engine": engine, "truth": truth, "as_of": as_of}


def test_every_planted_over_and_under_code_is_found_with_the_dollars_and_nothing_else(syn):
    found = {}
    with tenant_session(syn["engine"], 1) as s:
        for rec in s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a4_coding")):
            p = json.loads(rec.action_payload)
            for f in p.get("findings", []):
                found[(p["claim"], f["line_number"])] = (f["kind"], f["billed"], f["documented"], D(f["difference"]))
    kind = {"upcoded": UNSUPPORTED, "undercoded": COULD_BE_HIGHER}
    want = {(t["claim_id"], int(t["line_no"])): (kind[t["defect"]], t["billed"], t["documented"], D(t["difference"]))
            for t in syn["truth"]}  # fmt: skip
    assert {t["defect"] for t in syn["truth"]} == {"upcoded", "undercoded"}
    assert found == want


def test_audit_variance_matches_the_planted_counts_and_the_cli_stays_in_shadow(syn, tmp_path, capsys):
    v = variance(syn["engine"], 1)
    over = sum(1 for t in syn["truth"] if t["defect"] == "upcoded")
    under = sum(1 for t in syn["truth"] if t["defect"] == "undercoded")
    assert v["by_kind"][UNSUPPORTED]["lines"] == over and v["by_kind"][COULD_BE_HIGHER]["lines"] == under
    assert v["lines_judged"] > over + under and "a coder decides" in format_variance(v)
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a4", "variance", "--tenant", "1"]) == 0
    assert "audit variance" in capsys.readouterr().out
    raw = syn["root"] / "raw"
    a, b = tmp_path / "plain", tmp_path / "plain2"
    build(raw, a, syn["as_of"], seed=7, documentation=True)
    build(raw, b, syn["as_of"], seed=7, documentation=True, coding=False)
    assert not (a / "coding_truth.csv").exists()
    digest = lambda x: {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(x.iterdir())}  # noqa: E731
    assert digest(a) == digest(b)
    with pytest.raises(ValueError):
        build(raw, tmp_path / "bad", syn["as_of"], seed=7, coding=True)  # needs --documentation
