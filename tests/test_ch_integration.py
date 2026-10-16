"""Stage 1, clearinghouse: X12 builders and parsers, the mock service, the client guard, and bots end to end."""

from __future__ import annotations

import json
import shutil
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from krisnai.ingest.eligibility import parse_271
from krisnai.ingest.loader import parse_x12
from krisnai.ingest.x12 import read_transactions
from krisnai.integrations.clearinghouse.bots import (
    eligibility_bot,
    latest_decisions,
    mask,
    resubmission_bot,
    status_bot,
)
from krisnai.integrations.clearinghouse.claim_store import load_extract
from krisnai.integrations.clearinghouse.client import ALLOW_ENV, ClearinghouseClient, EndpointRefused
from krisnai.integrations.clearinghouse.mock_server import create_app
from krisnai.integrations.clearinghouse.mock_world import MockWorld, parse_inbound_270, parse_inbound_276
from krisnai.integrations.clearinghouse.scenario import pick_bot_day
from krisnai.integrations.clearinghouse.x12_out import (
    parse_277_status,
    write_270,
    write_276,
    write_corrected_837,
)
from krisnai.ops import run_period
from krisnai.synthea import build
from tests.fixtures import synthea_mini
from tests.test_ingest import SALT, make_engine

AS_OF = date(2026, 6, 30)
TOKEN = "test-token"


@pytest.fixture(scope="module")
def book(tmp_path_factory):
    root = tmp_path_factory.mktemp("ch_book")
    raw = synthea_mini.write(root / "raw", n_claims=320, n_patients=45, seed=5)
    build(raw, root / "book", AS_OF, seed=7, documentation=True, eligibility=True)
    return root / "book"


@pytest.fixture(scope="module")
def extract(book):
    return load_extract(book)


def make_client(extract, book, today=AS_OF):
    world = MockWorld(extract, truth_dir=book, today=today)
    app = create_app(world, token=TOKEN, today=today)
    http = TestClient(app)
    return ClearinghouseClient("http://testserver", TOKEN, http=http), app, world


# ------------------------------------------------------------------------------------- builders and parsers


def test_the_practice_extract_holds_claims_appointments_and_answers(extract):
    assert len(extract.claims) > 100 and len(extract.appointments) > 100
    c = next(iter(extract.claims.values()))
    assert c.member_id and c.payer_id and c.lines and c.dos and c.billed > 0
    states = {a.state for a in extract.answers.values()}
    assert {"paid", "denied"} <= states


def test_270_276_and_the_corrected_837_are_valid_x12_the_existing_parsers_read(extract):
    c = next(iter(extract.claims.values()))
    t270 = write_270(c.payer_id, c.payer_name, c.member_id, c.last, c.first, c.dob, c.dos, "REF1", 1, AS_OF)
    sub = parse_inbound_270(t270)[0]
    assert (sub["payer_id"], sub["member"], sub["dos"], sub["ref"]) == (c.payer_id, c.member_id, c.dos, "REF1")
    t276 = write_276(c, "PCN1", "REF2", 2, AS_OF)
    s276 = parse_inbound_276(t276)[0]
    assert (s276["claim"], s276["member"], s276["payer_claim_no"]) == (c.claim_id, c.member_id, "PCN1")
    t837 = write_corrected_837(c, "PCN1", 3, AS_OF)
    kind, parsed = parse_x12(t837, SALT)
    assert kind == "837P"
    rec = parsed[0][2][0]
    assert rec.claim_submitter_id == c.claim_id and rec.frequency_code == "7"
    assert abs(sum(ln.charge for ln in rec.lines) - c.billed) < 0.01 or rec.total_charge == c.billed


# ------------------------------------------------------------------------------------------- the service


def test_the_service_needs_the_token_and_answers_from_the_answer_key(extract, book):
    client, app, world = make_client(extract, book)
    bad = TestClient(app).post("/v1/eligibility", content="x", headers={"Authorization": "Bearer nope"})
    assert bad.status_code == 401
    assert client.health()["claims"] == len(extract.claims)
    by_defect = {}
    for appt_id, defect in world.appt_defect.items():
        by_defect.setdefault(defect, appt_id)
    kinds = {}
    for defect, appt_id in by_defect.items():
        a = extract.appointments[appt_id]
        claim = next(c for c in extract.claims.values() if c.member_id == a["patient_ref"] and c.payer_id == a["payer_id"])
        req = write_270(a["payer_id"], claim.payer_name, a["patient_ref"], claim.last, claim.first, claim.dob,
                        date.fromisoformat(a["appt_date"]), "R" + appt_id, 5, AS_OF)  # fmt: skip
        rec = parse_271(read_transactions(client.check_eligibility(req))[0], "s")[0]
        kinds[defect] = (rec.active, bool(rec.other_payer))
    assert kinds["coverage_inactive"] == (False, False)
    assert kinds["cob_other_payer"] == (True, True)
    assert kinds.get("no_check", (True, False)) == (True, False)


def test_status_follows_the_files_and_a_replacement_is_only_taken_for_a_returned_claim(extract, book):
    client, _, world = make_client(extract, book)
    pick = {}
    for cid, ans in extract.answers.items():
        pick.setdefault(ans.state, cid)
    for state, cid in pick.items():
        c = extract.claims[cid]
        got = parse_277_status(client.claim_status(write_276(c, extract.answers[cid].payer_claim_no, "R", 7, AS_OF)))[0]
        assert got.category == {"rejected": "A3", "denied": "F2", "paid": "F1"}[state]
    unknown = write_276(next(iter(extract.claims.values())), "", "R", 8, AS_OF).replace(
        next(iter(extract.claims)), "NOSUCHCLAIM"
    )
    assert parse_277_status(client.claim_status(unknown))[0].category == "E1"
    if "rejected" in pick:
        c = extract.claims[pick["rejected"]]
        ok = client.submit_claim(write_corrected_837(c, "PCN", 9, AS_OF))
        assert ok["results"][0]["ok"] and "A2" in ok["277CA"]
        paid = extract.claims[pick["paid"]]
        no = client.submit_claim(write_corrected_837(paid, "PCN", 10, AS_OF))
        assert not no["results"][0]["ok"] and "original claim was not returned" in no["results"][0]["reason"]
    assert world.received_corrected


