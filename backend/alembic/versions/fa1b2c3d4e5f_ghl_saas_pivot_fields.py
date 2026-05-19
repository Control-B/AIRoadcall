"""GHL SaaS pivot fields

Revision ID: fa1b2c3d4e5f
Revises: f9a0b1c2d3e4
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "fa1b2c3d4e5f"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {col["name"] for col in inspector.get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def _create_index_if_missing(name: str, table: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {idx["name"] for idx in inspector.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns)


def upgrade() -> None:
    _add_column_if_missing("ghl_tenant_mappings", sa.Column("agency_id", sa.String(length=120), nullable=True))
    _add_column_if_missing("ghl_tenant_mappings", sa.Column("ghl_user_id", sa.String(length=120), nullable=True))
    _add_column_if_missing("ghl_tenant_mappings", sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True))
    _add_column_if_missing("ghl_tenant_mappings", sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"))
    _add_column_if_missing("ghl_tenant_mappings", sa.Column("token_source", sa.String(length=40), nullable=False, server_default="manual"))
    _create_index_if_missing("ix_ghl_tenant_mappings_agency_id", "ghl_tenant_mappings", ["agency_id"])
    _create_index_if_missing("ix_ghl_tenant_mappings_ghl_user_id", "ghl_tenant_mappings", ["ghl_user_id"])
    _create_index_if_missing("ix_ghl_tenant_mappings_token_expires_at", "ghl_tenant_mappings", ["token_expires_at"])

    for column in (
        sa.Column("agency_id", sa.String(length=120), nullable=True),
        sa.Column("ghl_user_id", sa.String(length=120), nullable=True),
        sa.Column("calendar_id", sa.String(length=120), nullable=True),
        sa.Column("calendar_url", sa.Text(), nullable=True),
        sa.Column("pipeline_id", sa.String(length=120), nullable=True),
        sa.Column("workflow_status", sa.String(length=40), nullable=False, server_default="not_configured"),
        sa.Column("website_status", sa.String(length=40), nullable=False, server_default="not_configured"),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    ):
        _add_column_if_missing("ghl_connections", column)
    _create_index_if_missing("ix_ghl_connections_agency_id", "ghl_connections", ["agency_id"])
    _create_index_if_missing("ix_ghl_connections_ghl_user_id", "ghl_connections", ["ghl_user_id"])

    for column in (
        sa.Column("ghl_location_id", sa.String(length=120), nullable=True),
        sa.Column("ghl_company_id", sa.String(length=120), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=120), nullable=True),
        sa.Column("plan", sa.String(length=40), nullable=False, server_default="standard"),
    ):
        _add_column_if_missing("mechanic_accounts", column)
    _create_index_if_missing("ix_mechanic_accounts_ghl_location_id", "mechanic_accounts", ["ghl_location_id"])
    _create_index_if_missing("ix_mechanic_accounts_stripe_subscription_id", "mechanic_accounts", ["stripe_subscription_id"])
    _create_index_if_missing("ix_mechanic_accounts_plan", "mechanic_accounts", ["plan"])

    _add_column_if_missing("shop_profiles", sa.Column("ghl_calendar_id", sa.String(length=120), nullable=True))
    _add_column_if_missing("shop_profiles", sa.Column("ghl_calendar_url", sa.Text(), nullable=True))

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "service_requests" not in inspector.get_table_names():
        op.create_table(
            "service_requests",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True),
            sa.Column("mechanic_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mechanic_accounts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("ghl_contact_id", sa.String(length=120), nullable=True),
            sa.Column("ghl_opportunity_id", sa.String(length=120), nullable=True),
            sa.Column("caller_name", sa.String(length=255), nullable=True),
            sa.Column("caller_phone", sa.String(length=30), nullable=True),
            sa.Column("vehicle_type", sa.String(length=120), nullable=True),
            sa.Column("service_type", sa.String(length=120), nullable=True),
            sa.Column("urgency", sa.String(length=40), nullable=True),
            sa.Column("location_text", sa.Text(), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("call_summary", sa.Text(), nullable=True),
            sa.Column("transcript_url", sa.Text(), nullable=True),
            sa.Column("ai_status", sa.String(length=60), nullable=False, server_default="pending"),
            sa.Column("ghl_pipeline_stage", sa.String(length=120), nullable=True),
            sa.Column("status", sa.String(length=60), nullable=False, server_default="new"),
            sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
    for col in ("tenant_id", "mechanic_account_id", "ghl_contact_id", "ghl_opportunity_id", "caller_phone", "service_type", "urgency", "ai_status", "status", "created_at"):
        _create_index_if_missing(f"ix_service_requests_{col}", "service_requests", [col])


def downgrade() -> None:
    op.drop_table("service_requests")
    for table, cols in (
        ("shop_profiles", ("ghl_calendar_url", "ghl_calendar_id")),
        ("mechanic_accounts", ("plan", "stripe_subscription_id", "ghl_company_id", "ghl_location_id")),
        ("ghl_connections", ("scopes", "token_expires_at", "encrypted_refresh_token", "encrypted_access_token", "website_status", "workflow_status", "pipeline_id", "calendar_url", "calendar_id", "ghl_user_id", "agency_id")),
        ("ghl_tenant_mappings", ("token_source", "scopes", "token_expires_at", "ghl_user_id", "agency_id")),
    ):
        for col in cols:
            op.drop_column(table, col)
