# ruff: noqa: E501
"""S4 of the live encounter stream: the orchestrator and clock, tested with an in-memory EMR and in-process servers (no Docker)."""

import csv
import json
from datetime import date
from pathlib import Path

import pytest

from krisnai.live.emr import FakeEmr
from krisnai.live.stream import SimulatedCrash, StreamConfig, run_stream

CFG = dict(count=14, per_day=5, engine=False, bots=False, serve=False)


def cfg(**kw) -> StreamConfig:
    return StreamConfig(**{**CFG, **kw})


def events(out: Path) -> list[dict]:
    return [json.loads(ln) for ln in (out / "events.jsonl").read_text("utf-8").splitlines()]


def test_every_encounter_goes_through_the_whole_chain_with_no_data_typed_in(tmp_path):
    emr = FakeEmr()
    s = run_stream(tmp_path / "r", cfg(), emr, log=lambda *_: None)
    assert s["encounters"] == 14 and emr.counts() == {"patients": 14, "visits": 14, "appointments": 14}
    assert s["stages"].get("adjudicated", 0) + s["stages"].get("pending_coder", 0) == 14
    assert s["remits_issued"] == s["stages"]["adjudicated"] and s["coder_queue"] == s["stages"].get("pending_coder", 0)
    steps = {e["step"] for e in events(tmp_path / "r")}
    assert {"1 appointment", "2 eligibility", "3 visit", "3b coder", "4 claim", "5 clearinghouse", "6 payer", "7 remit"} <= steps


def test_the_problem_visits_wait_for_a_coder_and_nothing_is_billed_for_them(tmp_path):
    out = tmp_path / "r"
    s = run_stream(out, cfg(count=20), FakeEmr(), log=lambda *_: None)
    q = [json.loads(ln) for ln in (out / "coder_queue.jsonl").read_text("utf-8").splitlines()]
    assert q and s["coder_queue"] == len(q) and all(x["reason"] for x in q)
    billed = {e["subject"] for e in events(out) if e["step"] == "4 claim"}
    waiting = {x["visit"] for x in q}
    assert not [b for b in billed if b.split("-")[0] and b in waiting]


def test_the_payers_decisions_stay_out_of_the_engines_inbox_and_in_the_truth_log(tmp_path):
    out = tmp_path / "r"
    s = run_stream(out, cfg(), FakeEmr(), log=lambda *_: None)
    assert not [p for p in (out / "inbox").rglob("*") if "truth" in p.name]
    rows = list(csv.DictReader((out / "truth.csv").read_text("utf-8").splitlines()))
    assert len(rows) == sum(1 for e in json.loads((out / "state.json").read_text("utf-8"))["enc"].values() if e["stage"] == "adjudicated")
    assert sum(s["payer_outcomes"].values()) == len(rows)


def test_a_quality_check_sample_is_confirmed_by_a_simulated_person_labelled_as_such(tmp_path):
    out = tmp_path / "r"
    run_stream(out, cfg(count=50), FakeEmr(), log=lambda *_: None)
    conf = [e for e in events(out) if e["step"] == "3c coder"]
    assert conf and all("simulated" in e["detail"] and e["tool"] == "Simulated coder" for e in conf)
    st = json.loads((out / "state.json").read_text("utf-8"))["enc"]
    assert any(e.get("approval", "").startswith("person:simulated-coder") for e in st.values())
    assert any(e.get("approval", "").startswith("policy:") for e in st.values())


def test_a_lapsed_coverage_is_flagged_before_the_visit_and_denied_by_the_payer(tmp_path):
    out = tmp_path / "r"
    run_stream(out, cfg(count=50, inactive_rate=0.3), FakeEmr(), log=lambda *_: None)
    flagged = {e["subject"] for e in events(out) if e["step"] == "2 eligibility" and e["outcome"] == "inactive"}
    assert flagged
    rows = {r["claim_id"]: r for r in csv.DictReader((out / "truth.csv").read_text("utf-8").splitlines())}
    st = json.loads((out / "state.json").read_text("utf-8"))["enc"]
    inactive_claims = [e["claim"] for e in st.values() if e.get("active") is False and e.get("claim") in rows]
    assert inactive_claims and all(rows[c]["outcome"] == "denied" and rows[c]["carc"] == "27" for c in inactive_claims)


