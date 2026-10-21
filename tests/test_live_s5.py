# ruff: noqa: E501
"""S5 of the live encounter stream: the scorecard against the payer's hidden decisions, and the remit reconciliation."""

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from krisnai.live import score
from krisnai.live.emr import FakeEmr
from krisnai.live.payer import TRUTH_COLUMNS, PayerConfig, PayerSim
from krisnai.live.stream import StreamConfig, run_stream
from krisnai.synthea import x12out
from krisnai.synthea.types import PayerInfo, Person, SimClaim, SimLine

INFO = PayerInfo("SYNAETNA", "SYNAETNA Demo Payer", Decimal("1"), 14)


def _claim(i: int) -> SimClaim:
    p = Person(f"SYNM{i:05d}", f"LAST{i}", "Synthetic", date(1980, 1, 1), "F")
    return SimClaim(f"C{i:05d}", INFO, "1999999984", p, date(2026, 3, 2), ["J029"], [SimLine("99213", 1, Decimal("110.00"), Decimal("0"))], date(2026, 3, 3))


def _run_folder(tmp: Path, n: int = 6, **cfg) -> tuple[Path, PayerSim]:
    """A hand-made run folder: a payer sim's decisions, their 835s in the inbox, and a minimal state."""
    sim = PayerSim("SYNAETNA", "SYNAETNA Demo Payer", config=PayerConfig(seed=3, **cfg))
    (tmp / "inbox").mkdir(parents=True)
    (tmp / "archive").mkdir()
    for i in range(n):
        d = sim.adjudicate(_claim(i), date(2026, 3, 3))
        (tmp / "inbox" / f"835_{d.claim.claim_id}.835").write_text(x12out.write_835(INFO, d.remit_date, [d.claim], 7000 + i), encoding="utf-8")
    (tmp / "truth.csv").write_text(sim.truth_csv(), encoding="utf-8")
    (tmp / "state.json").write_text(json.dumps({"config": {"seed": 7, "count": 1, "start": "2026-10-21"}, "enc": {}, "issued": [f"C{i:05d}" for i in range(n)]}), encoding="utf-8")
    return tmp, sim


def test_the_remits_tie_out_to_the_payers_truth_and_cash_is_never_shown_as_collected(tmp_path):
    run, sim = _run_folder(tmp_path / "r", n=20, deny_rate=0.3, deviation_rate=0.3)
    led = score.reconcile(run)
    paid = sum((d.claim.paid for d in sim.cases.values()), Decimal(0))
    assert led["remits_read"] == 20 and led["tie_out_mismatches"] == [] and led["awaiting_remit"] == []
    assert Decimal(led["remitted_by_payer"]) == paid
    assert led["cash_collected"] == "0.00" and "No bank deposits" in led["cash_note"]


def test_an_835_that_disagrees_with_the_truth_log_is_flagged(tmp_path):
    run, _ = _run_folder(tmp_path / "r", n=5)
    f = run / "inbox" / "835_C00002.835"
    f.write_text(f.read_text("utf-8").replace("CLP*C00002*1*110*72*18", "CLP*C00002*1*110*99*18"), encoding="utf-8")
    led = score.reconcile(run)
    assert [m["claim"] for m in led["tie_out_mismatches"]] == ["C00002"]


def test_the_same_remit_in_two_files_is_counted_once(tmp_path):
    run, sim = _run_folder(tmp_path / "r", n=4)
    (run / "archive" / "2026-03-20").mkdir()
    (run / "archive" / "2026-03-20" / "835_C00001.835").write_text((run / "inbox" / "835_C00001.835").read_text("utf-8"), encoding="utf-8")
    led = score.reconcile(run)
    assert led["remits_read"] == 4 and led["duplicate_claims"] == 1
    assert Decimal(led["remitted_by_payer"]) == sum((d.claim.paid for d in sim.cases.values()), Decimal(0)), "no double count"


def test_a_claim_without_a_remit_is_listed_as_awaiting(tmp_path):
    run, _ = _run_folder(tmp_path / "r", n=4)
    (run / "inbox" / "835_C00003.835").unlink()
    assert score.reconcile(run)["awaiting_remit"] == ["C00003"]


