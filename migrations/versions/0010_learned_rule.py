"""a9 config: learned_rule

Revision ID: 0010
Revises: 0009

Rules the denial prevention learning agent (M15) proposed from recurring denials. Only rows with status approved
change A5, and only a named person approves. Generated from krisnai.model.engine.
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "learned_rule",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_key", sa.String(length=60), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("carc", sa.String(length=5), nullable=False),
        sa.Column("proposed_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("n_denials", sa.Integer(), nullable=False),
        sa.Column("n_adjudicated", sa.Integer(), nullable=False),
        sa.Column("denial_rate", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("approved_by", sa.String(length=60), nullable=True),
        sa.Column("decided_on", sa.Date(), nullable=True),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('proposed', 'approved', 'rejected')", name=op.f("ck_learned_rule_status")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payer_id"],
            ["payer.tenant_id", "payer.id"],
            name=op.f("fk_learned_rule_tenant_id_payer_id_payer"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_learned_rule_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learned_rule")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_learned_rule_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "rule_key", name=op.f("uq_learned_rule_tenant_id_rule_key")),
    )


def downgrade() -> None:
    op.drop_table("learned_rule")
