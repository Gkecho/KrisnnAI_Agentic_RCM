"""M8 tests: the A5 claim prevention agent in shadow mode, on hand-built claims and on the synthetic history."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a5_prevention import ACTION_TYPES, A5PreventionAgent, format_summary, seed_defaults, summarize
from krisnnai.engine import NO_ACTION, fingerprint, replay, run
from krisnnai.ingest.loader import ingest_path
from krisnnai.model import tenant_session
from tests.fixtures import make_synthetic as ms
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
DOS = date(2026, 5, 1)
SUBMIT = date(2026, 5, 10)


def seed(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        n = seed_defaults(s)
        s.commit()
    return n


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).order_by(m.DecisionRecord.id)))


def by_claim(engine, tenant=1):
    return {json.loads(r.action_payload)["claim"]: r for r in records(engine, tenant)}


def add_claim(b, sid, lines=(("99213", (), 1),), payer="P1", dos=DOS, known=SUBMIT, dx=True, pointer="1",
              patient=None, charge="150.00"):  # fmt: skip
    """A claim built straight from model objects. `lines` is (cpt, modifiers, units) per line."""
    c = m.Claim(event_id=b.event(known, "837P.claim", st02=sid, gs06=sid), payer_id=b.payer(payer).id,
                provider_id=b.provider.id, patient_ref_id=(patient or b.patient).id, claim_submitter_id=sid,
                total_charge=D(charge), place_of_service="11", frequency_code="1", service_date=dos,
                submitted_on=known)  # fmt: skip
    b._add(c)
    for i, (cpt, mods, units) in enumerate(lines, start=1):
        mod = dict(zip(("modifier_1", "modifier_2", "modifier_3", "modifier_4"), mods, strict=False))
        b._add(m.ClaimLine(claim_id=c.id, line_number=i, cpt=cpt, charge=D(charge), units=D(units), unit_basis="UN",
                           diagnosis_pointer=pointer if pointer else None, service_date=dos, **mod))  # fmt: skip
    if dx:
        b._add(m.ClaimDx(claim_id=c.id, seq=1, dx_qualifier="ABK", dx_code="M5450"))
    return c


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    return b


def go(b, agent=None, seeded=True):
    b.commit()
    if seeded:
        seed(b.engine)
    return replay(b.engine, 1, agent or A5PreventionAgent())


def failed_rules(rec):
    return {f["rule"] for f in json.loads(rec.action_payload).get("failed_rules", [])}


# ------------------------------------------------------------------------------------ hand-built cases


def test_a_clean_claim_proposes_nothing(book):
    add_claim(book, "OK1")
    go(book)
    (rec,) = records(book.engine)
    assert rec.action_type == NO_ACTION and rec.outcome == NO_ACTION
    assert json.loads(rec.action_payload)["not_evaluated"] == ["eligibility_on_dos", "auth_units"]


def test_missing_diagnosis_and_pointer_is_a_billing_fix(book):
    add_claim(book, "R1", dx=False, pointer="")
    go(book)
    (rec,) = records(book.engine)
    p = json.loads(rec.action_payload)
    assert rec.action_type == "a5_fix_task" and p["owner"] == "billing" and failed_rules(rec) == {"required_fields"}
    assert "diagnoses" in p["failed_rules"][0]["detail"] and "diagnosis_pointer" in p["failed_rules"][0]["detail"]


def test_ncci_pair_without_modifier_holds_the_claim_and_a_modifier_clears_it(book):
    add_claim(book, "N1", lines=(("97140", (), 1), ("97530", (), 1)))
    add_claim(book, "N2", lines=(("97140", (), 1), ("97530", ("59",), 1)), dos=date(2026, 5, 2))
    add_claim(book, "N3", lines=(("99213", (), 1), ("99214", ("25",), 1)), dos=date(2026, 5, 3))
    go(book)
    recs = by_claim(book.engine)
    assert recs["N1"].action_type == "a5_hold_review" and failed_rules(recs["N1"]) == {"ncci_pair"}
    assert recs["N2"].action_type == NO_ACTION  # a modifier bypasses an indicator-1 pair
    assert recs["N3"].action_type == "a5_hold_review"  # indicator 0: never together, modifier or not


def test_mue_over_the_limit_is_a_coding_fix(book):
    add_claim(book, "M1", lines=(("97110", (), 3), ("97110", (), 2)))  # 5 units on one date, limit 4
    add_claim(book, "M2", lines=(("97110", (), 4),), dos=date(2026, 5, 2))
    go(book)
    recs = by_claim(book.engine)
    p = json.loads(recs["M1"].action_payload)
    assert (
        recs["M1"].action_type == "a5_fix_task" and p["owner"] == "coding" and failed_rules(recs["M1"]) == {"mue_units"}
    )
    assert recs["M2"].action_type == NO_ACTION


def test_timely_filing_uses_the_payer_row_and_holds_when_close_or_past(book):
    book.payer("P2")
    book.s.flush()
    book.s.add(m.PayerFilingWindow(payer_id=book.payers["P2"].id, filing_days=90))
    add_claim(book, "T1", dos=date(2025, 4, 1), known=date(2026, 5, 10))  # default 365 days, deadline 2026-04-01: past
    add_claim(book, "T2", dos=date(2026, 3, 1), known=date(2026, 5, 10), payer="P2")  # 90 days, deadline 05-30: 20 left
    add_claim(book, "T3", dos=date(2026, 5, 1), known=date(2026, 5, 10), payer="P2")  # 81 days left: fine
    go(book)
    recs = by_claim(book.engine)
    assert recs["T1"].action_type == "a5_hold_review" and failed_rules(recs["T1"]) == {"timely_filing"}
    assert recs["T2"].action_type == "a5_hold_review" and "20 days left of 90" in json.dumps(
        json.loads(recs["T2"].action_payload)["failed_rules"]
    )
    assert recs["T3"].action_type == NO_ACTION


def test_duplicate_is_flagged_on_the_later_claim_only(book):
    add_claim(book, "D1", known=date(2026, 5, 10))
    add_claim(book, "D2", known=date(2026, 5, 12))
    add_claim(book, "D3", lines=(("99213", (), 1), ("85025", (), 1)), known=date(2026, 5, 13))  # different codes
    go(book)
    recs = by_claim(book.engine)
    assert recs["D1"].action_type == NO_ACTION  # point in time: D2 did not exist yet
    assert recs["D2"].action_type == "a5_hold_review" and failed_rules(recs["D2"]) == {"duplicate_claim"}
    assert recs["D3"].action_type == NO_ACTION


def test_a_rejected_original_is_not_a_duplicate_of_its_correction(book):
    first = add_claim(book, "J1", known=date(2026, 5, 10))
    book.ack_277ca(first, "A3", date(2026, 5, 11), code="21")  # returned by the 277CA: never adjudicated
    add_claim(book, "J2", known=date(2026, 5, 12))  # the corrected original, filed after the rejection
    add_claim(book, "K1", dos=date(2026, 5, 2), known=date(2026, 5, 10))
    book.ack_999("K1", "R", date(2026, 5, 11), errors="IK5:5")  # the 999 rejected K1's whole file
    add_claim(book, "K2", dos=date(2026, 5, 2), known=date(2026, 5, 12))
    add_claim(book, "L1", dos=date(2026, 5, 3), known=date(2026, 5, 10))
    add_claim(book, "L2", dos=date(2026, 5, 3), known=date(2026, 5, 12))  # L1 was accepted, so L2 is a real duplicate
    go(book)
    recs = by_claim(book.engine)
    assert recs["J2"].action_type == NO_ACTION and recs["K2"].action_type == NO_ACTION
    assert recs["L2"].action_type == "a5_hold_review" and failed_rules(recs["L2"]) == {"duplicate_claim"}


# --------------------------------------------------------------------------------- engine guarantees


def test_shadow_never_reaches_an_adapter_and_a_rerun_creates_nothing(book):
    add_claim(book, "S1", dx=False)
    book.commit()
    seed(book.engine)
    spy = SpyAdapter()
    with tenant_session(book.engine, 1) as s:
        (eid,) = list(s.scalars(select(m.Event.id)))
    res = run(book.engine, 1, A5PreventionAgent(), eid, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == []
    again = run(book.engine, 1, A5PreventionAgent(), eid, adapters={a: spy for a in ACTION_TYPES})
    assert again.created is False and again.record_id == res.record_id and len(records(book.engine)) == 1


def test_replay_is_deterministic(book):
    add_claim(book, "P1x", dx=False)
    add_claim(book, "P2x", lines=(("97140", (), 1), ("97530", (), 1)), dos=date(2026, 5, 2))
    first = go(book)
    second = replay(book.engine, 1, A5PreventionAgent())
    assert [i.fingerprint for i in first] == [i.fingerprint for i in second] and len(first) == 2
    with tenant_session(book.engine, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.DecisionRecord)) == 2
        assert all(fingerprint(r) for r in s.scalars(select(m.DecisionRecord)))


def test_rule_data_and_records_do_not_cross_tenants(book):
    add_claim(book, "X1", lines=(("97140", (), 1), ("97530", (), 1)))
    book.commit()
    seed(book.engine, tenant=1)  # tenant 2 gets no NCCI rows
    b2 = Book(book.engine, 2, tag="b")
    add_claim(b2, "X1", lines=(("97140", (), 1), ("97530", (), 1)))
    b2.commit()
    replay(book.engine, 1, A5PreventionAgent())
    replay(book.engine, 2, A5PreventionAgent())
    assert by_claim(book.engine, 1)["X1"].action_type == "a5_hold_review"
    assert by_claim(book.engine, 2)["X1"].action_type == NO_ACTION  # tenant 1's NCCI table is invisible to tenant 2
    assert len(records(book.engine, 1)) == len(records(book.engine, 2)) == 1


def test_records_carry_no_patient_identifier(book):
    add_claim(book, "PHI1", dx=False)
    go(book)
    (rec,) = records(book.engine)
    text = rec.input_snapshot + rec.action_payload
    assert "ref_hash" not in text and "patient" not in text.lower() and "member" not in text.lower()


# ------------------------------------------------------------------------------------ synthetic history


def test_replay_over_the_synthetic_history_runs_every_claim_and_executes_nothing(tmp_path, capsys):
    ms.generate(tmp_path / "data", seed=5, n_claims=200)
    engine = make_engine(tmp_path / "db.sqlite")
    ingest_path(engine, 1, tmp_path / "data", SALT)
    assert cli.main(["--db-url", str(engine.url), "a5", "seed", "--tenant", "1"]) == 0
    assert "4 rule rows added" in capsys.readouterr().out
    assert cli.main(["--db-url", str(engine.url), "a5", "replay", "--tenant", "1"]) == 0
    out = capsys.readouterr().out
    with tenant_session(engine, 1) as s:
        claims = s.scalar(select(func.count()).select_from(m.Claim))
    summary = summarize(engine, 1)
    print("\n" + format_summary(summary))
    assert summary["claims"] == claims and summary["executed"] == 0
    assert "shadow: nothing executed" in out and f"{claims} claims checked" in out