def test_every_kind_of_payer_behaviour_is_classified():
    row = lambda **k: {c: "" for c in TRUTH_COLUMNS} | k  # noqa: E731
    assert score._kind(row(outcome="paid", published="paid")) == "paid_clean"
    assert score._kind(row(outcome="denied", published="paid", carc="50")) == "denied_ordinary"
    assert score._kind(row(outcome="denied", published="denied", carc="27")) == "denied_published"
    assert score._kind(row(outcome="denied", published="paid", deviation="wrong_denial")) == "denied_deviation"
    assert score._kind(row(outcome="underpaid", published="paid", deviation="underpay_off_schedule")) == "underpaid"


def test_found_missed_false_alarm_and_recognized_are_counted_against_the_truth(tmp_path, monkeypatch):
    run = tmp_path / "r"
    run.mkdir()
    rows = [
        {"claim_id": "A", "outcome": "denied", "published": "paid", "carc": "50", "deviation": ""},
        {"claim_id": "B", "outcome": "denied", "published": "paid", "carc": "31", "deviation": "wrong_denial"},
        {"claim_id": "C", "outcome": "underpaid", "published": "paid", "carc": "", "deviation": "underpay_off_schedule"},
        {"claim_id": "D", "outcome": "paid", "published": "paid", "carc": "", "deviation": ""},
        {"claim_id": "E", "outcome": "paid", "published": "paid", "carc": "", "deviation": ""},
    ]
    with (run / "truth.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=TRUTH_COLUMNS)
        w.writeheader()
        w.writerows({c: "" for c in TRUTH_COLUMNS} | {"paid": "0", "billed": "110"} | r for r in rows)
    (run / "state.json").write_text(json.dumps({"config": {"seed": 7, "count": 1, "start": "2026-10-21"}, "enc": {}, "issued": []}), encoding="utf-8")
    (run / "inbox").mkdir()
    (run / "archive").mkdir()
    dec = {"a8_denial": {"A": [{"action": "a8_fix_task", "known": "x", "text": "{}"}],
                         "B": [{"action": "a8_appeal_task", "known": "x", "text": '{"why": "contradicts the published rules"}'}],
                         "D": [{"action": "a8_fix_task", "known": "x", "text": "{}"}]},  # a false alarm on a correctly paid claim
           "a10_underpay": {}}  # the underpayment is missed
    monkeypatch.setattr(score, "_decisions", lambda _run: dec)
    sc = score.score(run)
    assert sc["problems"] == 3 and sc["found"] == 2
    assert [m["claim"] for m in sc["by_class"]["underpaid"]["missed"]] == ["C"]
    assert [a["claim"] for a in sc["false_alarms"]] == ["D"]
    assert sc["by_class"]["denied_deviation"]["recognized"] == 1 and sc["agents_read_the_knowledge_book"] is False
    assert sc["by_class"]["paid_clean"]["n"] == 2


@pytest.mark.slow
def test_a_real_streamed_run_scores_reconciles_and_writes_its_reports(tmp_path):
    out = tmp_path / "r"
    run_stream(out, StreamConfig(count=14, per_day=7, deny_rate=0.3, deviation_rate=0.4, serve=False, bots=False), FakeEmr(), log=lambda *_: None)
    sc = score.write_reports(out)
    assert sc["ledger"]["tie_out_mismatches"] == [] and sc["ledger"]["cash_collected"] == "0.00"
    assert sc["coding"]["auto_wrong"] == [] and sc["coding"]["problem_missed"] == []
    assert sc["found"] <= sc["problems"] and (out / "scorecard.html").exists() and (out / "ledger.csv").exists()
    assert "Cash collected: 0.00" in (out / "scorecard.html").read_text("utf-8")
    from krisnai.live.export import build

    data = build(out)
    assert len(data["claims"]) == 14 and len(data["book"]) == 10 and data["ledger"]["cash_collected"] == "0.00"
    paid = [c for c in data["claims"] if c["payer"]]
    assert paid and all(c["payer"]["claim_id"] == c["claim"] and c["events"] for c in paid), "each claim carries its truth row and its timeline"
    assert all(c["coding"]["checks"] for c in data["claims"] if c["coding"])
