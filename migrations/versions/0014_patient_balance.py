"""patient balance: patient_payment, patient_statement

Revision ID: 0014
Revises: 0013

Patient payments and statement / account status, for the patient engagement agent (M19).
Generated from krisnai.model.patient_balance.
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def _fk(table: str, col: str, ref: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", col], [f"{ref}.tenant_id", f"{ref}.id"], name=op.f(f"fk_{table}_tenant_id_{col}_{ref}")
    )


def upgrade() -> None:
    op.create_table(
        "patient_payment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("payment_ref", sa.String(length=40), nullable=False),
        sa.Column("claim_submitter_id", sa.String(length=38), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        _fk("patient_payment", "source_file_id", "source_file"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_patient_payment_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_payment")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_patient_payment_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "payment_ref", name=op.f("uq_patient_payment_tenant_id_payment_ref")),
    )
    op.create_table(
        "patient_statement",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("statement_ref", sa.String(length=40), nullable=False),
        sa.Column("claim_submitter_id", sa.String(length=38), nullable=False),
        sa.Column("sent_on", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('sent', 'disputed', 'plan', 'hardship', 'returned')",
            name=op.f("ck_patient_statement_status"),
        ),
        _fk("patient_statement", "source_file_id", "source_file"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_patient_statement_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_statement")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_patient_statement_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id", "statement_ref", name=op.f("uq_patient_statement_tenant_id_statement_ref")
        ),
    )


def downgrade() -> None:
    op.drop_table("patient_statement")
    op.drop_table("patient_payment")
