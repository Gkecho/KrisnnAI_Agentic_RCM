"""documentation: visit_note, charge

Revision ID: 0008
Revises: 0007

Note status and charge entries per visit, for the documentation completeness agent (M13). Generated from
krisnai.model.visits.
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _common(table: str) -> list:
    return [
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
    ]


def _tail(table: str, unique_col: str) -> list:
    return [
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f(f"fk_{table}_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f(f"fk_{table}_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f(f"uq_{table}_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", unique_col, name=op.f(f"uq_{table}_tenant_id_{unique_col}")),
    ]


def upgrade() -> None:
    op.create_table(
        "visit_note",
        *_common("visit_note"),
        sa.Column("visit_ref", sa.String(length=40), nullable=False),
        sa.Column("note_date", sa.Date(), nullable=False),
        sa.Column("signed_date", sa.Date(), nullable=True),
        sa.Column("minutes", sa.Integer(), nullable=True),
        sa.Column("elements", sa.String(length=200), nullable=False),
        *_tail("visit_note", "visit_ref"),
    )
    op.create_table(
        "charge",
        *_common("charge"),
        sa.Column("charge_ref", sa.String(length=40), nullable=False),
        sa.Column("visit_ref", sa.String(length=40), nullable=False),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("units", sa.Numeric(precision=9, scale=2), nullable=False),
        sa.Column("entered_date", sa.Date(), nullable=False),
        *_tail("charge", "charge_ref"),
    )


def downgrade() -> None:
    op.drop_table("charge")
    op.drop_table("visit_note")
