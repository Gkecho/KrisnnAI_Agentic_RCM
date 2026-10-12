"""a6 config: rejection_route

Revision ID: 0007
Revises: 0006

Routing table for the claim submission and response agent (M10). Generated from krisnai.model.engine.
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rejection_route",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source", sa.String(length=5), nullable=False),
        sa.Column("status_category", sa.String(length=5), nullable=False),
        sa.Column("status_code", sa.String(length=5), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("owner", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint("kind IN ('technical', 'business')", name=op.f("ck_rejection_route_kind")),
        sa.CheckConstraint(
            "owner IN ('front_desk', 'coding', 'billing')", name=op.f("ck_rejection_route_owner")
        ),
        sa.CheckConstraint("source IN ('999', '277CA')", name=op.f("ck_rejection_route_source")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_rejection_route_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rejection_route")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_rejection_route_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "source",
            "status_category",
            "status_code",
            name=op.f("uq_rejection_route_tenant_id_source_status_category_status_code"),
        ),
    )


def downgrade() -> None:
    op.drop_table("rejection_route")
