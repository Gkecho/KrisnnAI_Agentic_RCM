"""The mock practice: build, run all fifteen agents through the runner, and render one deterministic page."""

from __future__ import annotations

import re
from datetime import date

import pytest

from krisnai import cli
from krisnai.demo import make_demo, write_report
from krisnai.ops import watermark
from tests.fixtures import synthea_mini

AS_OF = date(2026, 6, 30)


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo")
    raw = synthea_mini.write(root / "raw", n_claims=700, n_patients=70, seed=5)
    res = make_demo(root / "out", raw, AS_OF, log=lambda *_: None)
    return {"root": root, "raw": raw, "res": res}


def test_the_run_finishes_ok_and_everything_is_on_disk(demo):
    res = demo["res"]
    assert res.report.status == "ok" and res.report.gate == "passed"
    assert watermark(res.engine, res.tenant_id) == AS_OF
    out = demo["root"] / "out"
    assert (out / "demo.sqlite").exists() and (out / "report.html").exists()
    keys = {p.name for p in (out / "truth").iterdir()}
    assert {"ground_truth.csv", "doc_truth.csv", "elig_truth.csv", "pattern_truth.csv"} <= keys
    assert not list((out / "inbox").glob("*truth*"))  # answer keys are not feeds
    assert res.planted["rate_cut"]["payer"] != res.planted["denial_pattern"]["payer"]


def test_report_has_every_agent_the_queue_and_the_shadow_banner(demo):
    html = (demo["root"] / "out" / "report.html").read_text(encoding="utf-8")
    for n in range(1, 16):
        assert f'id="a{n}"' in html
    assert "Shadow mode" in html and "Work queue" in html and "Planted payer-wide problems" in html
    assert "<script" not in html and "http://" not in html and "https://" not in html  # self-contained
    assert re.search(r"\d+ open items", html)


def test_report_is_deterministic_and_holds_no_member_ids(demo):
    res, out = demo["res"], demo["root"] / "out"
    first = (out / "report.html").read_text(encoding="utf-8")
    write_report(res.engine, res.tenant_id, out, AS_OF, planted=res.planted, run=res.report)
    assert (out / "report.html").read_text(encoding="utf-8") == first
    with (out / "archive" / AS_OF.isoformat() / "visits.csv").open(encoding="utf-8") as f:
        next(f)
        members = {line.split(",")[3] for line in f if line.strip()}
    assert members and not any(mem in first for mem in members)


def test_cli_demo_rebuilds_the_folder_and_prints_the_report_path(demo, capsys):
    out = demo["root"] / "out2"
    rc = cli.main(["demo", "--out", str(out), "--synthea", str(demo["raw"]), "--as-of", AS_OF.isoformat()])
    text = capsys.readouterr().out
    assert rc == 0 and "report:" in text and (out / "report.html").exists()
    rc = cli.main(["demo", "--out", str(out), "--synthea", str(demo["raw"]), "--as-of", AS_OF.isoformat()])
    assert rc == 0  # the second run wipes and rebuilds the same folder


