# ruff: noqa: E501
"""The three pieces working as one: wide transcripts -> the reader and coder -> six payers -> the bots' replies.

These tests exist because each piece passed its own tests and the first combined run still found problems (a preventive visit
auto-accepted as an office visit, an MRI ordered with no stated reason auto-accepted, a visit plus therapy billed as therapy alone).
"""

from datetime import date

import pytest

from krisnai.live.coder import Coder, Policy
from krisnai.live.emr import FakeEmr
from krisnai.live.stream import StreamConfig, run_stream
from krisnai.live.transcripts import generate_wide

DAY = date(2026, 10, 24)
CODER = lambda: Coder(Policy(enabled=True, sample_rate=0.0))  # noqa: E731


def coded(seed: int, n: int = 150):
    c = CODER()
    return [(v, c.code(v.visit_id, v.text, v.signed, DAY)) for v in generate_wide(seed, n, DAY)]


@pytest.mark.parametrize("seed", [3, 7, 11])
def test_nothing_is_auto_accepted_with_a_code_that_disagrees_with_the_answer_key(seed):
    wrong = []
    for v, r in coded(seed):
        if r.route != "auto":
            continue
        x = v.expected
        if x.route != "auto" or r.cpt != x.cpt or r.dx[0][0] != x.dx:
            wrong.append((v.visit_id, v.visit_type, x.route, x.reason, x.cpt, r.cpt))
    assert wrong == [], wrong


@pytest.mark.parametrize("seed", [3, 7])
def test_every_problem_visit_goes_to_a_coder(seed):
    missed = [(v.visit_id, v.expected.reason, r.reason) for v, r in coded(seed) if v.expected.route == "coder" and r.route == "auto"]
    assert missed == [], missed


def test_preventive_and_emergency_visits_are_never_auto_accepted():
    seen = 0
    for v, r in coded(7, 300):
        if v.visit_type.startswith(("wide_Z00", "wide_Z01", "wide_Z23")) or v.expected.cpt.startswith(("9928", "9938", "9939")):
            seen += 1
            assert r.route == "coder", (v.visit_id, v.expected.cpt, r.cpt, r.reason)
    assert seen >= 3


def test_an_order_with_no_stated_reason_is_not_auto_accepted():
    bad = [(v.visit_id, r.reason) for v, r in coded(7, 300) if "necessity_not_documented" in v.expected.pressure and r.route == "auto"]
    assert bad == [], bad


def test_the_visit_code_follows_how_deep_the_documentation_is():
    got = {r.cpt for _, r in coded(7, 300) if r.route == "auto"}
    assert {"99212", "99213", "99214"} <= got, got


def test_a_visit_note_with_therapy_is_a_modifier_question_for_a_coder():
    hits = [r for v, r in coded(7, 300) if v.expected.services and any(s.startswith("971") for s in v.expected.services) and v.expected.services[0].startswith("992")]
    assert hits and all(r.route == "coder" for r in hits)


def test_a_bigger_catalog_is_read_from_the_same_catalog_the_generator_used():
    from krisnai.live import catalog

    assert len(catalog.CONDITIONS) >= 45 and len(catalog.SERVICES) >= 35
    named = sum(1 for v, r in coded(7, 150) if r.dx and v.expected.dx and r.dx[0][0] == v.expected.dx)
    assert named >= 120, "the reader names the right main diagnosis on most wide visits"


def test_a_thirty_visit_run_goes_through_six_payers_replies_and_settles(tmp_path):
    cfg = StreamConfig(count=30, seed=5, wide=True, payers="network", replies=True, reject_rate=0.1, engine=False, bots=False, serve=False, sample_rate=0.0)
    emr = FakeEmr()
    s = run_stream(tmp_path / "r", cfg, emr, log=lambda *_: None)
    assert s["encounters"] == 30 and emr.counts()["visits"] == 30
    stages = s["stages"]
    assert "adjudicated" not in stages, "with replies on every claim ends settled, in review, or as a patient balance"
    assert sum(stages.values()) == 30 and (stages.get("pending_coder", 0) + stages.get("review", 0) + stages.get("patient_balance", 0) + stages.get("settled", 0)) == 30
    assert len(s["replies"]["sent"]) >= 1 and s["replies"]["claims"] >= 1
    import csv

    rows = list(csv.DictReader((tmp_path / "r" / "truth.csv").read_text("utf-8").splitlines()))
    assert len(rows) == s["replies"]["claims"]
    assert (tmp_path / "r" / "truth_payers.csv").exists() and len({r["payer_id"] for r in csv.DictReader((tmp_path / "r" / "truth_payers.csv").read_text("utf-8").splitlines())}) >= 3
