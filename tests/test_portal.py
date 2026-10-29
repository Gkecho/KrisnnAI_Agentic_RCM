"""Stage 1, portal bots: login, read, evidence, stop on a changed screen, rate limits, no credentials in the output."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from krisnnai.integrations.clearinghouse.claim_store import Adjudication, PmExtract, StoredClaim, StoredLine
from krisnnai.integrations.clearinghouse.client import EndpointRefused
from krisnnai.integrations.clearinghouse.mock_world import MockWorld
from krisnnai.integrations.portal.bots import claim_status_bot, credentials_from_env
from krisnnai.integrations.portal.driver import HttpDriver
from krisnnai.integrations.portal.mock_portal import create_app

USER, PASSWORD = "bot-user", "s3cret-pass-xyz"


def _claim(cid: str) -> StoredClaim:
    return StoredClaim(cid, "PAYER1", "PAYER ONE", "M" + cid, "LAST", "FIRST", "19700101", "F", Decimal("100"),
                       date(2026, 5, 4), ["Z00"], "1888888800", [StoredLine("99213", Decimal("100"), "1")])  # fmt: skip


def _records_claim() -> str:
    for i in range(500):
        cid = f"PEND{i}"
        if int(hashlib.sha256(cid.encode()).hexdigest(), 16) % 3 == 0:
            return cid
    raise AssertionError("unreachable")


@pytest.fixture()
def world():
    pend = _records_claim()
    ex = PmExtract()
    for cid in ("REJ1", "PAID1", "DEN1", pend, "NEW1"):
        ex.claims[cid] = _claim(cid)
    ex.answers["REJ1"] = Adjudication("rejected", "21", Decimal(0), "PCN-REJ")
    ex.answers["PAID1"] = Adjudication("paid", "1", Decimal("80"), "PCN-PAID")
    ex.answers["DEN1"] = Adjudication("denied", "4", Decimal(0), "PCN-DEN")
    ex.answers[pend] = Adjudication("paid", "1", Decimal(0), "")  # replaced below: pending means no answer
    del ex.answers[pend]
    w = MockWorld(ex)
    w.pend = pend
    return w


def driver_for(world, **kw):
    app = create_app(world, USER, PASSWORD, **kw)
    return HttpDriver("http://testserver", TestClient(app)), app


def test_it_reads_status_reason_and_amount_and_keeps_the_page_as_evidence(world, tmp_path):
    d, _ = driver_for(world)
    res = claim_status_bot(d, USER, PASSWORD, ["REJ1", "PAID1", "DEN1", "NEW1"], tmp_path / "ev",
                           log_path=tmp_path / "log.jsonl")  # fmt: skip
    by = {r.claim: r for r in res}
    assert by["REJ1"].status.startswith("Returned") and "resubmit" in by["REJ1"].reason
    assert by["PAID1"].status == "Finalized: paid" and by["PAID1"].paid == "80.00"
    assert by["DEN1"].status == "Finalized: denied"
    assert all(r.outcome == "read" for r in res)
    assert (tmp_path / "ev" / "REJ1_detail.html").read_text().count("Claim REJ1") >= 1
    log = (tmp_path / "log.jsonl").read_text()
    assert len(log.splitlines()) == 4 and PASSWORD not in log and USER not in log


def test_an_unknown_claim_is_not_found_and_a_records_request_is_read(world, tmp_path):
    d, _ = driver_for(world)
    res = {r.claim: r for r in claim_status_bot(d, USER, PASSWORD, ["NOPE", world.pend], tmp_path)}
    assert res["NOPE"].outcome == "not_found"
    r = res[world.pend]
    assert r.outcome == "read" and r.records_requested is True and len(r.evidence) == 2
    assert PASSWORD not in "".join(p.read_text() for p in tmp_path.iterdir())


def test_a_wrong_password_stops_at_sign_in_and_nothing_else_is_tried(world, tmp_path):
    d, app = driver_for(world)
    res = claim_status_bot(d, USER, "wrong", ["REJ1", "PAID1"], tmp_path)
    assert [r.outcome for r in res] == ["login_failed", "not_attempted"]
    assert not app.state.sessions


def test_a_changed_screen_stops_the_run_and_no_further_page_is_requested(world, tmp_path):
    d, app = driver_for(world, layout=2)
    res = claim_status_bot(d, USER, PASSWORD, ["REJ1", "PAID1", "DEN1"], tmp_path)
    assert [r.outcome for r in res] == ["screen_changed", "not_attempted", "not_attempted"]
    assert "claim-status" in res[0].detail
    seen = d.requests
    assert seen == 4  # login form, sign in, search, detail: nothing after the mismatch
    assert not list(tmp_path.glob("*_detail.html"))  # a page the bot did not understand is not kept as a result


def test_the_rate_limit_is_respected_by_stopping(world, tmp_path):
    d, _ = driver_for(world, max_per_minute=4)
    res = claim_status_bot(d, USER, PASSWORD, ["REJ1", "PAID1", "DEN1", "NEW1"], tmp_path)
    assert "rate_limited" in {r.outcome for r in res}
    stop = next(i for i, r in enumerate(res) if r.outcome == "rate_limited")
    assert all(r.outcome == "not_attempted" for r in res[stop + 1:])


def test_credentials_must_come_from_the_environment_and_real_portals_are_refused(monkeypatch):
    monkeypatch.delenv("P_USER", raising=False)
    with pytest.raises(SystemExit):
        credentials_from_env("P_USER", "P_PASS")
    monkeypatch.setenv("P_USER", "u")
    monkeypatch.setenv("P_PASS", "p")
    assert credentials_from_env("P_USER", "P_PASS") == ("u", "p")
    with pytest.raises(EndpointRefused):
        HttpDriver("https://portal.example-payer.com")
    with pytest.raises(ValueError):
        create_app(MockWorld(PmExtract()), "", "")
