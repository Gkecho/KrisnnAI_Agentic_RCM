"""visit: practice-management visits, to detect visits that were never billed

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "visit",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("visit_ref", sa.String(length=40), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_ref_id", sa.BigInteger(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("units", sa.Numeric(precision=9, scale=2), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "patient_ref_id"],
            ["patient_ref.tenant_id", "patient_ref.id"],
            name=op.f("fk_visit_tenant_id_patient_ref_id_patient_ref"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payer_id"],
            ["payer.tenant_id", "payer.id"],
            name=op.f("fk_visit_tenant_id_payer_id_payer"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "provider_id"],
            ["provider.tenant_id", "provider.id"],
            name=op.f("fk_visit_tenant_id_provider_id_provider"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_visit_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_visit_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_visit")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_visit_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "visit_ref", name=op.f("uq_visit_tenant_id_visit_ref")),
    )


def downgrade() -> None:
    op.drop_table("visit")
