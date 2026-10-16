"""Stage 1 runner: the whole loop on a small book, with real HTTP between the bots and the local mock services."""

from __future__ import annotations

import json
from datetime import date

import pytest

from krisnai.integrations.stage1 import run_stage1
from tests.fixtures import synthea_mini

AS_OF = date(2026, 6, 30)


@pytest.fixture(scope="module")
def stage1(tmp_path_factory):
    root = tmp_path_factory.mktemp("stage1")
    raw = synthea_mini.write(root / "raw", n_claims=320, n_patients=45, seed=5)
    return run_stage1(root / "out", raw, AS_OF, seed=7, limit=15, log=lambda *_: None)


def test_the_loop_runs_and_the_report_says_it_is_mock(stage1):
    html = stage1.report.read_text(encoding="utf-8")
    assert "Mock endpoints, not a real payer or EMR" in html
    for section in ("Eligibility bot", "Claim status bot", "Resubmission bot", "Portal bot", "FHIR"):
        assert section in html
    assert "<script" not in html and "https://" not in html


def test_the_bots_acted_and_the_agents_saw_the_eligibility_answers(stage1):
    s = stage1.summary
    assert sum(s["bots"]["eligibility"].values()) > 0 and sum(s["bots"]["status"].values()) > 0
    assert s["checked"] > 0, "no flagged appointment was checked by the bot"
    assert s["control_still_missing"] > 0
    assert s["bot_still_missing"] < s["control_still_missing"]


def test_the_portal_bot_reads_and_stops_on_a_redesigned_portal(stage1):
    s = stage1.summary
    assert s["portal"].get("read", 0) > 0
    assert s["portal_changed"][0] == "screen_changed" and set(s["portal_changed"][1:]) <= {"not_attempted"}
    assert s["portal_changed_requests"] == 4  # login form, sign in, search, claim page: then nothing


def test_nothing_secret_or_identifying_is_in_the_log_or_the_report(stage1):
    log = (stage1.root / "bot_log.jsonl").read_text(encoding="utf-8")
    html = stage1.report.read_text(encoding="utf-8")
    for token in ("stage1-local-token", "stage1-local-only"):
        assert token not in log and token not in html
    assert json.loads((stage1.root / "summary.json").read_text())["day"] == stage1.day.isoformat()
    members = {line.split(",")[3] for line in (stage1.root / "book" / "visits.csv").read_text().splitlines()[1:]}
    assert members and not any(m in log for m in members)  # member ids appear masked, never in full
