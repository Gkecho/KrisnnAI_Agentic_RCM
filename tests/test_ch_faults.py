"""Failure injection for the clearinghouse bots: timeouts, 5xx, 401, garbage, truncated and mismatched replies, outages.

The bots must keep going or stop as designed, never raise out of the batch, never keep another subject's reply, never
send the same replacement twice, and never write identifiers or bodies to the log. A small hand-built book is used so
the file runs in seconds; the real-HTTP happy path is covered by test_ch_integration.py and test_stage1.py.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from krisnai.integrations.clearinghouse import bots
from krisnai.integrations.clearinghouse.bots import eligibility_bot, resubmission_bot, status_bot
from krisnai.integrations.clearinghouse.claim_store import Adjudication, PmExtract, StoredClaim, StoredLine
from krisnai.integrations.clearinghouse.client import ClearinghouseClient
from krisnai.integrations.clearinghouse.faults import FaultyClient
from krisnai.integrations.clearinghouse.mock_server import create_app
from krisnai.integrations.clearinghouse.mock_world import MockWorld

WHEN = date(2026, 6, 30)
TOKEN = "test-token-not-secret"
N = 6
PAID = [f"C{i}" for i in range(1, N + 1)]  # status bot subjects
REJ = [f"R{i}" for i in range(1, 5)]  # resubmission bot subjects
APPT = [f"A{i}" for i in range(1, N + 1)]  # eligibility bot subjects


def _claim(cid: str) -> StoredClaim:
    return StoredClaim(cid, "PAYER1", "PAYER ONE", "MEMBER000" + cid, "LAST", "FIRST", "19700101", "F", Decimal("100"),
                       date(2026, 5, 4), ["Z00"], "1888888800", [StoredLine("99213", Decimal("100"), "1")])  # fmt: skip


@pytest.fixture()
def book(monkeypatch):
    ex = PmExtract()
    for cid in PAID + REJ:
        ex.claims[cid] = _claim(cid)
    for cid in PAID:
        ex.answers[cid] = Adjudication("paid", "1", Decimal("80"), "PCN" + cid)
    for cid in REJ:
        ex.answers[cid] = Adjudication("rejected", "21", Decimal(0), "PCN" + cid)
    for appt, cid in zip(APPT, PAID):
        ex.appointments[appt] = {"appointment_id": appt, "payer_id": "PAYER1", "patient_ref": "MEMBER000" + cid,
                                 "appt_date": (WHEN + timedelta(days=3)).isoformat(), "booked_on": "2026-06-01"}  # fmt: skip
    world = MockWorld(ex, today=WHEN)
    inner = ClearinghouseClient("http://testserver", TOKEN, http=TestClient(create_app(world, token=TOKEN, today=WHEN)))
    todo = {"a1_clearance": APPT, "a7_ar": PAID, "a6_submission": REJ}
    monkeypatch.setattr(bots, "latest_decisions",
                        lambda engine, tenant, agent, key: {k: ("act", {}) for k in todo[agent]})  # fmt: skip
    return ex, world, inner


def run(kind: str, ex, client, out, **kw):
    fn = {"eligibility": eligibility_bot, "status": status_bot, "resubmission": resubmission_bot}[kind]
    return fn(None, 1, ex, client, out, WHEN, log_path=out.parent / "bot_log.jsonl", **kw)


def outcomes(rep) -> list[str]:
    return [e.outcome for e in rep.events]


def files(out) -> set[str]:
    return {p.name for p in out.iterdir() if p.suffix == ".x12"} if out.exists() else set()


# ------------------------------------------------------------------------------------------------- happy path


def test_without_faults_everything_is_done_once(book, tmp_path):
    ex, world, inner = book
    assert outcomes(run("eligibility", ex, inner, tmp_path / "o")) == ["active"] * N
    assert outcomes(run("status", ex, inner, tmp_path / "o")) == ["paid"] * N
    assert outcomes(run("resubmission", ex, inner, tmp_path / "o")) == ["accepted"] * len(REJ)
    assert all(world.received_corrected[c] == 1 for c in REJ)


# --------------------------------------------------------------------------------------- read-only bots


@pytest.mark.parametrize("kind,ok", [("eligibility", "active"), ("status", "paid")])
@pytest.mark.parametrize("fault", ["timeout", "connection_error", "http_5xx"])
def test_a_transient_fault_is_retried_and_the_batch_completes(book, tmp_path, kind, ok, fault):
    ex, _, inner = book
    fc = FaultyClient(inner, {1: fault})
    assert outcomes(run(kind, ex, fc, tmp_path / "o")) == [ok] * N
    assert fc.calls == N + 1  # exactly one retry


@pytest.mark.parametrize("kind,ok", [("eligibility", "active"), ("status", "paid")])
def test_a_permanent_fault_is_not_retried_and_the_rest_continues(book, tmp_path, kind, ok):
    ex, _, inner = book
    fc = FaultyClient(inner, {1: "http_400"})
    assert outcomes(run(kind, ex, fc, tmp_path / "o")) == ["error"] + [ok] * (N - 1)
    assert fc.calls == N  # no retry on a 4xx


@pytest.mark.parametrize("kind", ["eligibility", "status"])
def test_a_rejected_credential_stops_the_batch_at_once(book, tmp_path, kind):
    ex, _, inner = book
    fc = FaultyClient(inner, {1: "http_401"})
    rep = run(kind, ex, fc, tmp_path / "o")
    assert outcomes(rep) == ["error"] + ["not_attempted"] * (N - 1)
    assert fc.calls == 1 and "credential rejected" in rep.events[-1].detail
    assert files(tmp_path / "o") == set()


@pytest.mark.parametrize("kind,ok", [("eligibility", "active"), ("status", "paid")])
@pytest.mark.parametrize("fault", ["garbage", "truncated"])
def test_a_damaged_reply_is_not_kept(book, tmp_path, kind, ok, fault):
    ex, _, inner = book
    rep = run(kind, ex, FaultyClient(inner, {1: fault}), tmp_path / "o")
    assert outcomes(rep) == ["bad_response"] + [ok] * (N - 1)
    assert len(files(tmp_path / "o")) == N - 1


@pytest.mark.parametrize("kind,ok", [("eligibility", "active"), ("status", "paid")])
def test_a_reply_for_another_subject_is_refused_and_never_reaches_the_inbox(book, tmp_path, kind, ok):
    ex, _, inner = book
    rep = run(kind, ex, FaultyClient(inner, {2: "wrong_subject"}), tmp_path / "o")
    assert outcomes(rep) == [ok, "bad_response"] + [ok] * (N - 2)
    subject2 = rep.events[1].subject
    assert not any(subject2 in name for name in files(tmp_path / "o"))
    assert len(files(tmp_path / "o")) == N - 1


@pytest.mark.parametrize("kind,ok", [("eligibility", "active"), ("status", "paid")])
def test_an_outage_opens_the_breaker_and_the_remaining_subjects_are_left_alone(book, tmp_path, kind, ok):
    ex, _, inner = book
    fc = FaultyClient(inner, outage_after=2)
    rep = run(kind, ex, fc, tmp_path / "o")
    assert outcomes(rep) == [ok, ok, "error", "error", "error", "not_attempted"]
    assert "3 failures in a row" in rep.events[-1].detail
    assert len(files(tmp_path / "o")) == 2
    assert fc.calls == 2 + 3 * 3  # two good calls, then three subjects with three attempts each; the sixth is never tried


def test_a_second_run_gives_the_same_files_not_more(book, tmp_path):
    ex, _, inner = book
    out = tmp_path / "o"
    run("eligibility", ex, inner, out)
    first = files(out)
    run("eligibility", ex, inner, out)
    assert files(out) == first


# --------------------------------------------------------------------------------------- resubmission bot


def test_a_lost_reply_after_a_send_is_never_resent(book, tmp_path):
    ex, world, inner = book
    out = tmp_path / "o"
    fc = FaultyClient(inner, {1: "timeout_after_send"})
    rep = run("resubmission", ex, fc, out)
    assert outcomes(rep) == ["unknown_sent"] + ["accepted"] * (len(REJ) - 1)
    first = rep.events[0].subject
    assert world.received_corrected[first] == 1  # the clearinghouse did process it
    again = run("resubmission", ex, FaultyClient(inner), out)
    assert set(outcomes(again)) == {"skipped"} and "already sent once" in again.events[0].detail
    assert all(world.received_corrected[c] == 1 for c in REJ)


@pytest.mark.parametrize("fault", ["timeout", "http_5xx"])
def test_a_timeout_or_5xx_on_a_send_is_not_retried_and_waits_for_a_status_check(book, tmp_path, fault):
    ex, world, inner = book
    fc = FaultyClient(inner, {1: fault})
    rep = run("resubmission", ex, fc, tmp_path / "o")
    assert outcomes(rep) == ["unknown_sent"] + ["accepted"] * (len(REJ) - 1)
    assert fc.calls == len(REJ)  # no retry of a send whose fate is unknown
    assert world.received_corrected.get(rep.events[0].subject, 0) == 0


def test_a_connection_error_is_retried_because_the_request_never_left(book, tmp_path):
    ex, world, inner = book
    fc = FaultyClient(inner, {1: "connection_error"})
    assert outcomes(run("resubmission", ex, fc, tmp_path / "o")) == ["accepted"] * len(REJ)
    assert fc.calls == len(REJ) + 1 and all(world.received_corrected[c] == 1 for c in REJ)


def test_a_rejected_credential_stops_resubmission_and_a_later_run_may_try_again(book, tmp_path):
    ex, world, inner = book
    out = tmp_path / "o"
    rep = run("resubmission", ex, FaultyClient(inner, {1: "http_401"}), out)
    assert outcomes(rep) == ["error"] + ["not_attempted"] * (len(REJ) - 1)
    assert world.received_corrected == {}
    assert outcomes(run("resubmission", ex, inner, out)) == ["accepted"] * len(REJ)  # 401 means it was not processed


@pytest.mark.parametrize("fault", ["garbage", "truncated"])
def test_a_damaged_answer_to_a_send_is_not_resent(book, tmp_path, fault):
    ex, world, inner = book
    out = tmp_path / "o"
    rep = run("resubmission", ex, FaultyClient(inner, {1: fault}), out)
    assert outcomes(rep)[0] == "bad_response"
    assert outcomes(run("resubmission", ex, inner, out))[0] == "skipped"
    assert world.received_corrected.get(rep.events[0].subject, 0) <= 1


def test_an_answer_for_another_claim_is_not_trusted(book, tmp_path):
    ex, world, inner = book
    rep = run("resubmission", ex, FaultyClient(inner, {2: "wrong_subject"}), tmp_path / "o")
    assert outcomes(rep)[:2] == ["accepted", "bad_response"]
    assert "does not cover this claim" in rep.events[1].detail


def test_a_replacement_the_payer_refuses_is_recorded_and_not_sent_again(book, tmp_path):
    ex, world, inner = book
    out = tmp_path / "o"
    ex.answers["R1"] = Adjudication("paid", "1", Decimal("80"), "PCNR1")  # no longer rejected: the bot skips it
    rep = run("resubmission", ex, inner, out)
    assert rep.events[0].outcome == "skipped" and "not currently rejected" in rep.events[0].detail


# ------------------------------------------------------------------------------------------------ hygiene


def test_the_log_holds_no_full_member_id_token_or_reply_body(book, tmp_path):
    ex, _, inner = book
    out = tmp_path / "o"
    fc = FaultyClient(inner, {1: "garbage", 2: "http_5xx", 3: "truncated", 6: "timeout_after_send"})
    for kind in ("eligibility", "status", "resubmission"):
        run(kind, ex, fc, out)
    text = (tmp_path / "bot_log.jsonl").read_text(encoding="utf-8")
    assert text.strip()
    for forbidden in ("MEMBER000", TOKEN, "Bad Gateway", "ISA*"):
        assert forbidden not in text
    for line in text.splitlines():
        assert json.loads(line)["bot"]


def test_unknown_faults_are_rejected_at_construction(book):
    _, _, inner = book
    with pytest.raises(ValueError):
        FaultyClient(inner, {1: "gremlins"})