def test_the_client_refuses_a_real_endpoint_unless_it_is_enabled(monkeypatch):
    monkeypatch.delenv(ALLOW_ENV, raising=False)
    with pytest.raises(EndpointRefused):
        ClearinghouseClient("https://api.example-clearinghouse.com", "tok")
    monkeypatch.setenv(ALLOW_ENV, "1")
    ClearinghouseClient("https://api.example-clearinghouse.com", "tok").close()


def test_the_service_refuses_to_start_without_a_token(extract, book, monkeypatch):
    monkeypatch.delenv("KRISNAI_MOCK_CH_TOKEN", raising=False)
    with pytest.raises(ValueError):
        create_app(MockWorld(extract, truth_dir=book))


def test_masking_keeps_only_the_last_three_characters():
    assert mask("SYNM000232") == "*******232" and mask("") == ""


# ----------------------------------------------------------------------------------------- bots end to end


def test_eligibility_bot_closes_the_gaps_a1_flagged_and_the_agents_see_it(book, extract, tmp_path):
    day, appts = pick_bot_day(extract, book)
    assert appts, "the book has no planted check defect three days out on any day"
    start = day - timedelta(days=150)
    engines = {}
    for name in ("bot", "control"):
        inbox = tmp_path / f"in_{name}"
        shutil.copytree(book, inbox, ignore=shutil.ignore_patterns("*truth*"))
        eng = make_engine(tmp_path / f"{name}.sqlite")
        rep = run_period(eng, 1, SALT, day, inbox=inbox, archive=tmp_path / f"ar_{name}", mode="backfill",
                         start=start, step_days=28)  # fmt: skip
        assert rep.status == "ok", rep.reasons
        engines[name] = eng

    # at the 72 h checkpoint A1 has flagged the defect appointments; the bot works that list
    flagged = {a for a, (action, p) in latest_decisions(engines["bot"], 1, "a1_clearance", "appt").items()
               if a in appts}  # fmt: skip
    assert flagged, "A1 flagged none of the planted appointments at the 72 h checkpoint"
    client, app, world = make_client(extract, book, today=day)
    out = tmp_path / "bot_out"
    log = tmp_path / "bot_log.jsonl"
    rep = eligibility_bot(engines["bot"], 1, extract, client, out, day, limit=500, log_path=log)
    assert {e.outcome for e in rep.events} <= {"active", "coverage_inactive", "other_payer", "not_found", "skipped"}
    answered = {e.subject for e in rep.events if e.outcome != "skipped"}
    assert flagged & answered
    assert len(log.read_text().splitlines()) == len(rep.events)
    assert not any(c.member_id in log.read_text() for c in list(extract.claims.values())[:50])  # ids are masked

    # the next checkpoint (24 h) happens two days later; the bot database has the answers, the control does not
    after = day + timedelta(days=2)
    run_period(engines["bot"], 1, SALT, after, inbox=out, archive=tmp_path / "ar_bot2", mode="daily")
    run_period(engines["control"], 1, SALT, after, mode="daily")

    def gap_kinds(eng, appt):
        _, p = latest_decisions(eng, 1, "a1_clearance", "appt").get(appt, ("", {}))
        return {g["kind"] for g in p.get("gaps", [])}

    checked = sorted(flagged & answered)
    still_missing_control = [a for a in checked if gap_kinds(engines["control"], a) & {"no_eligibility_check", "stale_check"}]
    still_missing_bot = [a for a in checked if gap_kinds(engines["bot"], a) & {"no_eligibility_check", "stale_check"}]
    assert still_missing_control, "the control run should keep the check gaps open"
    assert len(still_missing_bot) < len(still_missing_control)
    assert not still_missing_bot


def test_status_and_resubmission_bots_write_files_the_loader_accepts(book, extract, tmp_path):
    day = AS_OF
    eng = make_engine(tmp_path / "s.sqlite")
    inbox = tmp_path / "in"
    shutil.copytree(book, inbox, ignore=shutil.ignore_patterns("*truth*"))
    rep = run_period(eng, 1, SALT, day, inbox=inbox, archive=tmp_path / "ar", mode="backfill",
                     start=day - timedelta(days=200), step_days=28)  # fmt: skip
    assert rep.status == "ok", rep.reasons
    client, _, world = make_client(extract, book, today=day)
    st = status_bot(eng, 1, extract, client, tmp_path / "out", day, limit=10)
    assert st.events and all(e.response_files for e in st.events if e.outcome != "skipped")
    rs = resubmission_bot(eng, 1, extract, client, tmp_path / "out", day, limit=10)
    assert all(e.outcome in ("accepted", "skipped") for e in rs.events)
    accepted = [e for e in rs.events if e.outcome == "accepted"]
    out = tmp_path / "out"
    for e in accepted:  # every file a bot wrote parses with the loader
        for name in [e.request_file, *e.response_files]:
            parse_x12((out / name).read_text(encoding="ascii"), SALT)
    again = run_period(eng, 1, SALT, day, inbox=out, archive=tmp_path / "ar2", mode="daily")
    assert again.status == "ok" and again.files_failed == 0
    assert json.dumps(rs.counts())  # serialisable for the Stage 1 report
