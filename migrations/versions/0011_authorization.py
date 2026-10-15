"""authorization: prior_authorization, auth_requirement

Revision ID: 0011
Revises: 0010

Prior-authorization records and the payer + CPT pairs that need one, for the authorization agent (M16).
Generated from krisnai.model.authorization.
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def _fk(table: str, col: str, ref: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", col], [f"{ref}.tenant_id", f"{ref}.id"], name=op.f(f"fk_{table}_tenant_id_{col}_{ref}")
    )


def upgrade() -> None:
    op.create_table(
        "prior_authorization",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("auth_ref", sa.String(length=40), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_ref_id", sa.BigInteger(), nullable=False),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("appointment_ref", sa.String(length=40), nullable=True),
        sa.Column("units_approved", sa.Integer(), nullable=True),
        sa.Column("units_used", sa.Integer(), nullable=True),
        sa.Column("units_as_of", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("requested_on", sa.Date(), nullable=False),
        sa.Column("decided_on", sa.Date(), nullable=True),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('requested', 'approved', 'denied', 'expired')", name=op.f("ck_prior_authorization_status")
        ),
        _fk("prior_authorization", "patient_ref_id", "patient_ref"),
        _fk("prior_authorization", "payer_id", "payer"),
        _fk("prior_authorization", "source_file_id", "source_file"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_prior_authorization_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prior_authorization")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_prior_authorization_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "auth_ref", name=op.f("uq_prior_authorization_tenant_id_auth_ref")),
    )
    op.create_table(
        "auth_requirement",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("validity_days", sa.Integer(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        _fk("auth_requirement", "payer_id", "payer"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_auth_requirement_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_requirement")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_auth_requirement_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "payer_id", "cpt", name=op.f("uq_auth_requirement_tenant_id_payer_id_cpt")),
    )


def downgrade() -> None:
    op.drop_table("auth_requirement")
    op.drop_table("prior_authorization")
