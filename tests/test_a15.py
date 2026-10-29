"""M5 tests: the A15-lite leakage diagnostic on the synthetic set, hand-built cases, G0, read-only and tenancy."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import pytest
from openpyxl import load_workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import krisnnai.model as m
from krisnnai import cli
from krisnnai.agents.a15_lite import A15Config, G0Error, detect, format_scores, load_snapshot, run_a15
from krisnnai.agents.a15_lite.config import UNBILLED_VISIT
from krisnnai.ingest.loader import ingest_path
from krisnnai.match import run_matching
from krisnnai.model import Base, tenant_session
from tests.fixtures import make_synthetic as ms
from tests.fixtures.tiny_book import Book
from tests.test_ingest import SALT, make_engine

AS_OF = ms.AS_OF
D = Decimal


@pytest.fixture(scope="module")
def syn(tmp_path_factory):
    root = tmp_path_factory.mktemp("a15")
    ms.generate(root / "data", seed=5, n_claims=200)
    engine = make_engine(root / "db.sqlite")
    ingest_path(engine, 1, root / "data", SALT)
    run_matching(engine, 1)
    return {"root": root, "engine": engine, "truth": root / "data" / "ground_truth.csv"}


def by_key(findings):
    return {f.key: f for f in findings}


# ------------------------------------------------------------------------------------ synthetic ground truth


def test_finds_the_planted_issues_with_the_right_type_dollars_and_status(syn, capsys):
    res = run_a15(syn["engine"], 1, AS_OF, syn["root"] / "out", ground_truth=syn["truth"])
    table = format_scores(res.scores)
    print("\n" + table)  # shown with pytest -s
    assert {"denial", "timely_filing", "underpayment", "rejection", "unbilled_visit"} <= set(res.scores)
    for kind, sc in res.scores.items():
        assert sc.precision >= 0.95 and sc.recall >= 0.95, table
        assert sc.correct_recall >= 0.95, f"{kind}: dollars or status wrong\n{table}"
    assert "unexplained_adjustment" not in {f.type for f in res.findings}  # nothing planted, nothing reported
    assert res.report["reconciliation"]["passed"]


def test_every_finding_names_an_agent_a_basis_and_a_status(syn):
    res = run_a15(syn["engine"], 1, AS_OF, syn["root"] / "out2")
    assert res.findings
    for f in res.findings:
        assert f.agent in {"A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A10"}
        assert f.basis == "fee_schedule" and f.status in ("recoverable", "structural") and f.expected_amount >= 0
    assert all(f.deadline is None for f in res.findings if f.type == "timely_filing")


def test_json_and_excel_agree(syn):
    res = run_a15(syn["engine"], 1, AS_OF, syn["root"] / "out3")
    data = json.loads(res.json_path.read_text())
    wb = load_workbook(res.xlsx_path)
    assert wb.sheetnames == ["Summary", "By payer", "By CPT", "By location", "By provider", "Recoverable vs structural",
                             "Opportunities", "Baseline KPIs", "Reconciliation"]  # fmt: skip
    summary = {row[0].value: row[1].value for row in wb["Summary"].iter_rows() if row[0].value}
    assert D(str(summary["Recoverable $ (detected)"])) == D(data["summary"]["recoverable"])
    assert summary["Findings"] == data["summary"]["findings"] == len(wb["Opportunities"]["A"]) - 1
    assert "not recovered" in data["note"]
    total = sum(D(r["total"]) for r in data["by_payer"])
    assert total == D(data["summary"]["recoverable"]) + D(data["summary"]["structural"])
    assert wb["Reconciliation"].max_row == 1 + len(data["reconciliation"]["checks"])
    top = wb["Opportunities"]
    statuses = [top.cell(row=r, column=3).value for r in range(2, top.max_row + 1)]
    assert statuses == sorted(statuses, key=lambda s: s != "recoverable")  # recoverable ranked first


def test_report_holds_no_patient_identifiers(syn):
    res = run_a15(syn["engine"], 1, AS_OF, syn["root"] / "out4")
    text = res.json_path.read_text()
    with open(syn["root"] / "data" / "visits.csv", encoding="utf8") as f:
        members = {line.split(",")[3] for line in list(f)[1:]}
    assert not any(member in text for member in members)


# -------------------------------------------------------------------------------- G0, read-only, tenancy


def row_counts(engine):
    with Session(engine) as s:
        return {t.name: s.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables}


def test_run_changes_no_data(syn):
    before = row_counts(syn["engine"])
    run_a15(syn["engine"], 1, AS_OF, syn["root"] / "ro")
    assert row_counts(syn["engine"]) == before


def test_g0_stops_the_report_when_totals_do_not_reconcile(tmp_path):
    ms.generate(tmp_path / "data", seed=5, n_claims=60)
    engine = make_engine(tmp_path / "g.sqlite")
    ingest_path(engine, 1, tmp_path / "data", SALT)
    run_matching(engine, 1)
    with tenant_session(engine, 1) as s:
        s.scalars(select(m.Remit)).first().total_paid += D("5.00")
        s.commit()
    out = tmp_path / "out"
    with pytest.raises(G0Error, match="remit_paid|payment_total"):
        run_a15(engine, 1, AS_OF, out)
    assert not out.exists(), "no report may be written when G0 fails"
    run_a15(engine, 1, AS_OF, tmp_path / "wide", A15Config(g0_tolerance=D("5.00")))  # tolerance is configurable
    assert (tmp_path / "wide" / "a15_lite.json").exists()


def test_g0_fails_when_remits_are_not_matched_yet(tmp_path):
    ms.generate(tmp_path / "data", seed=5, n_claims=40)
    engine = make_engine(tmp_path / "u.sqlite")
    ingest_path(engine, 1, tmp_path / "data", SALT)  # no `krisnnai match`
    with pytest.raises(G0Error, match="remit_match_rate"):
        run_a15(engine, 1, AS_OF, tmp_path / "out")


def test_another_tenants_data_never_reaches_the_report(syn, tmp_path):
    alone = len(run_a15(syn["engine"], 1, AS_OF, tmp_path / "a").findings)
    ingest_path(syn["engine"], 2, syn["root"] / "data", SALT)
    run_matching(syn["engine"], 2)
    assert len(run_a15(syn["engine"], 1, AS_OF, tmp_path / "b").findings) == alone
    assert len(run_a15(syn["engine"], 2, AS_OF, tmp_path / "c").findings) == alone  # its own copy, not doubled


def test_cli_prints_the_scores_and_stops_with_code_2_on_g0(syn, tmp_path, capsys):
    url = str(syn["engine"].url)
    args = ["--db-url", url, "a15", "--tenant", "1", "--as-of", "2026-06-30", "--out", str(tmp_path / "o"),
            "--ground-truth", str(syn["truth"])]  # fmt: skip
    assert cli.main(args) == 0
    out = capsys.readouterr().out
    assert "findings detected" in out and "all planted issues" in out


# ------------------------------------------------------------------------------------- hand-built cases


def snapshot_of(engine, as_of):
    return load_snapshot(engine, 1, as_of)


@pytest.fixture()
def small(tmp_path):
    engine = make_engine(tmp_path / "s.sqlite")
    b = Book(engine, 1)
    b.fee("P1", "99213", "100.00")
    jan = date(2026, 1, 1)
    # K1 teaches the patient share: 10 of 100 allowed
    k1 = b.claim("K1", "P1", "150.00", jan, jan)
    pay = b.payment("P1", jan, "T1", "90.00")
    b.remit(pay, k1, "1", "90.00", "10.00", [("CO", "45", "50.00"), ("PR", "2", "10.00")])
    # D1 denied (CARC 16), D2 coverage (27), D3 timely filing (29), all paid out on Jan 1
    for sid, carc in (("D1", "16"), ("D2", "27"), ("D3", "29")):
        c = b.claim(sid, "P1", "150.00", jan, jan)
        b.remit(pay, c, "4", "0.00", "0.00", [("CO", carc, "150.00")])
    # fallback: 97110 has no fee row. Median received is 100; F4 got 50, F5 got 90.
    for sid, paid, pr in (("F1", "80.00", "20.00"), ("F2", "80.00", "20.00"), ("F3", "80.00", "20.00"),
                          ("F4", "40.00", "10.00"), ("F5", "72.00", "18.00")):  # fmt: skip
        c = b.claim(sid, "P1", "150.00", jan, jan, cpt="97110")
        b.remit(pay, c, "1", paid, pr, [("PR", "2", pr)], cpt="97110")
    # U1: paid line with a non-contractual adjustment and no price to compare with
    u = b.claim("U1", "P3", "150.00", jan, jan, cpt="99999")
    b.remit(b.payment("P3", jan, "T3", "85.00"), u, "1", "85.00", "10.00",
            [("CO", "45", "50.00"), ("CO", "253", "5.00"), ("PR", "2", "10.00")], cpt="99999")  # fmt: skip
    # R1: rejected by the 277CA and never answered; V1 visit never billed; V2 visit that was billed
    r = b.claim("R1", "P1", "150.00", jan, jan)
    b.ack_277ca(r, "A3", jan)
    b.visit("V1", "P1", date(2026, 2, 1))
    b.visit("V2", "P1", jan)  # K1..D3 were all billed for this patient on Jan 1 with CPT 99213
    b.commit()
    return engine


def test_denials_carry_category_agent_and_expected_payer_amount(small):
    f = by_key(detect(snapshot_of(small, date(2026, 3, 1))))
    d1 = f[("denial", "D1", None)]
    assert (d1.carc, d1.category, d1.agent) == ("16", "missing_information", "A5")
    assert d1.expected_amount == D("90.00")  # 100 allowed less the 10% share learned from K1
    assert f[("denial", "D2", None)].agent == "A1"  # coverage goes to eligibility
    t = f[("timely_filing", "D3", None)]
    assert (t.status, t.deadline, t.agent) == ("structural", None, "A5")  # always structural


def test_appeal_window_boundary_is_day_180(small):
    on_day = by_key(detect(snapshot_of(small, date(2026, 6, 30))))[("denial", "D1", None)]  # Jan 1 + 180 days
    after = by_key(detect(snapshot_of(small, date(2026, 7, 1))))[("denial", "D1", None)]
    assert (on_day.status, on_day.deadline) == ("recoverable", date(2026, 6, 30))
    assert after.status == "structural"


def test_window_is_configurable_per_payer(small):
    cfg = A15Config(appeal_window_overrides={"P1": 30})
    f = by_key(detect(snapshot_of(small, date(2026, 3, 1)), cfg))
    assert f[("denial", "D1", None)].status == "structural"
    assert by_key(detect(snapshot_of(small, date(2026, 3, 1))))[("denial", "D1", None)].status == "recoverable"


def test_fallback_pricing_is_flagged_and_needs_a_real_shortfall(small):
    under = [f for f in detect(snapshot_of(small, date(2026, 3, 1))) if f.type == "underpayment"]
    assert [(f.claim, f.basis, f.expected_amount) for f in under] == [("F4", "fallback", D("50.00"))]
    # F5 is 10 below the median, under the 20% floor; K1 matches its contract; F1-F3 sit at the median


def test_unexplained_adjustment_on_a_paid_line(small):
    f = [x for x in detect(snapshot_of(small, date(2026, 3, 1))) if x.type == "unexplained_adjustment"]
    assert [(x.claim, x.carc, x.expected_amount, x.agent) for x in f] == [("U1", "253", D("5.00"), "A7")]


def test_rejection_and_unbilled_visit(small):
    f = by_key(detect(snapshot_of(small, date(2026, 3, 1))))
    r1 = f[("rejection", "R1", None)]
    assert (r1.agent, r1.expected_amount, r1.status) == ("A6", D("90.00"), "recoverable")
    v1 = f[(UNBILLED_VISIT, "V1", None)]
    assert (v1.agent, v1.expected_amount) == ("A3", D("90.00"))
    assert (UNBILLED_VISIT, "V2", None) not in f  # a claim exists for that patient, date and CPT
    far = by_key(detect(snapshot_of(small, date(2027, 6, 1))))
    assert far[(UNBILLED_VISIT, "V1", None)].status == "structural"  # more than 365 days after the visit


def test_nothing_after_the_as_of_date_is_used(small):
    assert detect(snapshot_of(small, date(2025, 12, 31))) == []