@pytest.mark.parametrize("crash_at", [1, 7, 23, 40, 77])
def test_a_run_killed_anywhere_resumes_without_repeating_or_losing_an_encounter(tmp_path, crash_at):
    ref_emr, emr = FakeEmr(), FakeEmr()
    ref = run_stream(tmp_path / "ref", cfg(), ref_emr, log=lambda *_: None)
    out = tmp_path / "run"
    with pytest.raises(SimulatedCrash):
        run_stream(out, cfg(), emr, log=lambda *_: None, crash_after=crash_at)
    done = run_stream(out, cfg(), emr, log=lambda *_: None)  # same folder, same EMR: a restart
    assert emr.counts() == ref_emr.counts() == {"patients": 14, "visits": 14, "appointments": 14}, "no duplicate and no lost encounter"
    assert (out / "truth.csv").read_text("utf-8") == (tmp_path / "ref" / "truth.csv").read_text("utf-8"), "the same decisions as an uninterrupted run"
    assert done["stages"] == ref["stages"] and done["payer_outcomes"] == ref["payer_outcomes"] and done["remits_issued"] == ref["remits_issued"]
    keys = [e["key"] for e in events(out)]
    assert len(keys) == len(set(keys)), "no event is recorded twice"
    names = lambda d: sorted(p.name for p in (d / "inbox").glob("*") if p.suffix != ".csv")  # noqa: E731
    assert names(out) == names(tmp_path / "ref")


def test_a_saved_run_will_not_continue_with_different_settings(tmp_path):
    run_stream(tmp_path / "r", cfg(count=6), FakeEmr(), log=lambda *_: None)
    with pytest.raises(SystemExit, match="different settings"):
        run_stream(tmp_path / "r", cfg(count=6, seed=99), FakeEmr(), log=lambda *_: None)


def test_the_run_uses_only_the_simulation_clock(tmp_path):
    out = tmp_path / "r"
    run_stream(out, cfg(count=6), FakeEmr(), log=lambda *_: None)
    days = {e["day"] for e in events(out)}
    assert min(days) == "2026-10-21" and all(d >= "2026-10-21" and d <= "2026-12-31" for d in days)
    assert date.fromisoformat(json.loads((out / "state.json").read_text("utf-8"))["day"]) > date(2026, 11, 20)


def _openemr_up() -> bool:
    try:
        import httpx

        return httpx.get("http://127.0.0.1:8300/apis/default/fhir/metadata", timeout=5).status_code == 200
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.slow
def test_with_the_real_engine_and_bots_the_payers_answers_become_agent_work(tmp_path):
    out = tmp_path / "r"
    s = run_stream(out, StreamConfig(count=12, per_day=6, deviation_rate=0.5, deny_rate=0.4, serve=True), FakeEmr(), log=lambda *_: None)
    assert s["cards_for_stream_claims"], "the engine raised work on the streamed claims"
    assert any(k.startswith("a8_denial") for k in s["cards_for_stream_claims"]), s["cards_for_stream_claims"]
    assert not [p for p in (out / "inbox").rglob("*") if "truth" in p.name]


@pytest.mark.slow
@pytest.mark.skipif(not _openemr_up(), reason="the local OpenEMR is not running")
def test_against_the_real_openemr_a_killed_run_resumes_with_no_duplicate_patients(tmp_path):
    from krisnai.integrations.openemr import seed as oeseed
    from krisnai.integrations.openemr.auth import OpenEmrAuth
    from krisnai.live.emr import OpenEmrPort

    def port():
        return OpenEmrPort(oeseed._Server(OpenEmrAuth(Path("out/openemr"))))

    before = len(port().server.rest_rows("/patient"))
    out = tmp_path / "r"
    c = StreamConfig(count=5, per_day=5, serve=True)
    with pytest.raises(SimulatedCrash):
        run_stream(out, c, port(), log=lambda *_: None, crash_after=14)
    s = run_stream(out, c, port(), log=lambda *_: None)
    rows = port().server.rest_rows("/patient")
    members = [f"SYNST{i:05d}" for i in range(1, 6)]
    assert s["encounters"] == 5
    assert [sum(1 for p in rows if p.get("pubpid") == m) for m in members] == [1] * 5, "exactly one patient per member, never two"
    assert len(rows) <= before + 5, "members that already exist are reused, not created again"
