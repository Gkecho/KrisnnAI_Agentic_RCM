"""a8 config: carc_route and payer_appeal_window

Revision ID: 0005
Revises: 0004

Routing tables for the denial agent (M7). Generated from krisnai.model.engine.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carc_route",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("carc_code", sa.String(length=5), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("owner", sa.String(length=20), nullable=False),
        sa.Column("disposition", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint(
            "disposition IN ('correctable', 'appealable', 'write_off_review')", name=op.f("ck_carc_route_disposition")
        ),
        sa.CheckConstraint("owner IN ('front_desk', 'coding', 'billing')", name=op.f("ck_carc_route_owner")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_carc_route_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_carc_route")),
        sa.UniqueConstraint("tenant_id", "carc_code", name=op.f("uq_carc_route_tenant_id_carc_code")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_carc_route_tenant_id_id")),
    )
    op.create_table(
        "payer_appeal_window",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("appeal_days", sa.Integer(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payer_id"],
            ["payer.tenant_id", "payer.id"],
            name=op.f("fk_payer_appeal_window_tenant_id_payer_id_payer"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_payer_appeal_window_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payer_appeal_window")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_payer_appeal_window_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "payer_id", name=op.f("uq_payer_appeal_window_tenant_id_payer_id")),
    )


def downgrade() -> None:
    op.drop_table("payer_appeal_window")
    op.drop_table("carc_route")
