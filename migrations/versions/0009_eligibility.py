"""eligibility: appointment, eligibility_response

Revision ID: 0009
Revises: 0008

Appointments and 271 eligibility responses, for the pre-visit clearance agent (M14). Generated from
krisnai.model.eligibility.
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _fk(table: str, col: str, ref: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["tenant_id", col], [f"{ref}.tenant_id", f"{ref}.id"], name=op.f(f"fk_{table}_tenant_id_{col}_{ref}")
    )


def upgrade() -> None:
    op.create_table(
        "appointment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("appt_ref", sa.String(length=40), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_ref_id", sa.BigInteger(), nullable=False),
        sa.Column("appt_date", sa.Date(), nullable=False),
        sa.Column("booked_on", sa.Date(), nullable=False),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        _fk("appointment", "patient_ref_id", "patient_ref"),
        _fk("appointment", "payer_id", "payer"),
        _fk("appointment", "provider_id", "provider"),
        _fk("appointment", "source_file_id", "source_file"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_appointment_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointment")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_appointment_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "appt_ref", name=op.f("uq_appointment_tenant_id_appt_ref")),
    )
    op.create_table(
        "eligibility_response",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_ref_id", sa.BigInteger(), nullable=True),
        sa.Column("response_ref", sa.String(length=50), nullable=False),
        sa.Column("checked_on", sa.Date(), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("plan_begin", sa.Date(), nullable=True),
        sa.Column("plan_end", sa.Date(), nullable=True),
        sa.Column("other_payer", sa.String(length=60), nullable=True),
        sa.Column("copay", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("coinsurance", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("deductible_remaining", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        _fk("eligibility_response", "event_id", "event"),
        _fk("eligibility_response", "patient_ref_id", "patient_ref"),
        _fk("eligibility_response", "payer_id", "payer"),
        _fk("eligibility_response", "source_file_id", "source_file"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_eligibility_response_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eligibility_response")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_eligibility_response_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "event_id", name=op.f("uq_eligibility_response_tenant_id_event_id")),
    )


def downgrade() -> None:
    op.drop_table("eligibility_response")
    op.drop_table("appointment")