def test_ui_data_has_the_documented_shape_and_matches_the_report(demo):
    import json

    out = demo["root"] / "out"
    data = json.loads((out / "ui_data.json").read_text(encoding="utf-8"))
    assert data["schema"] == 1 and data["meta"]["shadow"] is True and data["meta"]["as_of"] == AS_OF.isoformat()
    assert [a["id"] for a in data["agents"]] == [f"A{n}" for n in range(1, 16)]
    assert all({"decisions", "proposed", "actions", "planted", "examples"} <= set(a) for a in data["agents"])
    keys = {"agent", "owner", "title", "value", "deadline", "overdue", "why", "next_steps", "evidence"}
    assert data["queue"] and all(keys <= set(q) for q in data["queue"])
    extra = {"action_type", "claim", "payer", "billed", "queue_type", "confidence", "filing_days_left"}
    assert all(extra <= set(q) for q in data["queue"])
    pills = {"Denial", "Rejection", "No response", "Underpaid", "Filing risk"}
    typed = [q for q in data["queue"] if q["queue_type"]]
    assert typed and {q["queue_type"] for q in typed} <= pills
    assert all(q["payer"] and q["billed"] is not None for q in typed), "a worklist row needs its payer and billed amount"
    assert all(q["queue_type"] is None for q in data["queue"] if q["agent"] not in
               {"a6_submission", "a7_ar", "a8_denial", "a10_underpay"})  # fmt: skip
    prio = [float(q["priority"]) for q in data["queue"]]
    assert prio == sorted(prio, reverse=True)
    from collections import Counter

    from krisnai.demo.export import QUEUE_PER_KEY

    shown = Counter(f"{q['owner']}|{q['agent']}" for q in data["queue"])
    tot = data["queue_totals"]
    assert set(shown) <= set(tot) and all(n <= QUEUE_PER_KEY for n in shown.values())
    assert all(tot[k]["open"] >= n for k, n in shown.items()), "the totals count everything that is open"
    stats = data["queue_stats"]
    assert set(stats) == set(tot) and all(stats[k]["open"] == tot[k]["open"] and stats[k]["value"] == tot[k]["value"] for k in tot)
    assert all(sum(x["open"] for x in v["by_cause"]) == v["open"] for v in stats.values()), "every item has a cause"
    st = data["staff"]
    assert st["synthetic"] is True and st["employees"] and st["allocation"]
    assert st["found_vs_planted"]["found"] == st["found_vs_planted"]["planted"]
    assert {"billing", "coding"} <= set(st["scenarios"]) and {"history", "handle_time", "rework_minutes"} <= set(st)
    ref = {"carc_routes", "rejection_routes", "ncci_pairs", "mue_limits", "fee_schedule", "auth_requirements",
           "filing_windows", "appeal_windows", "policy"}  # fmt: skip
    assert ref <= set(data["reference"]) and data["reference"]["carc_routes"] and data["reference"]["fee_schedule"]
    assert (out / "ui_data.js").read_text(encoding="utf-8").startswith("window.KRISNAI_LIVE = {")
    rp = data["replay"]
    assert rp["reconciliation"] and all(c["passed"] for c in rp["reconciliation"]), "the run's gate passed"
    assert {"claims", "clean_claim_rate", "days_in_ar", "ar_over_90_share"} <= set(rp["health"])
    assert rp["found_vs_planted"] and all(
        {"type", "planted", "found", "precision", "recall", "correct_recall"} <= set(x) for x in rp["found_vs_planted"]
    )
    assert len(rp["opportunities"]) <= 25 and len(rp["by_payer"]) <= 10


def test_replay_section_is_empty_without_a15_and_has_no_scores_without_an_answer_key(tmp_path):
    import json

    from krisnai.demo.export import _replay

    assert _replay(None, 1, tmp_path, AS_OF) == {}  # no a15 folder: nothing to show, nothing touched
    (tmp_path / "a15").mkdir()
    doc = {
        "kpis": {"clean_claim_rate": [{"submitted_claims": 10, "clean_claim_rate": "0.9"}], "days_in_ar": [{"days_in_ar": "40"}],
                 "ar_over_90": [{"ar_over_90_share": "0.2"}]},
        "reconciliation": {"checks": [{"name": "claim_charge", "passed": True}]},
        "by_payer": [{"key": f"P{i}"} for i in range(15)],
        "opportunities": [{"claim": f"C{i}"} for i in range(40)],
    }  # fmt: skip
    (tmp_path / "a15" / "a15_lite.json").write_text(json.dumps(doc), encoding="utf-8")
    out = _replay(None, 1, tmp_path, AS_OF)  # engine is not used without truth/ground_truth.csv
    assert out["health"] == {"claims": 10, "clean_claim_rate": "0.9", "days_in_ar": "40", "ar_over_90_share": "0.2"}
    assert out["reconciliation"] == [{"name": "claim_charge", "passed": True}]
    assert len(out["by_payer"]) == 10 and len(out["opportunities"]) == 25
    assert "found_vs_planted" not in out


def test_a_missing_synthea_folder_says_how_to_make_one(tmp_path):
    with pytest.raises(SystemExit, match="Synthea"):
        make_demo(tmp_path / "o", tmp_path / "nope", AS_OF, log=lambda *_: None)
