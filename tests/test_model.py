"""M1 tests: core data model, tenant isolation, idempotency keys, migration and docs."""

from __future__ import annotations

import io
import os
import re
from datetime import date
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Date, Float, create_engine, event, select
from sqlalchemy.dialects import mssql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

import krisnai.model as m
from krisnai.model import docgen
from krisnai.model.base import Base
from krisnai.model.scoping import TenantMismatchError, tenant_session

TABLES = Base.metadata.tables
ENGINE_TABLES = (
    "policy", "decision_record", "approval_request", "carc_route", "payer_appeal_window",
    "ncci_pair", "mue_limit", "payer_filing_window", "rejection_route",
)  # fmt: skip
EXPECTED_TABLES = {
    "tenant", "source_file", "event", "payer", "provider", "patient_ref", "claim", "claim_line",
    "claim_dx", "ack_999", "ack_277ca", "remit", "remit_line", "adjustment", "remit_remark",
    "plb_adjustment", "payment", "fee_schedule", "ar_snapshot", "visit",
    "policy", "decision_record", "approval_request", "carc_route", "payer_appeal_window",
    "ncci_pair", "mue_limit", "payer_filing_window", "rejection_route", "visit_note", "charge",
}  # fmt: skip


@pytest.fixture
def engine():
    eng = create_engine("sqlite://")

    @event.listens_for(eng, "connect")
    def _fk_on(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(eng)
    with Session(eng) as s:
        s.add_all([m.Tenant(name="Tenant A", patient_salt_key="SALT_A"),
                   m.Tenant(name="Tenant B", patient_salt_key="SALT_B")])  # fmt: skip
        s.commit()
    return eng


def load_file(eng, tenant_id, sha="a" * 64):
    with tenant_session(eng, tenant_id) as s:
        f = m.SourceFile(file_name="x.x12", file_sha256=sha, file_type="837P", byte_size=1, status="loaded")
        s.add(f)
        s.commit()
        return f.id


def test_all_planned_tables_exist():
    assert set(TABLES) == EXPECTED_TABLES


def test_every_table_is_tenant_scoped_with_lineage():
    for name, t in TABLES.items():
        if name == "tenant":
            continue
        cols = set(t.columns.keys())
        assert {"tenant_id", "loaded_at"} <= cols, name
        if name not in (
            "source_file",
            *ENGINE_TABLES,
        ):  # engine tables are produced by the engine, not loaded from a file
            assert "source_file_id" in cols, name


def test_no_float_columns_and_dates_are_dates():
    for t in TABLES.values():
        for c in t.columns:
            assert not isinstance(c.type, Float), f"{t.name}.{c.name} is float"
            if c.name.endswith("_date") or c.name in ("service_date", "submitted_on"):
                assert isinstance(c.type, Date), f"{t.name}.{c.name} must be DATE"


def test_no_raw_phi_columns():
    banned = re.compile(r"(first|last|full)_?name|patient_name|dob|birth|ssn|member_?id|address|phone")
    for t in TABLES.values():
        for c in t.columns:
            assert not banned.search(c.name), f"{t.name}.{c.name} looks like raw PHI"
    assert set(TABLES["patient_ref"].columns.keys()) >= {"ref_hash"}


def test_every_business_column_documents_its_source():
    infra = set(docgen.INFRA_SOURCES) | {"created_at"}
    for t in TABLES.values():
        for c in t.columns:
            assert c.info.get("src") or c.name in infra, f"{t.name}.{c.name} has no source note"


def test_mssql_ddl_compiles_with_expected_types():
    ddl = "\n".join(str(CreateTable(t).compile(dialect=mssql.dialect())) for t in TABLES.values())
    assert "DATETIME2(0)" in ddl and "SYSUTCDATETIME()" in ddl and "NVARCHAR(MAX)" in ddl
    assert "NUMERIC(18, 2)" in ddl and "IDENTITY" in ddl
    assert "FLOAT" not in ddl.upper()


# -------------------------------------------------------------------------- tenant isolation


def test_cross_tenant_reference_is_rejected_by_composite_fk(engine):
    file_a = load_file(engine, 1, "a" * 64)
    file_b = load_file(engine, 2, "b" * 64)
    with tenant_session(engine, 1) as s:
        s.add(m.Payer(source_file_id=file_a, payer_id_code="P1", name="Payer 1"))
        s.commit()
        payer_a = s.scalars(select(m.Payer)).one().id
    with tenant_session(engine, 2) as s:
        # tenant 2 tries to reference tenant 1's payer
        s.add(m.FeeSchedule(source_file_id=file_b, payer_id=payer_a, cpt="99213", modifier="",
                            allowed_amount=Decimal("90.00"), effective_date=date(2025, 1, 1)))  # fmt: skip
        with pytest.raises(IntegrityError):
            s.commit()


def test_file_from_another_tenant_is_rejected(engine):
    file_b = load_file(engine, 2)
    with tenant_session(engine, 1) as s:
        s.add(m.Payer(source_file_id=file_b, payer_id_code="P1", name="Payer 1"))
        with pytest.raises(IntegrityError):
            s.commit()


def test_cross_tenant_leak_every_scoped_model_returns_only_own_rows(engine):
    file_a, file_b = load_file(engine, 1, "a" * 64), load_file(engine, 2, "b" * 64)
    for tid, fid in ((1, file_a), (2, file_b)):
        with tenant_session(engine, tid) as s:
            s.add_all([
                m.Payer(source_file_id=fid, payer_id_code=f"PAY{tid}", name=f"Payer {tid}"),
                m.Provider(source_file_id=fid, npi=f"199999999{tid}", name=f"Prov {tid}"),
                m.PatientRef(source_file_id=fid, ref_hash=bytes([tid]) * 32),
            ])  # fmt: skip
            s.commit()
    for tid in (1, 2):
        with tenant_session(engine, tid) as s:
            for model in (m.SourceFile, m.Payer, m.Provider, m.PatientRef):
                rows = s.scalars(select(model)).all()
                assert len(rows) == 1 and rows[0].tenant_id == tid, model.__name__
            assert s.scalars(select(m.Payer).where(m.Payer.payer_id_code == f"PAY{3 - tid}")).first() is None


def test_every_scoped_model_query_is_filtered_by_tenant_in_sql(engine):
    seen: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def _capture(_conn, _cur, statement, _params, _ctx, _many):
        seen.append(statement)

    models = [c for c in vars(m).values() if isinstance(c, type) and issubclass(c, m.Scoped) and c is not m.Scoped]
    assert len(models) == len(EXPECTED_TABLES) - 1  # every table except tenant
    with tenant_session(engine, 1) as s:
        for model in models:
            seen.clear()
            s.scalars(select(model)).all()
            assert seen and f"{model.__tablename__}.tenant_id = ?" in seen[-1], model.__name__


def test_session_rejects_rows_for_another_tenant(engine):
    with tenant_session(engine, 1) as s:
        s.add(m.SourceFile(tenant_id=2, file_name="x", file_sha256="c" * 64, file_type="835",
                           byte_size=1, status="loaded"))  # fmt: skip
        with pytest.raises(TenantMismatchError):
            s.flush()


# ---------------------------------------------------------------------------- idempotency


def test_same_file_hash_cannot_load_twice_for_a_tenant_but_can_for_another(engine):
    load_file(engine, 1, "d" * 64)
    load_file(engine, 2, "d" * 64)  # a different tenant may hold the same bytes
    with pytest.raises(IntegrityError):
        load_file(engine, 1, "d" * 64)


def test_same_control_numbers_cannot_create_a_second_event(engine):
    fid = load_file(engine, 1)

    def add_event(seq):
        with tenant_session(engine, 1) as s:
            s.add(m.Event(source_file_id=fid, event_type="837P.claim", isa13="000000001", gs06="1",
                          st02="0001", seq_in_file=seq, known_at=date(2026, 1, 1), payload="[]"))  # fmt: skip
            s.commit()

    add_event(1)
    add_event(2)
    with pytest.raises(IntegrityError):
        add_event(1)


def test_adjustment_group_code_is_constrained(engine):
    assert any(c.name and "group_code" in c.name for c in TABLES["adjustment"].constraints)


# ------------------------------------------------------------------- migration and the docs


def _alembic_cfg(buffer=None):
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    if buffer is not None:
        cfg.output_buffer = buffer
    return cfg


def test_migration_generates_tsql_for_every_table_and_the_append_only_trigger(monkeypatch):
    monkeypatch.delenv("KRISNAI_ALEMBIC_URL", raising=False)
    buf = io.StringIO()
    command.upgrade(_alembic_cfg(buf), "head", sql=True)
    sql = buf.getvalue()
    for name in EXPECTED_TABLES:
        assert re.search(rf"CREATE TABLE {name} \(", sql), name
    assert "CREATE TRIGGER trg_event_append_only ON event" in sql
    assert "INSTEAD OF UPDATE, DELETE" in sql
    assert "DATETIME2(0)" in sql and "FLOAT" not in sql.upper()


def test_migration_matches_models_on_a_real_database(tmp_path, monkeypatch):
    """Run the real migration on scratch SQLite: no table/column/constraint drift from the models.

    Types are not compared: SQLite has no BIGINT identity, so keys differ by design.
    """
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    url = f"sqlite:///{tmp_path / 'drift.db'}"
    monkeypatch.setenv("KRISNAI_ALEMBIC_URL", url)
    command.upgrade(_alembic_cfg(), "head")
    eng = create_engine(url)
    with eng.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": False}), Base.metadata)
    assert diff == []
    command.downgrade(_alembic_cfg(), "base")


@pytest.mark.skipif(not os.environ.get("KRISNAI_TEST_ALEMBIC_URL"), reason="needs a SQL Server test DB")
def test_real_sql_server_upgrade_downgrade_and_append_only_trigger(monkeypatch):
    monkeypatch.setenv("KRISNAI_ALEMBIC_URL", os.environ["KRISNAI_TEST_ALEMBIC_URL"])
    cfg = _alembic_cfg()
    command.upgrade(cfg, "head")
    eng = create_engine(os.environ["KRISNAI_TEST_ALEMBIC_URL"])
    try:
        with Session(eng) as s:
            s.add(m.Tenant(name="T", patient_salt_key="K"))
            s.flush()
            tid = s.scalars(select(m.Tenant.tenant_id)).first()
            f = m.SourceFile(tenant_id=tid, file_name="f", file_sha256="e" * 64, file_type="837P",
                             byte_size=1, status="loaded")  # fmt: skip
            s.add(f)
            s.flush()
            s.add(m.Event(tenant_id=tid, source_file_id=f.id, event_type="t", isa13="1", gs06="1",
                          st02="1", seq_in_file=1, known_at=date(2026, 1, 1), payload="[]"))  # fmt: skip
            s.commit()
            with pytest.raises(Exception, match="append-only"):
                s.execute(m.Event.__table__.update().values(payload="changed"))
    finally:
        command.downgrade(cfg, "base")


def test_data_model_doc_is_current_and_lists_every_column():
    text = docgen.render()
    assert docgen.DOC_PATH.read_text(encoding="utf-8").replace("\r\n", "\n") == text
    for name, t in TABLES.items():
        assert f"### `{name}`" in text
        for c in t.columns:
            assert f"| `{c.name}` |" in text
    assert "CLM01" in text and "erDiagram" in text
