"""Valley loader tests. A small SQLite database with Valley's table and column names stands in for the
PostgreSQL original; one live smoke test runs only with KRISNAI_VALLEY_CONFIG set."""

from __future__ import annotations

import os
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

import krisnai.model as m
from krisnai.ingest.valley import load_valley
from krisnai.model import Base, tenant_session

SALT = "valley-salt"

SCHEMA = """
create table edi_837p_header (source_file text, interchange_control_number text, group_control_number text,
  transaction_control_number text, interchange_date text, transaction_date text);
create table edi_837p_billing_provider (source_file text, hl_id text, npi text, tax_id text, last_name_or_org text);
create table edi_837p_subscriber (source_file text, hl_id text, member_id text);
create table edi_837p_payer (source_file text, claim_context_hl_id text, name text, payer_id text);
create table edi_837p_claims (source_file text, claim_number text, claim_seq integer, billing_hl_id text,
  subscriber_hl_id text, total_charge_amount text, place_of_service_code text, frequency_code text,
  claim_service_date_start text);
create table edi_837p_service_lines (source_file text, claim_number text, line_seq integer, line_number text,
  procedure_code text, modifiers text, line_charge_amount text, unit_measure text, service_units text,
  diagnosis_pointers text, service_date text);
create table edi_837p_diagnosis_codes (source_file text, claim_number text, sequence text, qualifier text, code text);
create table edi_835_payment_header (source_file text, interchange_control_number text, group_control_number text,
  transaction_control_number text, interchange_date text, total_payment_amount text, credit_debit_flag text,
  payment_method text, payment_date text, trace_number text, payer_id text);
create table edi_835_payer (source_file text, name text, payer_id text);
create table edi_835_provider_adjustments (id integer primary key, source_file text, provider_id text,
  fiscal_period_date text, adjustment_reason_code text, reference_id text, amount text);
create table edi_835_claims (source_file text, claim_number text, claim_seq integer, claim_status_code text,
  total_charge_amount text, total_paid_amount text, patient_responsibility_amount text,
  claim_filing_indicator_code text, payer_claim_control_number text);
create table edi_835_service_payments (source_file text, claim_number text, line_seq integer, procedure_code text,
  modifiers text, line_charge_amount text, line_paid_amount text, units_paid text, service_date text);
create table edi_835_adjustments (id integer primary key, source_file text, claim_number text, line_seq text,
  group_code text, reason_code text, amount text, quantity text, remark_code text, remark_code_2 text,
  remark_qualifier text);
create table edi_835_amounts (source_file text, claim_number text, line_seq text, qualifier text, amount text);
create table edi_835_claim_parties (source_file text, claim_number text, role_code text, id_code text);
create table edi_835_dates (source_file text, claim_number text, line_seq text, qualifier text, raw_value text);
"""

F837, F835 = "VW_837P_20250106.8", "VW_835_COM_UHC_2025"


