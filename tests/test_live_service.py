# ruff: noqa: E501
"""The local demo service: give it a transcript, it runs the whole workflow for that one visit and returns the trace."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from krisnai.live import service
from krisnai.live.emr import FakeEmr
from krisnai.live.service import create_app, samples


def client(tmp_path, engine=False, **kw) -> TestClient:
    return TestClient(create_app(tmp_path, {"fake": FakeEmr}, engine=engine), **kw)


def wait(c: TestClient, rid: str, timeout: float = 120) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        d = c.get(f"/api/run/{rid}").json()
        if d["status"] != "running":
            return d
        time.sleep(0.2)
    raise AssertionError("the run did not finish")


def run(c: TestClient, sample: dict, **kw) -> dict:
    r = c.post("/api/run", json={"transcript": sample["text"], "signed": sample["signed"], **kw})
    assert r.status_code == 200, r.text
    return wait(c, r.json()["id"])


def pick(label_part: str) -> dict:
    return next(s for s in samples() if label_part in s["label"].lower())


def test_health_and_samples(tmp_path):
    c = client(tmp_path)
    h = c.get("/api/health").json()
    assert h["ok"] and h["emr"] == ["fake"] and {p["id"] for p in h["payer"]} == {"random", "pays", "denies", "breaks_rules", "pends"}
    s = c.get("/api/samples").json()
    assert len(s) >= 8 and all(x["text"] and x["note"] for x in s) and any("problem" in x["label"] for x in s)


def test_a_complete_visit_goes_all_the_way_to_a_payer_decision_and_a_remit(tmp_path):
    d = run(client(tmp_path), next(s for s in samples() if "problem" not in s["label"]), payer="pays")
    assert d["status"] == "done", d["error"]
    c = d["claims"][0]
    assert c["coding"]["checks"] and c["payer"] and c["payer"]["outcome"] == "paid" and c["stage"] == "adjudicated"
    steps = {e["step"] for e in d["events"]}
    assert {"1 appointment", "2 eligibility", "3 visit", "4 claim", "5 clearinghouse", "6 payer", "7 remit"} <= steps
    assert d["ledger"]["cash_collected"] == "0.00" and d["ledger"]["remits_read"] == 1


def test_the_chosen_payer_behaviour_changes_the_outcome(tmp_path):
    c = client(tmp_path)
    s = next(s for s in samples() if "problem" not in s["label"])
    assert run(c, s, payer="denies")["claims"][0]["payer"]["outcome"] == "denied"
    dev = run(c, s, payer="breaks_rules")["claims"][0]["payer"]
    assert dev["deviation"] and dev["published"] == "paid"
    assert run(c, s, payer="pends")["claims"][0]["payer"]["pended"] == "1"


def test_lapsed_coverage_is_flagged_before_the_visit_and_the_payer_denies_it(tmp_path):
    d = run(client(tmp_path), next(s for s in samples() if "problem" not in s["label"]), coverage_lapsed=True)
    assert any(e["step"] == "2 eligibility" and e["outcome"] == "inactive" for e in d["events"])
    assert d["claims"][0]["payer"]["carc"] == "27"


def test_a_visit_that_fails_a_check_goes_to_a_coder_and_nothing_is_billed(tmp_path):
    d = run(client(tmp_path), pick("problem"), signed=False)
    c = d["claims"][0]
    assert d["status"] == "done" and c["stage"] == "pending_coder" and c["payer"] is None
    assert c["coding"]["route"] == "coder" and c["coding"]["reason"] and not any(e["step"] == "4 claim" for e in d["events"])


def test_the_same_transcript_pasted_by_hand_is_coded_the_same_way(tmp_path):
    s = next(s for s in samples() if "problem" not in s["label"])
    a, b = run(client(tmp_path / "a"), s), run(client(tmp_path / "b"), s)
    assert a["claims"][0]["coding"]["cpt"] == b["claims"][0]["coding"]["cpt"] and a["claims"][0]["coding"]["route"] == b["claims"][0]["coding"]["route"]


def test_bad_requests_are_refused(tmp_path):
    c = client(tmp_path)
    assert c.post("/api/run", json={"transcript": "   "}).status_code == 400
    assert c.post("/api/run", json={"transcript": "x" * (service.MAX_TRANSCRIPT + 1)}).status_code == 413
    assert c.post("/api/run", json={"transcript": "hello", "payer": "nonsense"}).status_code == 400
    assert c.post("/api/run", json={"transcript": "hello", "emr": "openemr"}).status_code == 400, "OpenEMR is off unless the service was started with it"
    assert c.get("/api/run/NOPE").status_code == 404


def test_only_one_visit_runs_at_a_time(tmp_path, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(service, "run_stream", lambda *a, **k: gate.wait(10))
    c = client(tmp_path)
    first = c.post("/api/run", json={"transcript": "a visit"})
    assert first.status_code == 200
    assert c.post("/api/run", json={"transcript": "another visit"}).status_code == 409
    gate.set()
    wait(c, first.json()["id"])
    assert c.post("/api/run", json={"transcript": "and now it is free"}).status_code == 200
    gate.set()


def test_a_failure_inside_a_run_is_reported_not_hidden(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("the EMR went away")

    monkeypatch.setattr(service, "run_stream", boom)
    c = client(tmp_path)
    d = wait(c, c.post("/api/run", json={"transcript": "a visit"}).json()["id"])
    assert d["status"] == "error" and "the EMR went away" in d["error"]


def test_it_answers_only_the_machine_it_runs_on_and_only_the_preview_origin(tmp_path):
    assert client(tmp_path, client=("10.1.2.3", 5000)).get("/api/health").status_code == 403
    c = client(tmp_path)
    ok = c.get("/api/health", headers={"Origin": "http://127.0.0.1:8767"})
    assert ok.headers.get("access-control-allow-origin") == "http://127.0.0.1:8767"
    assert "access-control-allow-origin" not in c.get("/api/health", headers={"Origin": "https://evil.example"}).headers


@pytest.mark.slow
def test_with_the_real_engine_a_denied_visit_gets_agent_work(tmp_path):
    d = run(client(tmp_path, engine=True), next(s for s in samples() if "problem" not in s["label"]), payer="denies")
    assert d["status"] == "done", d["error"]
    assert any(w["agent"] == "a8_denial" for w in d["claims"][0]["work"]), d["claims"][0]["work"]
    ag = d["claims"][0]["agents"]
    a8 = next(a for a in ag if a["agent"] == "a8_denial")
    assert a8["raised"] and a8["rules"] and a8["facts"] and a8["level"] == "L0 shadow" and a8["did"] and a8["title"], "what it did, how, and what it looked at"
    quiet = [a for a in ag if not a["raised"]]
    assert quiet and all(a["rules"] and a["did"] for a in quiet), "agents that looked and found nothing are shown too, with their checks"
    assert {a["name"] for a in ag} >= {"Mirror (A5)", "Code Whisperer (A4)", "Advocate (A8)"}


def batch(c: TestClient, items: list[dict], **kw) -> dict:
    r = c.post("/api/batch", json={"items": items, **kw})
    assert r.status_code == 200, r.text
    return wait(c, r.json()["id"])


def item(sample: dict, **kw) -> dict:
    return {"transcript": sample["text"], "signed": sample["signed"], **kw}


def test_a_batch_runs_every_visit_and_gives_each_its_own_claim_number(tmp_path):
    clean = [s for s in samples() if "problem" not in s["label"]]
    problem = pick("problem")
    d = batch(client(tmp_path), [item(clean[0]), item(problem, signed=False), item(clean[1])])
    assert d["status"] == "done", d["error"]
    cs = d["claims"]
    assert [c["id"][-5:] for c in cs] == ["00001", "00002", "00003"], "results come back in the order they were given"
    assert cs[0]["claim"] and cs[2]["claim"] and cs[0]["claim"] != cs[2]["claim"]
    assert cs[1]["stage"] == "pending_coder" and cs[1]["claim"] == "" and cs[1]["payer"] is None
    assert cs[0]["payer"]["claim_id"] == cs[0]["claim"] and cs[2]["payer"]["claim_id"] == cs[2]["claim"]
    assert d["ledger"]["remits_read"] == 2


def test_coverage_can_lapse_for_one_visit_in_a_batch_and_the_payer_behaviour_applies_to_all(tmp_path):
    clean = [s for s in samples() if "problem" not in s["label"]]
    d = batch(client(tmp_path), [item(clean[0]), item(clean[1], lapsed=True), item(clean[2])], payer="pays")
    carcs = [c["payer"]["carc"] for c in d["claims"]]
    assert carcs == ["", "27", ""], carcs
    d2 = batch(client(tmp_path / "x"), [item(clean[0]), item(clean[1])], payer="denies")
    assert [c["payer"]["outcome"] for c in d2["claims"]] == ["denied", "denied"]


def test_a_batch_has_limits_and_says_which_visit_is_wrong(tmp_path):
    c = client(tmp_path)
    ok = {"transcript": "a visit"}
    assert c.post("/api/batch", json={"items": []}).status_code == 400
    assert c.post("/api/batch", json={"items": [ok] * (service.MAX_BATCH + 1)}).status_code == 400
    bad = c.post("/api/batch", json={"items": [ok, {"transcript": "  "}]})
    assert bad.status_code == 400 and "visit 2" in bad.json()["detail"]
    big = {"transcript": "x" * service.MAX_TRANSCRIPT}
    assert c.post("/api/batch", json={"items": [big] * 11}).status_code == 413
    assert c.post("/api/batch", json={"items": [ok], "payer": "nonsense"}).status_code == 400


def test_a_batch_and_a_single_visit_share_the_one_run_at_a_time_rule(tmp_path, monkeypatch):
    gate = threading.Event()
    monkeypatch.setattr(service, "run_stream", lambda *a, **k: gate.wait(10))
    c = client(tmp_path)
    first = c.post("/api/batch", json={"items": [{"transcript": "a"}, {"transcript": "b"}]})
    assert first.status_code == 200 and first.json()["visits"] == 2
    assert c.post("/api/run", json={"transcript": "single"}).status_code == 409
    gate.set()
    wait(c, first.json()["id"])
