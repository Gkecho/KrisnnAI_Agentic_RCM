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
    prio = [float(q["priority"]) for q in data["queue"]]
    assert prio == sorted(prio, reverse=True)
    assert (out / "ui_data.js").read_text(encoding="utf-8").startswith("window.KRISNAI_LIVE = {")


def test_a_missing_synthea_folder_says_how_to_make_one(tmp_path):
    with pytest.raises(SystemExit, match="Synthea"):
        make_demo(tmp_path / "o", tmp_path / "nope", AS_OF, log=lambda *_: None)
