"""M14 tests: the A1 pre-visit clearance agent in shadow mode, the 271 parser, the sweeper and the Synthea book."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

import krisnai.model as m
from krisnai import cli
from krisnai.agents.a1_clearance import (
    ACTION_TYPES,
    CHECK_TASK,
    COB_REVIEW,
    EVENT_TYPE,
    EXCEPTION_REVIEW,
    A1ClearanceAgent,
    Response,
    check,
    estimate,
    format_summary,
    latest,
    latest_by_appointment,
    summarize,
    sweep,
)
from krisnai.agents.a1_clearance import rules as r
from krisnai.engine import NO_ACTION, replay, run
from krisnai.engine.card import CARD_KEYS
from krisnai.ingest.eligibility import parse_271
from krisnai.ingest.loader import ingest_path, parse_appointments, parse_x12
from krisnai.ingest.x12 import X12Error, read_transactions
from krisnai.match.engine import run_matching
from krisnai.model import tenant_session
from krisnai.synthea import build
from krisnai.synthea.eligibility import write_271
from krisnai.synthea.types import PayerInfo, Person, SimClaim, SimLine
from tests.fixtures import synthea_mini
from tests.fixtures.dummy_agent import SpyAdapter
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

D = Decimal
VISIT = date(2026, 6, 20)


def resp(checked=date(2026, 6, 10), active=True, begin=None, end=None, other=None, copay=None, coins=None, ded=None):
    return Response(checked, active, begin, end, other, copay, coins, ded)


# ------------------------------------------------------------------------------------------- the rules


def gaps(response, as_of=date(2026, 6, 17)):
    return [g.kind for g in check(VISIT, response, as_of)]


def test_a_fresh_active_answer_clears_the_visit():
    assert gaps(resp()) == []


def test_no_answer_known_yet_is_no_eligibility_check():
    assert gaps(None) == [r.NO_CHECK]
    assert latest([resp(checked=date(2026, 6, 18))], date(2026, 6, 17)) is None  # produced after the checkpoint


def test_inactive_or_out_of_plan_dates_is_a_coverage_gap():
    assert gaps(resp(active=False)) == [r.INACTIVE]
    assert gaps(resp(end=date(2026, 6, 1))) == [r.INACTIVE]
    assert gaps(resp(begin=date(2026, 7, 1))) == [r.INACTIVE]
    assert gaps(resp(end=VISIT)) == []  # coverage through the visit day is fine


def test_another_primary_payer_is_a_cob_gap():
    assert gaps(resp(other="BLUE")) == [r.COB]


def test_an_old_answer_is_stale_and_the_gaps_are_worst_first():
    assert gaps(resp(checked=date(2026, 5, 20))) == [r.STALE]
    assert gaps(resp(checked=date(2026, 5, 20), active=False, other="X")) == [r.INACTIVE, r.COB, r.STALE]


def test_the_latest_known_answer_wins():
    older, newer = resp(checked=date(2026, 6, 1)), resp(checked=date(2026, 6, 12), active=False)
    assert latest([older, newer], date(2026, 6, 17)) is newer
    assert latest([older, newer], date(2026, 6, 10)) is older


def test_patient_estimate_arithmetic():
    allowed = D("100.00")
    assert estimate(D("25"), None, None, allowed) == D("25.00")  # copay only
    assert estimate(None, D("0.2"), None, allowed) == D("20.00")  # coinsurance only
    assert estimate(None, D("0.2"), D("50"), allowed) == D("60.00")  # deductible 50, then 20% of the other 50
    assert estimate(None, D("0.2"), D("500"), allowed) == D("100.00")  # deductible above the allowed amount
    assert estimate(D("25"), D("0.1"), D("0"), allowed) == D("35.00")  # copay plus coinsurance
    assert estimate(D("150"), None, None, allowed) == D("100.00")  # never more than allowed
    assert estimate(None, None, None, allowed) == D("0.00")


# ------------------------------------------------------------------------------------ the 271 parser


def make_271(answers, payer_id="P1", when=date(2026, 6, 10)):
    payer = PayerInfo(payer_id, "TEST PAYER", D("1.0"), 30)
    out = []
    for i, (active, other) in enumerate(answers, start=1):
        c = SimClaim(f"SYNC{i:06d}", payer, "1888888800", Person(f"M{i}", "LAST", "FIRST", date(1980, 1, 1), "F"),
                     VISIT, ["I10"], [SimLine("99213", 1, D("10"), D("10"))], when)  # fmt: skip
        out.append(_Answer(c, active, other))
    return write_271(payer, out, 1, when)


class _Answer:  # the simulator's answer shape, built by hand
    def __init__(self, claim, active, other):
        self.ref, self.claim, self.checked_on = f"AP{claim.claim_id[-3:]}", claim, date(2026, 6, 10)
        self.active, self.plan_end, self.other = active, None if active else date(2026, 5, 1), other


def test_271_parser_reads_active_inactive_and_other_payer_and_several_subscribers():
    text = make_271([(True, ""), (False, ""), (True, "SECOND PAYER")])
    (tx,) = read_transactions(text)
    recs = parse_271(tx, "salt")
    assert [x.active for x in recs] == [True, False, True]
    assert recs[1].plan_end == date(2026, 5, 1) and recs[2].other_payer == "SECOND PAYER"
    assert recs[0].coinsurance == D("0.10") and recs[0].deductible_remaining == D("0")
    assert recs[0].payer_code == "P1" and recs[0].service_date == VISIT and recs[0].checked_on == date(2026, 6, 10)
    assert recs[0].patient_hash is not None and recs[0].response_ref.startswith("TRC")
    assert parse_x12(text, "salt")[0] == "271"


def test_a_271_without_a_subscriber_or_coverage_line_is_rejected():
    (tx,) = read_transactions(make_271([(True, "")]))
    tx.segments[:] = [s for s in tx.segments if s.id != "EB"]
    with pytest.raises(X12Error):
        parse_271(tx, "salt")
    (tx2,) = read_transactions(make_271([(True, "")]))
    tx2.segments[:] = [s for s in tx2.segments if s.id != "HL" or s[3] != "22"]
    with pytest.raises(X12Error):
        parse_271(tx2, "salt")


def test_appointment_parser_reads_columns_hashes_the_member_and_rejects_bad_input():
    rows = parse_appointments(
        "appointment_id,payer_id,provider_npi,patient_ref,appt_date,booked_on,cpt\nA1,P1,1999999991,M1,2026-06-20,2026-06-01,99213\n",
        "salt",
    )
    assert rows[0]["appt"] == VISIT and rows[0]["status"] == "booked" and len(rows[0]["patient"]) == 32
    with pytest.raises(X12Error):
        parse_appointments("appointment_id,payer_id\nA1,P1\n", "salt")
    with pytest.raises(X12Error):
        parse_appointments(
            "appointment_id,payer_id,provider_npi,patient_ref,appt_date,booked_on,cpt\nA1,P1,1,M1,nope,2026-06-01,99213\n",
            "salt",
        )


# ------------------------------------------------------------------------------- the sweeper + agent


@pytest.fixture()
def book(tmp_path):
    engine = make_engine(tmp_path / "b.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "100.00")
    return b


def records(engine, tenant=1):
    with tenant_session(engine, tenant) as s:
        return list(s.scalars(select(m.DecisionRecord).where(m.DecisionRecord.agent_id == "a1_clearance")))


def go(b, start=date(2026, 6, 1), end=date(2026, 6, 30)):
    b.commit()
    sweep(b.engine, 1, start, end)
    return replay(b.engine, 1, A1ClearanceAgent())


def by_checkpoint(engine):
    out = {}
    for rec in records(engine):
        p = json.loads(rec.action_payload)
        out[(p["appt"], p.get("checkpoint_days"))] = rec
    return out


def test_sweeper_raises_both_checkpoints_inside_the_window_and_a_rerun_adds_nothing(book):
    book.appointment("A1", "P1", VISIT, date(2026, 6, 1))
    book.commit()
    first = sweep(book.engine, 1, date(2026, 6, 1), date(2026, 6, 30))
    assert first.events == 2 and not first.skipped
    assert sweep(book.engine, 1, date(2026, 6, 1), date(2026, 6, 30)).skipped
    only_late = sweep(book.engine, 1, date(2026, 6, 19), date(2026, 6, 19))  # only the 1-day checkpoint is in range
    assert only_late.events == 1
    with tenant_session(book.engine, 1) as s:
        days = sorted(json.loads(p)["due_on"] for p in s.scalars(
            select(m.Event.payload).where(m.Event.event_type == EVENT_TYPE)))  # fmt: skip
    assert days == ["2026-06-17", "2026-06-19", "2026-06-19"]


def test_a_visit_booked_after_a_checkpoint_has_no_checkpoint_that_day(book):
    book.appointment("A1", "P1", VISIT, booked=date(2026, 6, 18))  # booked 2 days out: the 3-day point already passed
    book.commit()
    assert sweep(book.engine, 1, date(2026, 6, 1), date(2026, 6, 30)).events == 1


def test_a_cleared_visit_is_no_action_with_a_patient_estimate(book):
    book.appointment("A1", "P1", VISIT, date(2026, 6, 5))
    book.eligibility("E1", "P1", date(2026, 6, 5), VISIT, coinsurance="0.2", deductible="0")
    go(book)
    recs = by_checkpoint(book.engine)
    assert {x.action_type for x in recs.values()} == {NO_ACTION}
    p = json.loads(recs[("A1", 1)].action_payload)
    assert p["cleared"] and p["patient_estimate"] == "20.00"  # 100.00 fee x 20%


def patient(b, n):
    return b._add(m.PatientRef(ref_hash=bytes([n]) * 32))


def test_each_gap_goes_to_its_own_action_for_the_front_desk(book):
    for n, ref in enumerate(("NONE", "LAPSED", "COB", "STALE", "CLEAR"), start=10):
        book.appointment(ref, "P1", VISIT, date(2026, 6, 5), patient=patient(book, n))
    p = {ref: patient_of(book, ref) for ref in ("LAPSED", "COB", "STALE", "CLEAR")}
    book.eligibility("E2", "P1", date(2026, 6, 5), VISIT, active=False, patient=p["LAPSED"])
    book.eligibility("E3", "P1", date(2026, 6, 5), VISIT, other="SECOND PAYER", patient=p["COB"])
    book.eligibility("E4", "P1", date(2026, 5, 1), VISIT, patient=p["STALE"])
    book.eligibility("E5", "P1", date(2026, 6, 5), VISIT, patient=p["CLEAR"])
    go(book)
    got = {}
    for rec in records(book.engine):
        got[json.loads(rec.action_payload)["appt"]] = rec.action_type
    assert got == {"NONE": CHECK_TASK, "LAPSED": EXCEPTION_REVIEW, "COB": COB_REVIEW, "STALE": CHECK_TASK,
                   "CLEAR": NO_ACTION}  # fmt: skip


def patient_of(b, ref):
    return b.s.get(m.PatientRef, b.s.scalars(select(m.Appointment.patient_ref_id).where(
        m.Appointment.appt_ref == ref)).one())  # fmt: skip


def test_gaps_are_matched_to_the_appointment_date_of_service_not_the_patient(tmp_path):
    engine = make_engine(tmp_path / "svc.sqlite")
    b = Book(engine, 1)
    b.engine = engine
    b.fee("P1", "99213", "100.00")
    other_day = VISIT + timedelta(days=7)
    b.appointment("A1", "P1", VISIT, date(2026, 6, 5))
    b.appointment("A2", "P1", other_day, date(2026, 6, 5))
    b.eligibility("E1", "P1", date(2026, 6, 5), VISIT, active=False)  # asked about the first visit only
    go(b)
    got = {}
    for rec in records(engine):
        p = json.loads(rec.action_payload)
        got.setdefault(p["appt"], set()).add(rec.action_type)
    assert got["A1"] == {EXCEPTION_REVIEW}
    assert got["A2"] == {CHECK_TASK}  # the answer for another date does not clear this visit


def test_shadow_mode_nothing_runs_a_rerun_creates_nothing_and_cards_have_the_standard_shape(book):
    book.appointment("A1", "P1", VISIT, date(2026, 6, 5))
    book.commit()
    sweep(book.engine, 1, date(2026, 6, 17), date(2026, 6, 17))
    with tenant_session(book.engine, 1) as s:
        event_id = s.scalar(select(m.Event.id).where(m.Event.event_type == EVENT_TYPE))
    spy = SpyAdapter()
    res = run(book.engine, 1, A1ClearanceAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    again = run(book.engine, 1, A1ClearanceAgent(), event_id, adapters={a: spy for a in ACTION_TYPES})
    assert res.outcome == "shadow" and spy.calls == [] and again.created is False
    (rec,) = records(book.engine)
    assert set(json.loads(rec.action_payload)["card"]) == set(CARD_KEYS)
    assert rec.action_type == CHECK_TASK
    assert all(a.endswith(("_task", "_review")) for a in ACTION_TYPES)


def test_replay_is_deterministic_and_tenants_are_isolated(tmp_path):
    def once(name):
        engine = make_engine(tmp_path / name)
        b = Book(engine, 1)
        b.engine = engine
        b.fee("P1", "99213", "100.00")
        b.appointment("A1", "P1", VISIT, date(2026, 6, 5))
        b.eligibility("E1", "P1", date(2026, 6, 5), VISIT, active=False)
        go(b)
        return engine, [(i.outcome, i.fingerprint) for i in replay(engine, 1, A1ClearanceAgent())]

    (e1, a), (_, b_) = once("a.sqlite"), once("b.sqlite")
    assert a == b_
    assert records(e1, 2) == []


# ------------------------------------------------------------------------------------- Synthea book


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a1")
    raw = synthea_mini.write(root / "raw", n_claims=900, n_patients=120, seed=5)
    build(raw, root / "book", date(2026, 6, 30), seed=7, documentation=True, eligibility=True)
    engine = make_engine(root / "db.sqlite")
    results = ingest_path(engine, 1, root / "book", SALT)
    run_matching(engine, 1)
    sweep(engine, 1, date(2025, 3, 1), date(2026, 6, 30))
    replay(engine, 1, A1ClearanceAgent())
    truth = defaultdict(set)
    for t in csv.DictReader((root / "book" / "elig_truth.csv").open()):
        truth[t["defect"]].add(t["appointment_id"])
    return {"root": root, "engine": engine, "truth": truth, "results": results}


def test_appointments_and_271s_load_idempotently(syn):
    assert all(x.status == "loaded" for x in syn["results"])
    assert {"271", "appointments"} <= {x.file_type for x in syn["results"]}
    again = ingest_path(syn["engine"], 1, syn["root"] / "book", SALT)
    assert all(x.status == "skipped" for x in again)


def test_every_planted_coverage_problem_is_found_and_nothing_else(syn):
    final = latest_by_appointment(syn["engine"], 1)
    pairs = {"coverage_inactive": r.INACTIVE, "cob_other_payer": r.COB, "no_check": r.NO_CHECK, "stale_check": r.STALE}
    for defect, kind in pairs.items():
        found = {a for a, v in final.items() if kind in v["gaps"]}
        assert len(syn["truth"][defect]) > 3
        assert found == syn["truth"][defect], defect


def test_every_coverage_denial_was_flagged_before_the_visit(syn):
    truth = list(csv.DictReader((syn["root"] / "book" / "ground_truth.csv").open()))
    denied = {t["claim_id"] for t in truth if t["issue_type"] == "denial" and t["carc"] in ("27", "31")}
    appt_of = {t["claim_id"]: t["appointment_id"]
               for t in csv.DictReader((syn["root"] / "book" / "elig_truth.csv").open())}  # fmt: skip
    final = latest_by_appointment(syn["engine"], 1)
    assert denied and all(appt_of[c] in final and r.INACTIVE in final[appt_of[c]]["gaps"] for c in denied)


def test_clearance_rate_and_summary(syn):
    s = summarize(syn["engine"], 1)
    planted = sum(len(v) for v in syn["truth"].values())
    assert s["appointments"] > planted and s["appointments"] - s["cleared"] == planted
    assert s["by_action"].get(EXCEPTION_REVIEW) == len(syn["truth"]["coverage_inactive"])
    assert "cleared" in format_summary(s)


def test_patient_estimate_equals_what_the_patient_owed_on_clean_paid_claims(syn):
    final = latest_by_appointment(syn["engine"], 1)
    with tenant_session(syn["engine"], 1) as s:
        rows = s.execute(
            select(m.Remit.claim_submitter_id, m.Remit.patient_responsibility, m.Remit.total_paid)
            .where(m.Remit.claim_status_code == "1")
        ).all()
        n_lines = {
            sid: n for sid, n in s.execute(
                select(m.Claim.claim_submitter_id, m.ClaimLine.line_number).join(
                    m.ClaimLine, m.ClaimLine.claim_id == m.Claim.id).where(m.ClaimLine.line_number == 2))  # fmt: skip
        }
    single = {sid: pr for sid, pr, paid in rows if sid not in n_lines and paid > 0}
    checked = 0
    for sid, pr in single.items():
        ref = f"SYNAP{sid[-6:]}"
        est = final.get(ref, {}).get("patient_estimate")
        if est is not None and not final[ref]["gaps"]:
            assert D(est) == pr, sid
            checked += 1
    assert checked > 50


def test_the_tower_shows_a1_cards_until_the_visit_date_passes(syn):
    from krisnai.agents.a14_tower.cards import open_cards

    with tenant_session(syn["engine"], 1) as s:  # a day on which at least one gap was raised
        day = s.scalars(
            select(m.Event.known_at)
            .join(m.DecisionRecord, m.DecisionRecord.event_id == m.Event.id)
            .where(m.DecisionRecord.agent_id == "a1_clearance", m.DecisionRecord.action_type != NO_ACTION)
            .order_by(m.Event.known_at)
        ).first().date()
    cards = [c for c in open_cards(syn["engine"], 1, day) if c["agent"] == "a1_clearance"]
    assert cards and all(date.fromisoformat(c["deadline"]) >= day for c in cards)
    assert not [c for c in open_cards(syn["engine"], 1, date(2026, 6, 30)) if c["agent"] == "a1_clearance"
                and date.fromisoformat(c["deadline"]) < date(2026, 6, 30)]  # fmt: skip


def test_cli_a1_replays_in_shadow_and_default_output_is_unchanged(syn, tmp_path, capsys):
    url = str(syn["engine"].url)
    assert cli.main(["--db-url", url, "a1", "replay", "--tenant", "1"]) == 0
    assert "shadow: nothing executed" in capsys.readouterr().out
    raw = syn["root"] / "raw"
    a, b = tmp_path / "plain", tmp_path / "plain2"
    build(raw, a, date(2026, 6, 30), seed=7)
    build(raw, b, date(2026, 6, 30), seed=7, eligibility=False)
    assert not (a / "appointments.csv").exists()
    digest = lambda d: {p.name: hashlib.md5(p.read_bytes()).hexdigest() for p in sorted(d.iterdir())}  # noqa: E731
    assert digest(a) == digest(b)
