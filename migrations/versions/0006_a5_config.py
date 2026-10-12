"""a5 config: ncci_pair, mue_limit and payer_filing_window

Revision ID: 0006
Revises: 0005

Rule tables for the claim prevention agent (M8). Generated from krisnai.model.engine.
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

def _loaded_at():
    return sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False)


def _tenant_cols():
    return [
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "ncci_pair",
        *_tenant_cols(),
        sa.Column("cpt_a", sa.String(length=5), nullable=False),
        sa.Column("cpt_b", sa.String(length=5), nullable=False),
        sa.Column("modifier_indicator", sa.String(length=1), nullable=False),
        _loaded_at(),
        sa.CheckConstraint("modifier_indicator IN ('0', '1')", name=op.f("ck_ncci_pair_indicator")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_ncci_pair_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ncci_pair")),
        sa.UniqueConstraint("tenant_id", "cpt_a", "cpt_b", name=op.f("uq_ncci_pair_tenant_id_cpt_a_cpt_b")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_ncci_pair_tenant_id_id")),
    )
    op.create_table(
        "mue_limit",
        *_tenant_cols(),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("max_units", sa.Integer(), nullable=False),
        _loaded_at(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_mue_limit_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mue_limit")),
        sa.UniqueConstraint("tenant_id", "cpt", name=op.f("uq_mue_limit_tenant_id_cpt")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_mue_limit_tenant_id_id")),
    )
    op.create_table(
        "payer_filing_window",
        *_tenant_cols(),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("filing_days", sa.Integer(), nullable=False),
        _loaded_at(),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payer_id"],
            ["payer.tenant_id", "payer.id"],
            name=op.f("fk_payer_filing_window_tenant_id_payer_id_payer"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_payer_filing_window_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payer_filing_window")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_payer_filing_window_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "payer_id", name=op.f("uq_payer_filing_window_tenant_id_payer_id")),
    )


def downgrade() -> None:
    op.drop_table("payer_filing_window")
    op.drop_table("mue_limit")
    op.drop_table("ncci_pair")