def valley_db(path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(path)
    c.executescript(SCHEMA)
    ins = lambda sql, rows: c.executemany(sql, rows)  # noqa: E731
    ins(
        "insert into edi_837p_header values (?,?,?,?,?,?)",
        [(F837, "100000001", "100000001", "0000001", "250106", "20250106")],
    )
    ins(
        "insert into edi_837p_billing_provider values (?,?,?,?,?)",
        [(F837, "5", "1700675790", "499849470", "FIREPIT MEDICAL")],
    )
    ins(
        "insert into edi_837p_subscriber values (?,?,?)",
        [(F837, "1001", "MEM1"), (F837, "1002", "MEM2"), (F837, "1003", "MEM3")],
    )
    ins(
        "insert into edi_837p_payer values (?,?,?,?)",
        [(F837, "1001", "AETNA", "60054"), (F837, "1002", "AETNA", "60054")],
    )
    ins(
        "insert into edi_837p_claims values (?,?,?,?,?,?,?,?,?)",
        [
            (F837, "C1", 1, "5", "1001", "193.09", "11", "1", "20250101"),
            (F837, "C2", 2, "5", "1002", "100.00", "22", "1", "20250102"),
            (F837, "C3", 3, "5", "1003", "50.00", "11", "1", "20250103"),  # subscriber has no payer row -> skipped
            (F837, "C4", 4, "5", "1001", "12x", "11", "1", "20250104"),  # bad amount -> skipped
        ],
    )
    ins(
        "insert into edi_837p_service_lines values (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (F837, "C1", 1, "1", "99213", "25:GT", "150.44", "UN", "1", "1:2", "20250101"),
            (F837, "C1", 2, "2", "97110", None, "42.65", "UN", "2", "1", "20250101"),
            (F837, "C2", 1, "1", "99214", None, "100.00", "UN", "1", "1", "20250102"),
        ],
    )
    ins(
        "insert into edi_837p_diagnosis_codes values (?,?,?,?,?)",
        [(F837, "C1", "1", "ABK", "N390"), (F837, "C1", "2", "ABF", "E039"), (F837, "C2", "1", "ABK", "I10")],
    )
    ins(
        "insert into edi_835_payment_header values (?,?,?,?,?,?,?,?,?,?,?)",
        [(F835, "300000057", "300000056", "0001", "250208", "93.00", "C", "ACH", "20250208", "TRN123", "9999999999")],
    )
    ins("insert into edi_835_payer values (?,?,?)", [(F835, "AETNA", "60054")])
    ins(
        "insert into edi_835_provider_adjustments (source_file, provider_id, fiscal_period_date, adjustment_reason_code, reference_id, amount) values (?,?,?,?,?,?)",
        [(F835, "1700675790", "20250131", "WO", "R9", "-3.50")],
    )
    ins(
        "insert into edi_835_claims values (?,?,?,?,?,?,?,?,?)",
        [
            (F835, "C1", 1, "1", "193.09", "93.00", "10.00", "CI", "PCN1"),
            (F835, "C9", 2, "4", "75.00", "0", "0", "CI", "PCN9"),  # remit with no 837 claim loaded (orphan)
        ],
    )
    ins(
        "insert into edi_835_service_payments values (?,?,?,?,?,?,?,?,?)",
        [
            (F835, "C1", 1, "99213", "25:GT", "150.44", "70.00", "1", "20250101"),
            (F835, "C1", 2, "97110", None, "42.65", "23.00", "2", "20250101"),
            (F835, "C9", 1, "99212", None, "75.00", "0", "0", "20250105"),
        ],
    )
    ins(
        "insert into edi_835_adjustments (source_file, claim_number, line_seq, group_code, reason_code, amount, quantity, remark_code, remark_code_2, remark_qualifier) values (?,?,?,?,?,?,?,?,?,?)",
        [
            (F835, "C1", "1", "CO", "45", "70.44", None, "N130", "MA01", "HE"),
            (F835, "C1", "1", "PR", "2", "10.00", None, None, None, None),
            (F835, "C1", "2", "CO", "45", "19.65", None, None, None, None),
            (F835, "C9", "1", "CO", "16", "75.00", None, "MA130", None, "HE"),
        ],
    )
    ins(
        "insert into edi_835_amounts values (?,?,?,?,?)",
        [(F835, "C1", "1", "B6", "80.00"), (F835, "C1", "2", "B6", "23.00"), (F835, "C1", "1", "AU", "1")],
    )
    ins("insert into edi_835_claim_parties values (?,?,?,?)", [(F835, "C1", "QC", "MEM1"), (F835, "C1", "IL", "OTHER")])
    ins(
        "insert into edi_835_dates values (?,?,?,?,?)",
        [
            (F835, "C1", None, "232", "20250101"),
            (F835, "C1", "1", "472", "20250101"),
            (F835, "C1", None, "050", "20250120"),
        ],
    )
    c.commit()
    return c


