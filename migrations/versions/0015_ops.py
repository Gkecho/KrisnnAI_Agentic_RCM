"""ops: ops_run, patient_crosswalk

Revision ID: 0015
Revises: 0014

Run log / watermark for the daily and backfill runner, and the member id -> master patient id crosswalk (M22).
Generated from krisnnai.model.ops.
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ops_run",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("go_live", sa.Date(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("files_loaded", sa.Integer(), nullable=False),
        sa.Column("files_skipped", sa.Integer(), nullable=False),
        sa.Column("files_failed", sa.Integer(), nullable=False),
        sa.Column("events_added", sa.Integer(), nullable=False),
        sa.Column("gate", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint("mode IN ('daily', 'backfill')", name=op.f("ck_ops_run_mode")),
        sa.CheckConstraint("gate IN ('passed', 'failed', 'skipped')", name=op.f("ck_ops_run_gate")),
        sa.CheckConstraint("status IN ('ok', 'gated', 'failed')", name=op.f("ck_ops_run_status")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_ops_run_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ops_run")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_ops_run_tenant_id_id")),
    )
    op.create_table(
        "patient_crosswalk",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("member_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column("master_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_patient_crosswalk_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_patient_crosswalk_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_crosswalk")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_patient_crosswalk_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id", "member_hash", name=op.f("uq_patient_crosswalk_tenant_id_member_hash")
        ),
    )


def downgrade() -> None:
    op.drop_table("patient_crosswalk")
    op.drop_table("ops_run")
