"""enrollment: enrollment, provider_screening

Revision ID: 0013
Revises: 0012

Provider enrollment with each payer and sanctions screening results, for the credentialing agent (M18).
Generated from krisnnai.model.credentialing.
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def _fk(table: str, col: str, ref: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", col], [f"{ref}.tenant_id", f"{ref}.id"], name=op.f(f"fk_{table}_tenant_id_{col}_{ref}")
    )


def upgrade() -> None:
    op.create_table(
        "enrollment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("enrollment_ref", sa.String(length=40), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("submitted_on", sa.Date(), nullable=True),
        sa.Column("effective_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("status_on", sa.Date(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'expired', 'denied', 'terminated')", name=op.f("ck_enrollment_status")
        ),
        _fk("enrollment", "payer_id", "payer"),
        _fk("enrollment", "provider_id", "provider"),
        _fk("enrollment", "source_file_id", "source_file"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_enrollment_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_enrollment")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_enrollment_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "enrollment_ref", name=op.f("uq_enrollment_tenant_id_enrollment_ref")),
    )
    op.create_table(
        "provider_screening",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("screening_ref", sa.String(length=40), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=False),
        sa.Column("screened_on", sa.Date(), nullable=False),
        sa.Column("result", sa.String(length=10), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint("result IN ('clear', 'excluded')", name=op.f("ck_provider_screening_result")),
        _fk("provider_screening", "provider_id", "provider"),
        _fk("provider_screening", "source_file_id", "source_file"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_provider_screening_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_screening")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_provider_screening_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id", "screening_ref", name=op.f("uq_provider_screening_tenant_id_screening_ref")
        ),
    )


def downgrade() -> None:
    op.drop_table("provider_screening")
    op.drop_table("enrollment")
