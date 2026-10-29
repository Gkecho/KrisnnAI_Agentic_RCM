"""The synthetic staff analytics behind the billing and coding manager screens (demo only; no database needed)."""

from collections import Counter
from datetime import date
from decimal import Decimal

import pytest

from krisnnai.demo import staff

AS_OF = date(2026, 10, 14)


def _cards(per_type: int = 30) -> list[dict]:
    cards = []
    for work in staff.WORK.values():
        for tt, owners in work:
            owner = sorted(owners)[0]
            for i in range(per_type):
                cards.append({
                    "action_type": tt, "owner": owner, "agent": "a8_denial" if tt.startswith("a8") else "x",
                    "expected_value": Decimal(10 + i), "claim": f"SYNC{tt[:3]}{i:04d}", "title": "t",
                    "raised_on": "2026-10-10",
                })  # fmt: skip
    return cards


@pytest.fixture(scope="module")
def built():
    return staff.build_staff(_cards(), AS_OF, lambda c: "Coverage")


def test_it_is_deterministic_and_labelled_synthetic(built):
    assert built["synthetic"] is True and "synthetic" in built["note"].lower()
    assert staff.build_staff(_cards(), AS_OF, lambda c: "Coverage") == built


def test_the_analysis_finds_every_planted_strength_weakness_and_nothing_else(built):
    f = built["found_vs_planted"]
    assert f["planted"] == len(staff.PLANTED) and f["found"] == f["planted"]
    assert f["flagged_but_not_planted"] == [], "no person is flagged for something that was not planted"
    kinds = {(g["employee"], g["task_type"], g["kind"]) for g in built["gaps"]}
    assert ("B02", "a6_rejection_task", "quality") in kinds and ("C04", "a5_hold_review", "speed") in kinds


def test_every_gap_has_evidence_a_sample_size_and_a_training_module(built):
    assert built["gaps"]
    for g in built["gaps"]:
        assert g["n"] >= staff.MIN_TASKS and g["module"] and g["evidence"]


def test_too_few_tasks_never_produce_a_flag(monkeypatch):
    monkeypatch.setattr(staff, "MIN_TASKS", 10_000)
    out = staff.build_staff(_cards(), AS_OF, None)
    assert out["gaps"] == [] and out["strengths"] == [] and out["allocation"] == []


def test_the_allocation_respects_capacity_fit_and_loses_no_item(built):
    people = {e["id"]: e for e in built["employees"]}
    for row in built["allocation"]:
        e = people[row["employee"]]
        assert row["load_after"] <= e["capacity_week"] and e["team"] == row["team"]
        assert built["metrics"][e["id"]][row["task_type"]]["n"] >= staff.MIN_TASKS
    placed = Counter()
    for row in built["allocation"]:
        placed[(row["team"], row["task_type"])] += row["items"]
    for x in built["unallocated"]:
        placed[(x["team"], x["task_type"])] += x["items"]
    for team, work in staff.WORK.items():
        for tt, _ in work:
            assert placed[(team, tt)] == 30, "every open item is either placed or listed as not placed"


def test_work_does_not_go_to_the_person_with_a_quality_gap_on_that_task(built):
    gap = {(g["employee"], g["task_type"]) for g in built["gaps"] if g["kind"] == "quality"}
    assert not [r for r in built["allocation"] if (r["employee"], r["task_type"]) in gap]


def test_a_person_near_capacity_is_flagged_and_gets_no_more_work(built):
    busy = [e for e in built["employees"] if e["busy"]]
    assert [e["id"] for e in busy] == ["C06"]
    assert not [r for r in built["allocation"] if r["employee"] == "C06"]
    assert any("close to capacity" in i["title"] for i in built["improvements"])


def test_scenarios_are_twelve_weeks_and_each_step_helps_or_holds(built):
    for sc in built["scenarios"].values():
        rows = {r["id"]: r for r in sc["scenarios"]}
        assert list(rows) == ["even", "suggested", "trained", "overtime", "upstream"]
        assert all(len(r["weeks"]) == staff.WEEKS for r in rows.values())
        assert rows["suggested"]["first_week_right"] >= rows["even"]["first_week_right"], "right the first time"
        done = [rows[k]["first_week_cleared"] for k in ("suggested", "trained", "overtime", "upstream")]
        assert done == sorted(done), "training and overtime never clear fewer tasks in the first week"
        assert all(r["first_week_cleared"] <= sc["ceiling_per_week"] for r in rows.values()), "the ceiling is a maximum"


def test_the_history_and_spread_cover_every_person_and_week(built):
    for team in staff.STAFF:
        h = built["history"][team]
        assert len(h["tasks"]) == staff.HISTORY_WEEKS and sum(h["tasks"]) == sum(sum(v) for v in h["by_type"].values())
    for e in built["employees"]:
        for spread in built["handle_time"][e["id"]].values():
            assert spread == sorted(spread), "p10 <= p25 <= median <= p75 <= p90"


def test_every_gap_says_how_much_work_closing_it_would_give_back(built):
    for g in built["gaps"]:
        assert g["avoidable_minutes"] > 0 and (g["kind"] == "speed" or g["avoidable_tasks"] > 0)
