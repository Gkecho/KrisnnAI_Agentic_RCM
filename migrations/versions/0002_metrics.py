"""metrics: one inline table-valued function per KPI in schema `metrics` (SQL Server)

Revision ID: 0002
Revises: 0001

SQL Server views cannot take a date, so each KPI is `metrics.fn_<kpi>(@as_of, @tenant_id)`. The text comes from
krisnai/metrics/sql/*.sql, the same files the Python tests run on SQLite. Other dialects skip this migration.
"""

from alembic import op

from krisnai.metrics.loader import function_ddl, kpi_names

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "mssql":
        return
    op.execute("CREATE SCHEMA metrics")
    for kpi in kpi_names():
        op.execute(function_ddl(kpi))


def downgrade() -> None:
    if op.get_context().dialect.name != "mssql":
        return
    for kpi in kpi_names():
        op.execute(f"DROP FUNCTION metrics.fn_{kpi}")
    op.execute("DROP SCHEMA metrics")
