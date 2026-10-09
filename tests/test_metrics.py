"""M4 tests: every KPI against the hand-built book in tests/fixtures/tiny_book.py (numbers checkable by eye)."""

from __future__ import annotations

import io
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command

from krisnai import cli
from krisnai.ingest.loader import ingest_path
from krisnai.match import run_matching
from krisnai.metrics import compute, compute_all, function_ddl, kpi_names, render
from tests.fixtures import make_synthetic as ms
from tests.fixtures.tiny_book import Book, build_tiny_book
from tests.test_ingest import SALT, make_engine
from tests.test_model import _alembic_cfg

JUN30 = date(2026, 6, 30)
AUG31 = date(2026, 8, 31)


def close(value, expected, places=5):
    assert value is not None, f"expected {expected}, got NULL"
    assert abs(float(value) - float(expected)) < 10**-places, f"{value} != {expected}"


@pytest.fixture(scope="module")
def eng(tmp_path_factory):
    engine = make_engine(tmp_path_factory.mktemp("m4") / "db.sqlite")
    build_tiny_book(engine, 1, "a")
    return engine


def one(eng, kpi, as_of=JUN30, tenant=1):
    rows = compute(eng, tenant, kpi, as_of)
    assert len(rows) == 1, rows
    return rows[0]


# Known by 06-30: C1 C2 C3 C4 C5 C7 C8 = 7 claims (C6 was submitted 07-14). First remits: C1 C2 C3 C7 = 4.


def test_clean_claim_rate(eng):
    r = one(eng, "clean_claim_rate")
    assert (r["submitted_claims"], r["clean_claims"]) == (7, 6)  # only C4 was rejected
    close(r["clean_claim_rate"], 6 / 7)


def test_rejection_rate(eng):
    r = one(eng, "rejection_rate")
    assert (r["submitted_claims"], r["rejected_by_277ca"], r["rejected_by_999"], r["rejected_claims"]) == (7, 1, 0, 1)
    close(r["rejection_rate"], 1 / 7)


def test_first_pass_paid_rate(eng):
    r = one(eng, "first_pass_paid_rate")
    assert (r["adjudicated_claims"], r["first_pass_paid_claims"]) == (4, 3)  # C3 was denied
    close(r["first_pass_paid_rate"], 3 / 4)


def test_denial_rate_overall_by_payer_carc_and_cpt(eng):
    rows = {(r["dimension"], r["dim_key"]): r for r in compute(eng, 1, "denial_rate", JUN30)}
    overall = rows[("overall", "all")]
    assert (overall["denied_claims"], overall["adjudicated_claims"]) == (1, 4)
    assert (overall["denied_charge"], overall["adjudicated_charge"]) == (150, 510)  # 150*3 + 60
    close(overall["denial_rate_count"], 1 / 4)
    close(overall["denial_rate_dollars"], 150 / 510)
    close(rows[("payer", "P1")]["denial_rate_count"], 0)  # C1 C2 C7 all paid
    close(rows[("payer", "P2")]["denial_rate_count"], 1)  # C3 is P2's only adjudicated claim
    carc = rows[("carc", "16")]
    assert (carc["denied_claims"], carc["denied_charge"]) == (1, 150)
    close(carc["denial_rate_count"], 1 / 4)  # share of all adjudicated claims
    cpt = rows[("cpt", "99213")]
    assert (cpt["denied_claims"], cpt["denied_charge"]) == (1, 150)
    assert ("carc", "45") not in rows  # the contractual CARC on paid claims is not a denial reason


def test_days_in_ar(eng):
    r = one(eng, "days_in_ar")
    assert (r["open_ar"], r["charges_last_90_days"]) == (
        200,
        860,
    )  # open: C5 150 + C8 50. billed since 04-01: 150*5 + 60 + 50
    close(r["days_in_ar"], 200 / (860 / 90))


def test_ar_over_90(eng):
    r = one(eng, "ar_over_90")
    assert (r["open_ar"], r["ar_over_90"]) == (200, 150)  # C5 is 171 days old, C8 is 20
    close(r["ar_over_90_share"], 150 / 200)


def test_net_collection_rate(eng):
    r = one(eng, "net_collection_rate")
    # claims with a remit: C1 C2 C3 C7. charges 510. contractual (CO 45) 50 + 70 = 120; C3's CO 16 is not contractual.
    assert (r["claims"], r["charges"], r["contractual"]) == (4, 510, 120)
    assert (r["payments"], r["patient_responsibility"]) == (208, 32)  # 90 + 70 + 48; 10 + 10 + 12
    close(r["net_collection_rate"], 208 / (510 - 120))
    close(r["net_collection_rate_with_patient_share"], (208 + 32) / (510 - 120))


def test_underpayment(eng):
    r = one(eng, "underpayment")
    # paid lines C1 C2 C7. C1: 100 allowed vs 90 + 10 = ok. C2: 100 vs 70 + 10 = 20 short. C7 has no fee row.
    assert (r["paid_lines"], r["lines_without_fee"], r["underpaid_lines"]) == (3, 1, 1)
    assert r["underpayment_amount"] == Decimal("20")


def test_charge_lag(eng):
    r = one(eng, "charge_lag")
    # Jan 10 -> Jun 1 is 142 days for C1-C5, C7 is May 20 -> Jun 1 = 12, C8 is Jun 10 -> Jun 12 = 2
    assert r["claims"] == 7
    close(r["avg_charge_lag_days"], (5 * 142 + 12 + 2) / 7)


