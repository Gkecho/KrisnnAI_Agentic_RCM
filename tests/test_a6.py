"""M10 tests: the A6 rejection-handling agent in shadow mode, on hand-built claims and on the synthetic history."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a5_prevention import seed_defaults as seed_a5
from krisnnai.agents.a6_submission import (
    ACTION_TYPES,
    DEFAULT_ROUTES,
    A6SubmissionAgent,
    format_summary,
    summarize,
    trigger_source,
)
from krisnnai.agents.a6_submission import seed_defaults as seed_a6
from krisnnai.engine import NO_ACTION, approve, fingerprint, list_requests, replay, run, set_policy
from krisnnai.engine.adapters import ClearinghouseStub
from krisnnai.ingest.loader import ingest_path
from krisnnai.model import tenant_session
from tests.fixtures import make_synthetic as ms
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
DOS = date(2026, 5, 1)
SUBMIT = date(2026, 5, 10)
ACK = date(2026, 5, 12)


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    return b


def add_claim(b, sid, lines=(("99213", (), 1),), payer="P1", dos=DOS, group=None, dx=True, pointer="1", charge="150.00"):
    """A claim built from model objects. `lines` is (cpt, modifiers, units); `group` = (GS06, ST02) shared by a file."""
    gs06, st02 = group or (sid, sid)
    c = m.Claim(event_id=b.event(SUBMIT, "837P.claim", st02=st02, gs06=gs06), payer_id=b.payer(payer).id,
                provider_id=b.provider.id, patient_ref_id=b.patient.id, claim_submitter_id=sid,
                total_charge=D(charge), place_of_service="11", frequency_code="1", service_date=dos,
                submitted_on=SUBMIT)  # fmt: skip
    b._add(c)
    for i, (cpt, mods, units) in enumerate(lines, start=1):
        mod = dict(zip(("modifier_1", "modifier_2", "modifier_3", "modifier_4"), mods, strict=False))
        b._add(m.ClaimLine(claim_id=c.id, line_number=i, cpt=cpt, charge=D(charge), units=D(units), unit_basis="UN",
                           diagnosis_pointer=pointer or None, service_date=dos, **mod))  # fmt: skip
    if dx:
        b._add(m.ClaimDx(claim_id=c.id, seq=1, dx_qualifier="ABK", dx_code="M5450"))
        b._add(m.ClaimDx(claim_id=c.id, seq=2, dx_qualifier="ABF", dx_code="G8929"))
    return c


def seed(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        n = seed_a6(s)
        seed_a5(s)
        s.commit()
    return n


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).order_by(m.DecisionRecord.id)))


def payload(rec):
    return json.loads(rec.action_payload)


def go(b, seeded=True):
    b.commit()
    if seeded:
        seed(b.engine)
    return replay(b.engine, 1, A6SubmissionAgent())


# --------------------------------------------------------------------------------------------- triggers


def test_only_rejection_acknowledgements_trigger_the_agent(book):
    claims = [add_claim(book, f"T{i}", dos=date(2026, 5, i + 1)) for i in range(1, 6)]
    for c, cat in zip(claims, ("A1", "A2", "A3", "A4", "A3"), strict=True):
        book.ack_277ca(c, cat, ACK, code="21" if cat == "A3" else None)
    for sid, status in (("N1", "A"), ("N2", "R"), ("N3", "E")):
        add_claim(book, sid, dos=date(2026, 6, 1))
        book.ack_999(sid, status, ACK, errors="IK5:5" if status != "A" else None)
    items = go(book)
    assert len(items) == 5  # A3, A4, A3 from the 277CA; R and E from the 999
    with tenant_session(book.engine, 1) as s:
        events = list(s.scalars(select(m.Event).where(m.Event.event_type.in_(["277CA.claim_status", "999.ack"]))))
    assert sorted(bool(trigger_source(e)) for e in events).count(True) == 5


# ------------------------------------------------------------------------------------------ routing


def test_a_277ca_return_is_a_business_task_for_billing_with_a_card(book):
    c = add_claim(book, "B1", dos=date(2026, 5, 1))
    book.ack_277ca(c, "A3", ACK, code="21", payer_claim_number="PCN1")
    (item,) = go(book)
    (rec,) = records(book.engine)
    p = payload(rec)
    assert rec.action_type == "a6_rejection_task" and item.outcome == "shadow"
    assert (p["kind"], p["owner"], p["category"], p["unrouted"]) == ("business", "billing", "missing_or_invalid_information", False)
    assert p["claims"] == ["B1"] and p["packets"] == []  # packets only go with technical resubmissions
    assert set(p["card"]) == {"title", "why", "priority", "expected_value", "deadline", "owner", "next_steps", "evidence"}
    assert p["fix_by"] == "2026-05-15" and p["card"]["deadline"] == "2026-05-15"


def test_a_999_rejection_is_technical_and_names_every_claim_in_the_transaction_set_only(book):
    for sid in ("F1", "F2"):
        add_claim(book, sid, group=("G7", "0001"), dos=date(2026, 5, 3))
    add_claim(book, "OTHER", group=("G8", "0001"), dos=date(2026, 5, 3))  # a different file
    book.ack_999("F1", "R", ACK, errors="IK5:5", gs06="G7", st02="0001")
    go(book)
    (rec,) = records(book.engine)
    p = payload(rec)
    assert rec.action_type == "a6_resubmit_review" and p["kind"] == "technical" and p["source"] == "999"
    assert sorted(p["claims"]) == ["F1", "F2"] and p["claims_total"] == 2 and len(p["packets"]) == 2
    assert p["error_codes"] == "IK5:5" and p["owner"] == "billing"


def test_an_unknown_status_is_business_and_flagged_unrouted(book):
    c = add_claim(book, "U1")
    book.ack_277ca(c, "A3", ACK, code="21")
    go(book, seeded=False)
    (rec,) = records(book.engine)
    p = payload(rec)
    assert rec.action_type == "a6_rejection_task" and p["unrouted"] and p["category"] == "unrouted"
    assert rec.confidence == D("0.50")


def test_seeding_is_idempotent(tmp_path):
    engine = make_engine(tmp_path / "s.sqlite")
    assert seed(engine) == len(DEFAULT_ROUTES) and seed(engine) == 0


def test_another_tenants_routing_is_not_used(book):
    c = add_claim(book, "X1")
    book.ack_277ca(c, "A3", ACK, code="21")
    book.commit()
    seed(book.engine, tenant=2)  # tenant 2 has routes; tenant 1 has none
    replay(book.engine, 1, A6SubmissionAgent())
    assert payload(records(book.engine, 1)[0])["unrouted"] is True
    assert records(book.engine, 2) == []


# --------------------------------------------------------------------------------- causes and the packet


def test_likely_causes_come_from_the_prevention_rules(book):
    a = add_claim(book, "L1", dx=False, pointer="")
    b = add_claim(book, "L2", lines=(("97140", (), 1), ("97530", (), 1)), dos=date(2026, 5, 2))
    book.ack_277ca(a, "A3", ACK, code="21")
    book.ack_277ca(b, "A3", ACK, code="21")
    go(book)
    by_claim = {payload(r)["claims"][0]: payload(r) for r in records(book.engine)}
    assert {c["rule"] for c in by_claim["L1"]["likely_causes"]} == {"required_fields"}
    assert {c["rule"] for c in by_claim["L2"]["likely_causes"]} == {"ncci_pair"}


def test_the_packet_copies_the_claim_verbatim_and_changes_nothing(book):
    add_claim(book, "K1", lines=(("97140", ("59", "GP"), 2), ("97530", (), 1)), charge="90.00")
    book.ack_999("K1", "R", ACK, errors="IK5:5")
    go(book)
    (rec,) = records(book.engine)
    (pk,) = payload(rec)["packets"]
    assert pk["status"] == "draft_not_sent" and pk["edits"] == [] and pk["frequency_code"] == "1"
    assert [(ln["cpt"], ln["modifiers"], D(ln["units"]), ln["charge"]) for ln in pk["lines"]] == [
        ("97140", ["59", "GP"], D(2), "90.00"), ("97530", [], D(1), "90.00")
    ]  # fmt: skip
    assert pk["diagnoses"] == ["M5450", "G8929"] and pk["total_charge"] == "90.00"
    checks = {r["rule"]: r["result"] for r in json.loads(rec.rules_fired)}
    assert checks["packet_unchanged"] is True


def test_no_action_type_can_submit_write_off_or_change_a_code():
    assert all(a.endswith(("_task", "_review")) for a in ACTION_TYPES)
    assert not any(w in a for a in ACTION_TYPES for w in ("write_off", "refund", "adjust", "code"))
    assert not any(a.startswith("a6_submit") for a in ACTION_TYPES)
    assert NO_ACTION not in ACTION_TYPES


# ---------------------------------------------------------------------------- deadlines and priority


def test_filing_risk_raises_urgency_and_pulls_the_deadline_in(book):
    near = add_claim(book, "R1", dos=date(2025, 5, 20))  # limit 2026-05-20: 8 days left on 05-12
    far = add_claim(book, "R2", dos=date(2026, 5, 1))
    past = add_claim(book, "R3", dos=date(2025, 4, 1))  # limit already passed
    for c in (near, far, past):
        book.ack_277ca(c, "A3", ACK, code="21")
    go(book)
    p = {payload(r)["claims"][0]: payload(r) for r in records(book.engine)}
    assert p["R1"]["urgency"] == "2" and p["R2"]["urgency"] == "1"
    assert p["R1"]["card"]["deadline"] == "2026-05-15" and p["R1"]["filing_days_left"] == 8
    assert p["R3"]["filing_days_left"] < 0
    past_rec = next(r for r in records(book.engine) if payload(r)["claims"] == ["R3"])
    assert {x["rule"]: x["result"] for x in json.loads(past_rec.rules_fired)}["within_filing_limit"] is False


# ------------------------------------------------------------------------------------ engine guarantees


def test_shadow_never_reaches_an_adapter_and_a_rerun_creates_nothing(book):
    c = add_claim(book, "S1")
    book.ack_277ca(c, "A3", ACK, code="21")
    book.commit()
    seed(book.engine)
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalars(select(m.Event).where(m.Event.event_type == "277CA.claim_status")).one().id
    spy = SpyAdapter()
    res = run(book.engine, 1, A6SubmissionAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == []
    again = run(book.engine, 1, A6SubmissionAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert again.created is False and again.record_id == res.record_id and len(records(book.engine)) == 1


def test_replay_is_deterministic(book):
    a = add_claim(book, "D1")
    b = add_claim(book, "D2", dos=date(2026, 5, 2))
    book.ack_277ca(a, "A3", ACK, code="21")
    book.ack_277ca(b, "A4", ACK)
    first = go(book)
    second = replay(book.engine, 1, A6SubmissionAgent())
    assert [i.fingerprint for i in first] == [i.fingerprint for i in second] and len(first) == 2
    with tenant_session(book.engine, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.DecisionRecord)) == 2
        assert all(fingerprint(r) for r in s.scalars(select(m.DecisionRecord)))


def test_a_live_level_3_resubmission_waits_for_a_person_then_only_the_stub_records_it(book):
    add_claim(book, "V1")
    book.ack_999("V1", "R", ACK, errors="IK5:5")
    book.commit()
    seed(book.engine)
    with tenant_session(book.engine, 1) as s:
        set_policy(s, "a6_resubmit_review", mode="live", autonomy_level=3, approver_role="billing_manager")
        s.commit()
        event_id = s.scalars(select(m.Event).where(m.Event.event_type == "999.ack")).one().id
    stub = ClearinghouseStub()
    res = run(book.engine, 1, A6SubmissionAgent(), event_id, adapters={"a6_resubmit_review": stub})
    assert res.outcome == "pending_approval" and stub.requests == []
    assert list_requests(book.engine, 1)[0]["action_type"] == "a6_resubmit_review"
    approve(book.engine, 1, res.approval_id, "Pat", "billing_manager", adapters={"a6_resubmit_review": stub})
    assert len(stub.requests) == 1 and stub.requests[0][1]["packets"][0]["status"] == "draft_not_sent"
    assert records(book.engine)[0].execution_result == "stub: recorded, not sent"


def test_records_carry_no_patient_identifier(book):
    c = add_claim(book, "PHI1")
    book.ack_277ca(c, "A3", ACK, code="21")
    go(book)
    (rec,) = records(book.engine)
    text = (rec.input_snapshot + rec.action_payload).lower()
    assert "ref_hash" not in text and "patient" not in text and "member" not in text


# ------------------------------------------------------------------------------------ synthetic history


def test_replay_over_the_synthetic_history_gives_every_planted_rejection_a_decision(tmp_path, capsys):
    ms.generate(tmp_path / "data", seed=5, n_claims=200)
    engine = make_engine(tmp_path / "db.sqlite")
    ingest_path(engine, 1, tmp_path / "data", SALT)
    assert cli.main(["--db-url", str(engine.url), "a6", "seed", "--tenant", "1"]) == 0
    assert f"{len(DEFAULT_ROUTES)} routing rows added" in capsys.readouterr().out
    assert cli.main(["--db-url", str(engine.url), "a6", "replay", "--tenant", "1"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    summary = summarize(engine, 1)
    print("\n" + format_summary(summary))
    t = summary["totals"]
    assert t["records"] == 4 and t["claims"] == 4 and t["executed"] == 0 and t["unrouted"] == 0  # the 4 planted rejections
    assert {g["owner"] for g in summary["groups"]} == {"billing"} and t["amount"] == D("542.97")
    with tenant_session(engine, 1) as s:
        assert all(payload(r)["card"]["deadline"] for r in s.scalars(select(m.DecisionRecord)))
