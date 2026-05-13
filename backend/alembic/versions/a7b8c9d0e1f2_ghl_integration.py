"""Add GoHighLevel integration tables.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ghl_tenant_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("location_id", sa.String(length=120), nullable=False),
        sa.Column("subaccount_name", sa.String(length=255), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("encrypted_webhook_secret", sa.Text(), nullable=True),
        sa.Column("pipeline_id", sa.String(length=120), nullable=True),
        sa.Column("default_workflow_id", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("organization_id", name="uq_ghl_tenant_mappings_organization"),
        sa.UniqueConstraint("location_id", name="uq_ghl_tenant_mappings_location"),
    )
    op.create_index("ix_ghl_tenant_mappings_organization_id", "ghl_tenant_mappings", ["organization_id"])
    op.create_index("ix_ghl_tenant_mappings_location_id", "ghl_tenant_mappings", ["location_id"])

    op.create_table(
        "ghl_contact_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_mapping_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ghl_tenant_mappings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ghl_contact_id", sa.String(length=120), nullable=False),
        sa.Column("roadcall_entity_type", sa.String(length=60), nullable=False),
        sa.Column("roadcall_entity_id", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("tenant_mapping_id", "roadcall_entity_type", "roadcall_entity_id", name="uq_ghl_contact_links_roadcall_entity"),
        sa.UniqueConstraint("tenant_mapping_id", "ghl_contact_id", name="uq_ghl_contact_links_contact"),
    )
    for col in ("tenant_mapping_id", "ghl_contact_id", "roadcall_entity_type", "roadcall_entity_id", "email", "phone"):
        op.create_index(f"ix_ghl_contact_links_{col}", "ghl_contact_links", [col])

    op.create_table(
        "ghl_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_mapping_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ghl_tenant_mappings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("external_event_id", sa.String(length=255), nullable=True),
        sa.Column("signature_valid", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("processing_status", sa.String(length=40), server_default="received", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("tenant_mapping_id", "event_type", "external_event_id", "processing_status", "created_at"):
        op.create_index(f"ix_ghl_webhook_events_{col}", "ghl_webhook_events", [col])

    op.create_table(
        "ghl_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_mapping_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ghl_tenant_mappings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("tenant_mapping_id", "organization_id", "action", "entity_type", "entity_id", "created_at"):
        op.create_index(f"ix_ghl_audit_logs_{col}", "ghl_audit_logs", [col])

    op.create_table(
        "ghl_retry_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_mapping_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ghl_tenant_mappings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("method", sa.String(length=10), server_default="POST", nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("headers_json", postgresql.JSONB(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column("status", sa.String(length=40), server_default="pending", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("tenant_mapping_id", "action", "status", "next_attempt_at"):
        op.create_index(f"ix_ghl_retry_queue_{col}", "ghl_retry_queue", [col])


def downgrade() -> None:
    for table, cols in (
        ("ghl_retry_queue", ("tenant_mapping_id", "action", "status", "next_attempt_at")),
        ("ghl_audit_logs", ("tenant_mapping_id", "organization_id", "action", "entity_type", "entity_id", "created_at")),
        ("ghl_webhook_events", ("tenant_mapping_id", "event_type", "external_event_id", "processing_status", "created_at")),
        ("ghl_contact_links", ("tenant_mapping_id", "ghl_contact_id", "roadcall_entity_type", "roadcall_entity_id", "email", "phone")),
    ):
        for col in cols:
            op.drop_index(f"ix_{table}_{col}", table_name=table)
        op.drop_table(table)
    op.drop_index("ix_ghl_tenant_mappings_location_id", table_name="ghl_tenant_mappings")
    op.drop_index("ix_ghl_tenant_mappings_organization_id", table_name="ghl_tenant_mappings")
    op.drop_table("ghl_tenant_mappings")
