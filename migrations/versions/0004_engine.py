"""engine: policy, decision_record, approval_request

Revision ID: 0004
Revises: 0003

The decision engine's tables (M6). Generated from krisnai.model.engine.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False),
        sa.Column("autonomy_level", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("max_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("approver_role", sa.String(length=50), nullable=True),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint("mode IN ('shadow', 'live')", name=op.f("ck_policy_mode")),
        sa.CheckConstraint("autonomy_level BETWEEN 0 AND 4", name=op.f("ck_policy_level")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_policy_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_policy")),
        sa.UniqueConstraint("tenant_id", "action_type", name=op.f("uq_policy_tenant_id_action_type")),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_policy_tenant_id_id")),
    )
    op.create_table(
        "decision_record",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("agent_id", sa.String(length=50), nullable=False),
        sa.Column("agent_version", sa.String(length=20), nullable=False),
        sa.Column("event_id", sa.BigInteger(), nullable=False),
        sa.Column("trigger_type", sa.String(length=40), nullable=False),
        sa.Column("input_snapshot", sa.Text(), nullable=False),
        sa.Column("rules_fired", sa.Text(), nullable=False),
        sa.Column("model_id", sa.String(length=100), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("prompt_hash", sa.CHAR(length=64), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("materiality_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("action_payload", sa.Text(), nullable=False),
        sa.Column("autonomy_level", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=10), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False),
        sa.Column("approver", sa.String(length=100), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("execution_result", sa.String(length=500), nullable=True),
        sa.Column("verification_condition", sa.String(length=500), nullable=True),
        sa.Column("verification_result", sa.String(length=500), nullable=True),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint("mode IN ('shadow', 'live')", name=op.f("ck_decision_record_mode")),
        sa.CheckConstraint("autonomy_level BETWEEN 0 AND 4", name=op.f("ck_decision_record_level")),
        sa.ForeignKeyConstraint(
            ["tenant_id", "event_id"],
            ["event.tenant_id", "event.id"],
            name=op.f("fk_decision_record_tenant_id_event_id_event"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_decision_record_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_decision_record")),
        sa.UniqueConstraint(
            "tenant_id",
            "event_id",
            "agent_id",
            "action_type",
            name=op.f("uq_decision_record_tenant_id_event_id_agent_id_action_type"),
        ),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_decision_record_tenant_id_id")),
    )
    op.create_table(
        "approval_request",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("decision_record_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("approver_role", sa.String(length=50), nullable=True),
        sa.Column("decided_by", sa.String(length=100), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.text("SYSUTCDATETIME()"), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected')", name=op.f("ck_approval_request_status")),
        sa.ForeignKeyConstraint(
            ["tenant_id", "decision_record_id"],
            ["decision_record.tenant_id", "decision_record.id"],
            name=op.f("fk_approval_request_tenant_id_decision_record_id_decision_record"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.tenant_id"], name=op.f("fk_approval_request_tenant_id_tenant")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_approval_request")),
        sa.UniqueConstraint(
            "tenant_id", "decision_record_id", name=op.f("uq_approval_request_tenant_id_decision_record_id")
        ),
        sa.UniqueConstraint("tenant_id", "id", name=op.f("uq_approval_request_tenant_id_id")),
    )


def downgrade() -> None:
    op.drop_table("approval_request")
    op.drop_table("decision_record")
    op.drop_table("policy")
