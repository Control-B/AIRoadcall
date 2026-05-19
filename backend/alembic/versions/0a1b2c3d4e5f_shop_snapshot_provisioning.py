"""shop snapshot provisioning

Revision ID: 0a1b2c3d4e5f
Revises: a1b2c3d4e5f7
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0a1b2c3d4e5f"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shop_profiles", sa.Column("business_hours", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("shop_profiles", sa.Column("intake_qualification", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.create_table(
        "shop_provisioning_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("snapshot_key", sa.String(length=80), nullable=False, server_default="shop_ai_intake_v1"),
        sa.Column("snapshot_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("readiness_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", name="uq_shop_provisioning_snapshots_tenant"),
    )
    for col in ("tenant_id", "organization_id", "snapshot_key", "status"):
        op.create_index(f"ix_shop_provisioning_snapshots_{col}", "shop_provisioning_snapshots", [col])

    op.create_table(
        "shop_messaging_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="twilio"),
        sa.Column("from_number", sa.String(length=30), nullable=True),
        sa.Column("messaging_service_sid", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="not_configured"),
        sa.Column("templates_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", name="uq_shop_messaging_configs_tenant"),
    )
    for col in ("tenant_id", "organization_id", "provider", "status"):
        op.create_index(f"ix_shop_messaging_configs_{col}", "shop_messaging_configs", [col])

    op.create_table(
        "shop_automation_workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("trigger_event", sa.String(length=120), nullable=False),
        sa.Column("channel", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="configured"),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "workflow_key", name="uq_shop_automation_workflows_tenant_key"),
    )
    for col in ("tenant_id", "organization_id", "workflow_key", "trigger_event", "channel", "enabled", "status"):
        op.create_index(f"ix_shop_automation_workflows_{col}", "shop_automation_workflows", [col])

    op.create_table(
        "shop_onboarding_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_key", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False, server_default="setup"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("manual_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "task_key", name="uq_shop_onboarding_tasks_tenant_key"),
    )
    for col in ("tenant_id", "organization_id", "task_key", "category", "status", "manual_required"):
        op.create_index(f"ix_shop_onboarding_tasks_{col}", "shop_onboarding_tasks", [col])


def downgrade() -> None:
    for table, cols in (
        ("shop_onboarding_tasks", ("tenant_id", "organization_id", "task_key", "category", "status", "manual_required")),
        ("shop_automation_workflows", ("tenant_id", "organization_id", "workflow_key", "trigger_event", "channel", "enabled", "status")),
        ("shop_messaging_configs", ("tenant_id", "organization_id", "provider", "status")),
        ("shop_provisioning_snapshots", ("tenant_id", "organization_id", "snapshot_key", "status")),
    ):
        for col in cols:
            op.drop_index(f"ix_{table}_{col}", table_name=table)
        op.drop_table(table)
    op.drop_column("shop_profiles", "intake_qualification")
    op.drop_column("shop_profiles", "business_hours")
