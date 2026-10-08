"""core model: tenant, ingest, reference, claims, remits, snapshots

Revision ID: 0001
Revises:

Tables are generated from krisnai.model (SQL Server). `event` is append-only: a trigger rejects
UPDATE and DELETE so normalized tables can always be rebuilt from it.
"""

import sqlalchemy as sa
from alembic import op

import krisnai.model  # noqa: F401  (registers the SQL Server type overrides)

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("tenant_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("patient_salt_key", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("tenant_id", name=op.f("pk_tenant")),
    )
    op.create_table(
        "source_file",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("failure_reason", sa.String(length=1000), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_source_file_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_file")),
        sa.UniqueConstraint(
            "tenant_id", "file_sha256", name=op.f("uq_source_file_tenant_id_file_sha256")
        ),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_source_file_tenant_id_id")),
    )
    op.create_table(
        "event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("isa13", sa.String(length=9), nullable=False),
        sa.Column("gs06", sa.String(length=9), nullable=False),
        sa.Column("st02", sa.String(length=9), nullable=False),
        sa.Column("seq_in_file", sa.Integer(), nullable=False),
        sa.Column("known_at", sa.DateTime(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_event_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_event_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_event_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "source_file_id",
            "isa13",
            "gs06",
            "st02",
            "seq_in_file",
            name=op.f("uq_event_tenant_id_source_file_id_isa13_gs06_st02_seq_in_file"),
        ),
    )
    op.create_table(
        "patient_ref",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("ref_hash", sa.LargeBinary(length=32), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_patient_ref_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_patient_ref_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_ref")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_patient_ref_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id", "ref_hash", name=op.f("uq_patient_ref_tenant_id_ref_hash")
        ),
    )
    op.create_table(
        "payer",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("payer_id_code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_payer_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_payer_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payer")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_payer_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id", "payer_id_code", name=op.f("uq_payer_tenant_id_payer_id_code")
        ),
    )
    op.create_table(
        "provider",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("npi", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("tax_id", sa.String(length=9), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_provider_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_provider_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_provider_tenant_id_id")),
        sa.UniqueConstraint("tenant_id", "npi", name=op.f("uq_provider_tenant_id_npi")),
    )
    op.create_table(
        "ack_999",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("acked_gs06", sa.String(length=9), nullable=False),
        sa.Column("acked_st02", sa.String(length=9), nullable=False),
        sa.Column("transaction_set", sa.String(length=3), nullable=False),
        sa.Column("transaction_status", sa.String(length=1), nullable=False),
        sa.Column("group_status", sa.String(length=1), nullable=True),
        sa.Column("error_codes", sa.String(length=100), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "event_id"],
            ["event.tenant_id", "event.id"],
            name=op.f("fk_ack_999_tenant_id_event_id_event"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_ack_999_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_ack_999_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ack_999")),
        sa.UniqueConstraint("tenant_id", "event_id", name=op.f("uq_ack_999_tenant_id_event_id")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_ack_999_tenant_id_id")),
    )
    op.create_table(
        "claim",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_ref_id", sa.BigInteger(), nullable=False),
        sa.Column("claim_submitter_id", sa.String(length=38), nullable=False),
        sa.Column("total_charge", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("place_of_service", sa.String(length=2), nullable=True),
        sa.Column("frequency_code", sa.String(length=1), nullable=False),
        sa.Column("payer_claim_control_number", sa.String(length=50), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("submitted_on", sa.Date(), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "event_id"],
            ["event.tenant_id", "event.id"],
            name=op.f("fk_claim_tenant_id_event_id_event"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "patient_ref_id"],
            ["patient_ref.tenant_id", "patient_ref.id"],
            name=op.f("fk_claim_tenant_id_patient_ref_id_patient_ref"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payer_id"],
            ["payer.tenant_id", "payer.id"],
            name=op.f("fk_claim_tenant_id_payer_id_payer"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "provider_id"],
            ["provider.tenant_id", "provider.id"],
            name=op.f("fk_claim_tenant_id_provider_id_provider"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_claim_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_claim_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claim")),
        sa.UniqueConstraint("tenant_id", "event_id", name=op.f("uq_claim_tenant_id_event_id")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_claim_tenant_id_id")),
    )
    op.create_table(
        "fee_schedule",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("modifier", sa.String(length=2), nullable=False),
        sa.Column("allowed_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payer_id"],
            ["payer.tenant_id", "payer.id"],
            name=op.f("fk_fee_schedule_tenant_id_payer_id_payer"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_fee_schedule_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_fee_schedule_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fee_schedule")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_fee_schedule_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "payer_id",
            "cpt",
            "modifier",
            "effective_date",
            name=op.f("uq_fee_schedule_tenant_id_payer_id_cpt_modifier_effective_date"),
        ),
    )
    op.create_table(
        "payment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("payer_id", sa.BigInteger(), nullable=False),
        sa.Column("trace_number", sa.String(length=50), nullable=False),
        sa.Column("payment_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("credit_debit", sa.String(length=1), nullable=False),
        sa.Column("payment_method", sa.String(length=3), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "event_id"],
            ["event.tenant_id", "event.id"],
            name=op.f("fk_payment_tenant_id_event_id_event"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payer_id"],
            ["payer.tenant_id", "payer.id"],
            name=op.f("fk_payment_tenant_id_payer_id_payer"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_payment_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_payment_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment")),
        sa.UniqueConstraint("tenant_id", "event_id", name=op.f("uq_payment_tenant_id_event_id")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_payment_tenant_id_id")),
    )
    op.create_table(
        "ack_277ca",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("claim_id", sa.BigInteger(), nullable=True),
        sa.Column("claim_submitter_id", sa.String(length=38), nullable=False),
        sa.Column("status_category", sa.String(length=5), nullable=False),
        sa.Column("status_code", sa.String(length=5), nullable=True),
        sa.Column("entity_code", sa.String(length=5), nullable=True),
        sa.Column("status_date", sa.Date(), nullable=True),
        sa.Column("total_charge", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("payer_claim_number", sa.String(length=50), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["claim.tenant_id", "claim.id"],
            name=op.f("fk_ack_277ca_tenant_id_claim_id_claim"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "event_id"],
            ["event.tenant_id", "event.id"],
            name=op.f("fk_ack_277ca_tenant_id_event_id_event"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_ack_277ca_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_ack_277ca_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ack_277ca")),
        sa.UniqueConstraint(
            "tenant_id",
            "event_id",
            "claim_submitter_id",
            name=op.f("uq_ack_277ca_tenant_id_event_id_claim_submitter_id"),
        ),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_ack_277ca_tenant_id_id")),
    )
    op.create_table(
        "ar_snapshot",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("claim_id", sa.BigInteger(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("balance", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("days_outstanding", sa.Integer(), nullable=False),
        sa.Column("aging_bucket", sa.String(length=10), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["claim.tenant_id", "claim.id"],
            name=op.f("fk_ar_snapshot_tenant_id_claim_id_claim"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_ar_snapshot_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_ar_snapshot_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ar_snapshot")),
        sa.UniqueConstraint(
            "tenant_id",
            "claim_id",
            "as_of_date",
            name=op.f("uq_ar_snapshot_tenant_id_claim_id_as_of_date"),
        ),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_ar_snapshot_tenant_id_id")),
    )
    op.create_table(
        "claim_dx",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("claim_id", sa.BigInteger(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("dx_qualifier", sa.String(length=3), nullable=False),
        sa.Column("dx_code", sa.String(length=8), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["claim.tenant_id", "claim.id"],
            name=op.f("fk_claim_dx_tenant_id_claim_id_claim"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_claim_dx_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_claim_dx_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claim_dx")),
        sa.UniqueConstraint(
            "tenant_id", "claim_id", "seq", name=op.f("uq_claim_dx_tenant_id_claim_id_seq")
        ),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_claim_dx_tenant_id_id")),
    )
    op.create_table(
        "claim_line",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("claim_id", sa.BigInteger(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("modifier_1", sa.String(length=2), nullable=True),
        sa.Column("modifier_2", sa.String(length=2), nullable=True),
        sa.Column("modifier_3", sa.String(length=2), nullable=True),
        sa.Column("modifier_4", sa.String(length=2), nullable=True),
        sa.Column("charge", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("units", sa.Numeric(precision=9, scale=2), nullable=False),
        sa.Column("unit_basis", sa.String(length=2), nullable=False),
        sa.Column("diagnosis_pointer", sa.String(length=8), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["claim.tenant_id", "claim.id"],
            name=op.f("fk_claim_line_tenant_id_claim_id_claim"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_claim_line_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_claim_line_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claim_line")),
        sa.UniqueConstraint(
            "tenant_id",
            "claim_id",
            "line_number",
            name=op.f("uq_claim_line_tenant_id_claim_id_line_number"),
        ),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_claim_line_tenant_id_id")),
    )
    op.create_table(
        "plb_adjustment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("payment_id", sa.BigInteger(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("provider_ref", sa.String(length=50), nullable=False),
        sa.Column("fiscal_period_date", sa.Date(), nullable=False),
        sa.Column("reason_code", sa.String(length=2), nullable=False),
        sa.Column("reference_id", sa.String(length=50), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payment_id"],
            ["payment.tenant_id", "payment.id"],
            name=op.f("fk_plb_adjustment_tenant_id_payment_id_payment"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_plb_adjustment_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_plb_adjustment_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plb_adjustment")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_plb_adjustment_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "payment_id",
            "seq",
            name=op.f("uq_plb_adjustment_tenant_id_payment_id_seq"),
        ),
    )
    op.create_table(
        "remit",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("payment_id", sa.BigInteger(), nullable=False),
        sa.Column("claim_id", sa.BigInteger(), nullable=True),
        sa.Column("patient_ref_id", sa.BigInteger(), nullable=True),
        sa.Column("claim_submitter_id", sa.String(length=38), nullable=False),
        sa.Column("claim_status_code", sa.String(length=2), nullable=False),
        sa.Column("total_charge", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_paid", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("patient_responsibility", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("filing_indicator", sa.String(length=2), nullable=True),
        sa.Column("payer_claim_control_number", sa.String(length=50), nullable=False),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("match_method", sa.String(length=30), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "claim_id"],
            ["claim.tenant_id", "claim.id"],
            name=op.f("fk_remit_tenant_id_claim_id_claim"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "event_id"],
            ["event.tenant_id", "event.id"],
            name=op.f("fk_remit_tenant_id_event_id_event"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "patient_ref_id"],
            ["patient_ref.tenant_id", "patient_ref.id"],
            name=op.f("fk_remit_tenant_id_patient_ref_id_patient_ref"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "payment_id"],
            ["payment.tenant_id", "payment.id"],
            name=op.f("fk_remit_tenant_id_payment_id_payment"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_remit_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_remit_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_remit")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_remit_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "payment_id",
            "claim_submitter_id",
            "payer_claim_control_number",
            name=op.f(
                "uq_remit_tenant_id_payment_id_claim_submitter_id_payer_claim_control_number"
            ),
        ),
    )
    op.create_table(
        "remit_line",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("remit_id", sa.BigInteger(), nullable=False),
        sa.Column("claim_line_id", sa.BigInteger(), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("cpt", sa.String(length=5), nullable=False),
        sa.Column("modifier_1", sa.String(length=2), nullable=True),
        sa.Column("modifier_2", sa.String(length=2), nullable=True),
        sa.Column("modifier_3", sa.String(length=2), nullable=True),
        sa.Column("modifier_4", sa.String(length=2), nullable=True),
        sa.Column("charge", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("paid", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("units", sa.Numeric(precision=9, scale=2), nullable=True),
        sa.Column("allowed_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("match_method", sa.String(length=30), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "claim_line_id"],
            ["claim_line.tenant_id", "claim_line.id"],
            name=op.f("fk_remit_line_tenant_id_claim_line_id_claim_line"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "remit_id"],
            ["remit.tenant_id", "remit.id"],
            name=op.f("fk_remit_line_tenant_id_remit_id_remit"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_remit_line_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_remit_line_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_remit_line")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_remit_line_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "remit_id",
            "line_number",
            name=op.f("uq_remit_line_tenant_id_remit_id_line_number"),
        ),
    )
    op.create_table(
        "adjustment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("remit_id", sa.BigInteger(), nullable=False),
        sa.Column("remit_line_id", sa.BigInteger(), nullable=True),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("group_code", sa.String(length=2), nullable=False),
        sa.Column("reason_code", sa.String(length=5), nullable=False),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=9, scale=2), nullable=True),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.CheckConstraint(
            "group_code IN ('CO', 'CR', 'OA', 'PI', 'PR')", name=op.f("ck_adjustment_group_code")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "remit_id"],
            ["remit.tenant_id", "remit.id"],
            name=op.f("fk_adjustment_tenant_id_remit_id_remit"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "remit_line_id"],
            ["remit_line.tenant_id", "remit_line.id"],
            name=op.f("fk_adjustment_tenant_id_remit_line_id_remit_line"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_adjustment_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_adjustment_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_adjustment")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_adjustment_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "remit_id",
            "remit_line_id",
            "seq",
            name=op.f("uq_adjustment_tenant_id_remit_id_remit_line_id_seq"),
        ),
    )
    op.create_table(
        "remit_remark",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("source_file_id", sa.BigInteger(), nullable=False),
        sa.Column("remit_id", sa.BigInteger(), nullable=False),
        sa.Column("remit_line_id", sa.BigInteger(), nullable=True),
        sa.Column("code_qualifier", sa.String(length=2), nullable=False),
        sa.Column("remark_code", sa.String(length=10), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "remit_id"],
            ["remit.tenant_id", "remit.id"],
            name=op.f("fk_remit_remark_tenant_id_remit_id_remit"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "remit_line_id"],
            ["remit_line.tenant_id", "remit_line.id"],
            name=op.f("fk_remit_remark_tenant_id_remit_line_id_remit_line"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "source_file_id"],
            ["source_file.tenant_id", "source_file.id"],
            name=op.f("fk_remit_remark_tenant_id_source_file_id_source_file"),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_remit_remark_tenant_id_tenant")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_remit_remark")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_remit_remark_tenant_id_id")),
        sa.UniqueConstraint(
            "tenant_id",
            "remit_id",
            "remit_line_id",
            "remark_code",
            name=op.f("uq_remit_remark_tenant_id_remit_id_remit_line_id_remark_code"),
        ),
    )
    if op.get_context().dialect.name != "mssql":
        return  # T-SQL trigger; other dialects (test SQLite) skip it
    op.execute(
        """
        CREATE TRIGGER trg_event_append_only ON event
        INSTEAD OF UPDATE, DELETE
        AS
        BEGIN
            THROW 51000, 'event is append-only: UPDATE and DELETE are not allowed', 1;
        END
        """
    )


def downgrade() -> None:
    if op.get_context().dialect.name == "mssql":
        op.execute("DROP TRIGGER trg_event_append_only")
    op.drop_table("remit_remark")
    op.drop_table("adjustment")
    op.drop_table("remit_line")
    op.drop_table("remit")
    op.drop_table("plb_adjustment")
    op.drop_table("claim_line")
    op.drop_table("claim_dx")
    op.drop_table("ar_snapshot")
    op.drop_table("ack_277ca")
    op.drop_table("payment")
    op.drop_table("fee_schedule")
    op.drop_table("claim")
    op.drop_table("ack_999")
    op.drop_table("provider")
    op.drop_table("payer")
    op.drop_table("patient_ref")
    op.drop_table("event")
    op.drop_table("source_file")
    op.drop_table("tenant")