@pytest.fixture
def env(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'k.db'}")

    @event.listens_for(eng, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(m.Tenant(name="V", patient_salt_key="SALT_V"))
        s.commit()
    return eng, valley_db(tmp_path / "valley.db")


def test_loads_claims_remits_and_reports_skipped_rows(env):
    eng, conn = env
    report = load_valley(eng, 1, SALT, conn, n_837_files=1)
    assert report.count("loaded") == 2 and report.count("skipped") == 0
    assert sum(report.skipped_rows.values()) == 2
    assert any("missing provider/subscriber/payer" in k for k in report.skipped_rows)
    assert any("bad amount" in k for k in report.skipped_rows)
    with tenant_session(eng, 1) as s:
        assert [c.claim_submitter_id for c in s.scalars(select(m.Claim).order_by(m.Claim.claim_submitter_id))] == [
            "C1",
            "C2",
        ]
        c1 = s.scalars(select(m.Claim).where(m.Claim.claim_submitter_id == "C1")).one()
        assert c1.total_charge == Decimal("193.09") and c1.service_date.isoformat() == "2025-01-01"
        lines = s.scalars(
            select(m.ClaimLine).where(m.ClaimLine.claim_id == c1.id).order_by(m.ClaimLine.line_number)
        ).all()
        assert [(ln.cpt, ln.modifier_1, ln.modifier_2, ln.units) for ln in lines] == [
            ("99213", "25", "GT", Decimal("1")), ("97110", None, None, Decimal("2"))
        ]  # fmt: skip
        dx = s.scalars(select(m.ClaimDx).where(m.ClaimDx.claim_id == c1.id).order_by(m.ClaimDx.seq)).all()
        assert [(d.dx_qualifier, d.dx_code) for d in dx] == [("ABK", "N390"), ("ABF", "E039")]
        ev = s.get(m.Event, c1.event_id)
        assert (ev.isa13, ev.gs06, ev.st02) == ("100000001", "100000001", "0000001")  # Valley's real control numbers


def test_remit_side_converts_text_to_exact_types(env):
    eng, conn = env
    load_valley(eng, 1, SALT, conn, n_837_files=1)
    with tenant_session(eng, 1) as s:
        pay = s.scalars(select(m.Payment)).one()
        assert pay.trace_number == "TRN123" and pay.payment_amount == Decimal("93.00")
        assert pay.payment_date.isoformat() == "2025-02-08"
        plb = s.scalars(select(m.PlbAdjustment)).one()
        assert plb.amount == Decimal("-3.50") and plb.reason_code == "WO"
        remits = {r.claim_submitter_id: r for r in s.scalars(select(m.Remit))}
        assert set(remits) == {"C1", "C9"}  # the orphan remit is loaded too
        r1 = remits["C1"]
        assert r1.total_paid == Decimal("93.00") and r1.service_date.isoformat() == "2025-01-01" and r1.patient_ref_id
        line1 = s.scalars(select(m.RemitLine).where(m.RemitLine.remit_id == r1.id, m.RemitLine.line_number == 1)).one()
        assert line1.allowed_amount == Decimal("80.00") and line1.modifier_2 == "GT" and line1.service_date
        adj = s.scalars(select(m.Adjustment).where(m.Adjustment.remit_line_id == line1.id)).all()
        assert sorted((a.group_code, a.reason_code, a.amount) for a in adj) == [
            ("CO", "45", Decimal("70.44")),
            ("PR", "2", Decimal("10.00")),
        ]
        marks = s.scalars(select(m.RemitRemark.remark_code).where(m.RemitRemark.remit_line_id == line1.id)).all()
        assert sorted(marks) == ["MA01", "N130"]
        for line in s.scalars(select(m.RemitLine)):
            total_adj = sum(
                a.amount for a in s.scalars(select(m.Adjustment).where(m.Adjustment.remit_line_id == line.id))
            )
            assert line.charge == line.paid + total_adj  # lines balance exactly


def test_same_member_hashes_to_one_patient_across_837_and_835(env):
    eng, conn = env
    load_valley(eng, 1, SALT, conn, n_837_files=1)
    with tenant_session(eng, 1) as s:
        c1 = s.scalars(select(m.Claim).where(m.Claim.claim_submitter_id == "C1")).one()
        r1 = s.scalars(select(m.Remit).where(m.Remit.claim_submitter_id == "C1")).one()
        assert c1.patient_ref_id == r1.patient_ref_id  # M3 can use this as a matching hint
        assert "MEM1" not in " ".join(s.scalars(select(m.Event.payload)))


def test_reload_is_idempotent_and_valley_is_never_written(env):
    eng, conn = env
    load_valley(eng, 1, SALT, conn, n_837_files=1)
    before = conn.execute("select count(*) from edi_835_claims").fetchone()
    with tenant_session(eng, 1) as s:
        n = s.scalar(select(func.count()).select_from(m.Event))
    again = load_valley(eng, 1, SALT, conn, n_837_files=1)
    assert again.count("loaded") == 0 and again.count("skipped") == 2
    with tenant_session(eng, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.Event)) == n
    assert conn.execute("select count(*) from edi_835_claims").fetchone() == before


def test_remit_files_are_only_those_touching_loaded_claims(env):
    eng, conn = env
    conn.execute(
        "insert into edi_835_payment_header values ('OTHER_835','1','1','0001','250301','1','C','NON','20250301','T','x')"
    )
    conn.execute("insert into edi_835_payer values ('OTHER_835','X','1')")
    conn.execute("insert into edi_835_claims values ('OTHER_835','ZZ','1','1','1','1','0','CI','P')")
    conn.commit()
    load_valley(eng, 1, SALT, conn, n_837_files=1)
    with tenant_session(eng, 1) as s:
        assert "ZZ" not in s.scalars(select(m.Remit.claim_submitter_id)).all()


@pytest.mark.skipif(
    not os.environ.get("KRISNAI_VALLEY_CONFIG"), reason="live RDS smoke test: set KRISNAI_VALLEY_CONFIG"
)
def test_live_valley_smoke(tmp_path):
    from krisnai.ingest.valley import connect_readonly

    eng = create_engine(f"sqlite:///{tmp_path / 'live.db'}")
    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add(m.Tenant(name="V", patient_salt_key="X"))
        s.commit()
    conn = connect_readonly(Path(os.environ["KRISNAI_VALLEY_CONFIG"]))
    try:
        report = load_valley(eng, 1, SALT, conn, n_837_files=1, max_835_files=20)
    finally:
        conn.close()
    assert report.count("loaded") >= 2
    with tenant_session(eng, 1) as s:
        assert s.scalar(select(func.count()).select_from(m.Claim)) > 0
        assert s.scalar(select(func.count()).select_from(m.Remit)) > 0