def test_as_of_is_point_in_time(eng):
    """Two months later C6 is known and C5 has been paid; the 06-30 numbers above did not change."""
    assert one(eng, "clean_claim_rate", AUG31)["submitted_claims"] == 8
    fp = one(eng, "first_pass_paid_rate", AUG31)
    assert (fp["adjudicated_claims"], fp["first_pass_paid_claims"]) == (5, 4)  # C5 paid on 08-01
    ar = one(eng, "days_in_ar", AUG31)
    assert ar["open_ar"] == 200  # C5 is paid now (-150), C6 appears (+150); C8 still open
    close(one(eng, "net_collection_rate", AUG31)["payments"], 298)  # 208 + C5's 90
    assert one(eng, "first_pass_paid_rate", JUN30)["adjudicated_claims"] == 4  # recomputed as of 06-30 again


def test_zero_denominators_return_null_not_zero(eng):
    before_anything = date(2025, 12, 31)
    for kpi, col in [("clean_claim_rate", "clean_claim_rate"), ("rejection_rate", "rejection_rate"),
                     ("first_pass_paid_rate", "first_pass_paid_rate"), ("days_in_ar", "days_in_ar"),
                     ("ar_over_90", "ar_over_90_share"), ("net_collection_rate", "net_collection_rate"),
                     ("charge_lag", "avg_charge_lag_days")]:  # fmt: skip
        assert one(eng, kpi, before_anything)[col] is None, kpi
    assert one(eng, "underpayment", before_anything)["underpayment_amount"] == 0


def test_a_999_rejection_counts(tmp_path):
    engine = make_engine(tmp_path / "n.sqlite")
    b = Book(engine, 1)
    b.claim("X1", "P1", "100.00", date(2026, 6, 1), date(2026, 6, 2))
    b.claim("X2", "P1", "100.00", date(2026, 6, 1), date(2026, 6, 2))
    b.ack_999("X1", "R", date(2026, 6, 3))
    b.commit()
    r = one(engine, "rejection_rate")
    assert (r["submitted_claims"], r["rejected_by_999"], r["rejected_claims"]) == (2, 1, 1)
    assert one(engine, "days_in_ar")["open_ar"] == 100  # the rejected claim is not AR


def test_other_tenants_do_not_change_the_numbers(tmp_path):
    engine = make_engine(tmp_path / "t.sqlite")
    build_tiny_book(engine, 1, "a")
    alone = compute_all(engine, 1, JUN30)
    build_tiny_book(engine, 2, "b")  # tenant 2 gets the same book
    assert compute_all(engine, 1, JUN30) == alone
    assert compute_all(engine, 2, JUN30) == alone  # and sees only its own copy, not double


def test_dictionary_documents_every_kpi_and_every_kpi_has_a_function():
    doc = (Path(__file__).parent.parent / "docs" / "metrics.md").read_text(encoding="utf8")
    for kpi in kpi_names():
        assert f"`{kpi}`" in doc, f"{kpi} is missing from docs/metrics.md"
        assert f"`krisnai/metrics/sql/{kpi}.sql`" in doc
    assert len(kpi_names()) == 9


def test_sql_server_text_uses_datediff_and_parameters_not_sqlite_functions():
    for kpi in kpi_names():
        sql = render(kpi, "mssql")
        assert "julianday" not in sql and "{" not in sql and ":as_of" not in sql and ":tenant_id" not in sql, kpi
        ddl = function_ddl(kpi)
        assert ddl.startswith(f"CREATE OR ALTER FUNCTION metrics.fn_{kpi} (@as_of DATE, @tenant_id BIGINT)")
    assert "DATEDIFF(day," in render("days_in_ar", "mssql")


def test_migration_0002_emits_one_function_per_kpi():
    import os

    os.environ.pop("KRISNAI_ALEMBIC_URL", None)
    buf = io.StringIO()
    command.upgrade(_alembic_cfg(buf), "head", sql=True)
    sql = buf.getvalue()
    assert "CREATE SCHEMA metrics" in sql
    for kpi in kpi_names():
        assert re.search(rf"CREATE OR ALTER FUNCTION metrics\.fn_{kpi} ", sql), kpi


def test_cli_metrics(eng, capsys):
    url = str(eng.url)
    assert cli.main(["--db-url", url, "metrics", "--tenant", "1", "--as-of", "2026-06-30", "--kpi", "underpayment",
                     "--json"]) == 0  # fmt: skip
    assert Decimal(json.loads(capsys.readouterr().out)["underpayment"][0]["underpayment_amount"]) == 20
    assert cli.main(["--db-url", url, "metrics", "--tenant", "1", "--as-of", "2026-06-30"]) == 0
    assert "days_in_ar (as of 2026-06-30)" in capsys.readouterr().out


def test_synthetic_set_agrees_with_the_planted_ground_truth(tmp_path):
    import csv

    ms.generate(tmp_path / "data", seed=5, n_claims=200)
    engine = make_engine(tmp_path / "s.sqlite")
    ingest_path(engine, 1, tmp_path / "data", SALT)
    run_matching(engine, 1)
    with open(tmp_path / "data" / "ground_truth.csv", newline="", encoding="utf8") as f:
        truth = list(csv.DictReader(f))
    n = lambda kind: sum(1 for g in truth if g["issue_type"] == kind)  # noqa: E731
    asof = ms.AS_OF
    assert one(engine, "rejection_rate", asof)["rejected_claims"] == n("rejection")
    denial = {(r["dimension"], r["dim_key"]): r for r in compute(engine, 1, "denial_rate", asof)}
    assert denial[("overall", "all")]["denied_claims"] == n("denial") + n("timely_filing")
    short = sum(Decimal(g["expected_amount"]) for g in truth if g["issue_type"] == "underpayment")
    got = one(engine, "underpayment", asof)
    assert got["underpaid_lines"] == n("underpayment")
    close(got["underpayment_amount"], short, places=1)
