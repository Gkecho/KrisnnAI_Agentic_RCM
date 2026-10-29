"""S2 of the live encounter stream: synthetic transcripts with an answer key, and the exception-only coder (ADR-0002)."""

import json
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from krisnnai.live.coder import Coder, Policy
from krisnnai.live.transcripts import generate

DAY = date(2026, 10, 24)
ON = Policy(enabled=True)


def _run(seed: int, policy: Policy = ON, n: int = 50):
    visits = generate(seed, n)
    coder = Coder(policy)
    return [(v, coder.code(v.visit_id, v.text, v.signed, v.day)) for v in visits]


def test_the_generator_is_deterministic_and_about_a_fifth_problematic():
    a, b = generate(7), generate(7)
    assert [v.text for v in a] == [v.text for v in b] and generate(8)[0].text != a[0].text
    assert len(a) == 50 and Counter(v.expected.route for v in a) == {"auto": 40, "coder": 10}
    assert {v.expected.reason for v in a if v.expected.route == "coder"} == {
        "missing_plan", "two_problems", "status_unclear", "unsigned", "thin_chronic"}


@pytest.mark.parametrize("seed", [7, 11, 23, 99])
def test_the_coder_matches_the_answer_key_and_never_auto_accepts_a_problem(seed):
    for v, r in _run(seed):
        if v.expected.route == "auto":
            assert r.route == "auto" or r.reason == "qa_sample", (v.visit_id, r.reason, r.note)
            assert r.cpt == v.expected.cpt and r.dx[0][0] == v.expected.dx, (v.visit_id, r.cpt, r.dx)
        else:
            assert r.route == "coder" and r.reason == v.expected.reason, (v.visit_id, v.expected.reason, r.reason)
            assert r.approval == "pending:coder"


def test_an_auto_accept_names_the_policy_not_a_person():
    autos = [r for _, r in _run(7) if r.route == "auto"]
    assert autos and all(r.approval == "policy:demo-exception-only-v1" for r in autos)


def test_a_sample_of_clean_visits_still_goes_to_a_coder_and_replays_the_same():
    first = [r.visit_id for _, r in _run(7) if r.reason == "qa_sample"]
    assert first == [r.visit_id for _, r in _run(7) if r.reason == "qa_sample"]
    assert 1 <= len(first) <= 8, "about 10% of 40 clean visits"


def test_with_the_policy_off_every_clean_visit_goes_to_a_coder():
    out = _run(7, Policy(enabled=False))
    assert not [r for _, r in out if r.route == "auto"]
    assert Counter(r.reason for v, r in out if v.expected.route == "auto") == {"policy_off": 40}


def test_the_daily_cap_stops_auto_accepts_and_says_why():
    out = _run(7, Policy(enabled=True, sample_rate=0.0, daily_cap=3), n=20)
    per_day = Counter(r.day for _, r in out if r.route == "auto")
    assert max(per_day.values()) == 3
    assert any(r.reason == "daily_cap_reached" for _, r in out)


def test_wording_the_generator_never_used_is_still_read():
    """Held-out transcripts written by hand, not drawn from the generator's phrase pools."""
    clean = ("Provider: Welcome back, I see you were last seen in June. Patient: Yes. My throat has been scratchy since Monday, "
             "roughly four days, mild to moderate, with some fever, and it is worse when I swallow.\n"
             "Provider: On exam your throat looks a little red.\nProvider: Assessment: pharyngitis.\n"
             "Provider: Plan: fluids and rest, return in a week.\nSigned electronically by Dr. Demo Provider.")
    r = Coder(ON).code("HELD1", clean, True, DAY)
    assert (r.cpt, r.dx[0][0]) == ("99213", "J02.9") and r.route in ("auto", "coder")
    assert r.reason in ("", "qa_sample")
    no_plan = clean.replace("Provider: Plan: fluids and rest, return in a week.\n", "")
    assert Coder(ON).code("HELD2", no_plan, True, DAY).reason == "missing_plan"
    assert Coder(ON).code("HELD3", clean, False, DAY).reason == "unsigned"


def test_a_note_that_is_not_signed_in_the_record_is_never_coded_even_if_the_text_says_signed():
    v = generate(7)[0]
    assert Coder(ON).code(v.visit_id, v.text, False, v.day).reason == "unsigned"


def test_records_are_plain_json_with_the_checks_shown():
    v, r = _run(7)[0]
    d = json.loads(json.dumps(r.to_dict()))
    assert {c["name"] for c in d["checks"]} == {"signed", "baseline", "status", "one_diagnosis", "depth", "mue", "ncci"}


def test_the_coder_never_sees_the_answer_key():
    src = (Path(__file__).resolve().parents[1] / "krisnnai" / "live" / "coder.py").read_text(encoding="utf-8")
    imports = [ln for ln in src.splitlines() if ln.startswith(("import ", "from "))]
    assert not [ln for ln in imports if "transcripts" in ln] and "Expected" not in src


def _openemr_up() -> bool:
    try:
        import httpx

        return httpx.get("http://127.0.0.1:8300/apis/default/fhir/metadata", timeout=5).status_code == 200
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.slow
@pytest.mark.skipif(not _openemr_up(), reason="the local OpenEMR is not running")
def test_live_an_auto_accepted_transcript_is_charged_by_policy_and_an_unsigned_one_stops_at_the_coder(tmp_path):
    from krisnnai.live.s1 import run_s1

    v = generate(7, 50)
    ok = run_s1(Path("out/openemr"), tmp_path / "a", date(2026, 10, 21), visit=v[0], coder=Coder(ON), log=lambda *_: None)
    assert ok.summary["engine_status"] == "ok" and ok.summary["coding"]["route"] == "auto"
    assert ok.summary["coding"]["approval"].startswith("policy:") and ok.summary["payer_outcome"] == "paid"
    stop = run_s1(Path("out/openemr"), tmp_path / "b", date(2026, 10, 21), visit=v[5], coder=Coder(ON), log=lambda *_: None)
    assert stop.summary["routed_to_coder"] == "unsigned" and "claim" not in stop.summary, "nothing is billed"
