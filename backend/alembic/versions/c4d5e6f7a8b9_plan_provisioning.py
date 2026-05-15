"""Add plan-aware tenant provisioning tables.

Revision ID: c4d5e6f7a8b9
Revises: b8c9d0e1f2a3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c4d5e6f7a8b9"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=30), nullable=True),
        sa.Column("current_plan", sa.String(length=40), server_default="standard", nullable=False),
        sa.Column("subscription_status", sa.String(length=40), server_default="pending", nullable=False),
        sa.Column("onboarding_status", sa.String(length=40), server_default="not_started", nullable=False),
        sa.Column("setup_fee_status", sa.String(length=40), server_default="unpaid", nullable=False),
        sa.Column("enabled_features", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("organization_id", name="uq_tenants_organization"),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    for col in ("organization_id", "slug", "current_plan", "subscription_status", "onboarding_status", "setup_fee_status"):
        op.create_index(f"ix_tenants_{col}", "tenants", [col])

    op.create_table(
        "tenant_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.String(length=40), nullable=False),
        sa.Column("plan_name", sa.String(length=80), nullable=False),
        sa.Column("price_monthly", sa.Integer(), nullable=False),
        sa.Column("setup_fee", sa.Integer(), nullable=False),
        sa.Column("snapshot_id", sa.String(length=255), nullable=True),
        sa.Column("enabled_features", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("allowed_modules", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("webhook_permissions", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("dashboard_permissions", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("dispatch_permissions", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("ai_feature_permissions", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("tenant_id", "plan_id", "is_active"):
        op.create_index(f"ix_tenant_plans_{col}", "tenant_plans", [col])

    op.create_table(
        "ghl_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.String(length=120), nullable=True),
        sa.Column("subaccount_name", sa.String(length=255), nullable=True),
        sa.Column("snapshot_id", sa.String(length=255), nullable=True),
        sa.Column("snapshot_status", sa.String(length=40), server_default="pending", nullable=False),
        sa.Column("connection_status", sa.String(length=40), server_default="not_connected", nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("tenant_id", name="uq_ghl_connections_tenant"),
    )
    for col in ("tenant_id", "organization_id", "location_id", "snapshot_status", "connection_status"):
        op.create_index(f"ix_ghl_connections_{col}", "ghl_connections", [col])

    op.create_table(
        "provisioning_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=60), server_default="roadcall", nullable=False),
        sa.Column("status", sa.String(length=40), server_default="received", nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("tenant_id", "organization_id", "event_type", "source", "status", "next_retry_at", "created_at"):
        op.create_index(f"ix_provisioning_events_{col}", "provisioning_events", [col])

    op.create_table(
        "feature_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("source", sa.String(length=40), server_default="plan", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("tenant_id", "feature", name="uq_feature_flags_tenant_feature"),
    )
    for col in ("tenant_id", "feature", "enabled"):
        op.create_index(f"ix_feature_flags_{col}", "feature_flags", [col])

    op.create_table(
        "roadside_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roadside_incidents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_type", sa.String(length=60), server_default="gps_capture", nullable=False),
        sa.Column("status", sa.String(length=40), server_default="pending", nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("tenant_id", "organization_id", "incident_id", "session_type", "status", "created_at"):
        op.create_index(f"ix_roadside_sessions_{col}", "roadside_sessions", [col])

    op.create_table(
        "dispatch_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roadside_incidents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), server_default="recorded", nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("tenant_id", "organization_id", "incident_id", "job_id", "event_type", "status", "created_at"):
        op.create_index(f"ix_dispatch_events_{col}", "dispatch_events", [col])


def downgrade() -> None:
    for table, cols in (
        ("dispatch_events", ("tenant_id", "organization_id", "incident_id", "job_id", "event_type", "status", "created_at")),
        ("roadside_sessions", ("tenant_id", "organization_id", "incident_id", "session_type", "status", "created_at")),
        ("feature_flags", ("tenant_id", "feature", "enabled")),
        ("provisioning_events", ("tenant_id", "organization_id", "event_type", "source", "status", "next_retry_at", "created_at")),
        ("ghl_connections", ("tenant_id", "organization_id", "location_id", "snapshot_status", "connection_status")),
        ("tenant_plans", ("tenant_id", "plan_id", "is_active")),
        ("tenants", ("organization_id", "slug", "current_plan", "subscription_status", "onboarding_status", "setup_fee_status")),
    ):
        for col in cols:
            op.drop_index(f"ix_{table}_{col}", table_name=table)
        op.drop_table(table)