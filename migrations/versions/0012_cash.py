"""cash: bank_deposit, posting

Revision ID: 0012
Revises: 0011

Bank deposits and PM postings, for the cash reconciliation agent (M17). Generated from krisnai.model.cash.
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def _fk(table: str, col: str, ref: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", col], [f"{ref}.tenant_id", f"{ref}.id"], name=op.f(f"fk_{table}_tenant_id_{col}_{ref}")
    )


def upgrade() -> None:
    op.create_table(
        "bank_deposit",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("deposit_ref", sa.String(length=40), nullable=False),
        sa.Column("deposit_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=True),
        sa.Column("trace_ref", sa.String(length=50), nullable=True),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        _fk("bank_deposit", "payer_id", "payer"),
        _fk("bank_deposit", "source_file_id", "source_file"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_bank_deposit_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bank_deposit")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_bank_deposit_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "deposit_ref", name=op.f("uq_bank_deposit_tenant_id_deposit_ref")),
    )
    op.create_table(
        "posting",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("posting_ref", sa.String(length=40), nullable=False),
        sa.Column("payment_trace", sa.String(length=50), nullable=False),
        sa.Column("claim_submitter_id", sa.String(length=38), nullable=False),
        sa.Column("posted_on", sa.Date(), nullable=False),
        sa.Column("posted_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("posted_by_role", sa.String(length=20), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        _fk("posting", "source_file_id", "source_file"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_posting_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_posting")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_posting_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "posting_ref", name=op.f("uq_posting_tenant_id_posting_ref")),
    )


def downgrade() -> None:
    op.drop_table("posting")
    op.drop_table("bank_deposit")
