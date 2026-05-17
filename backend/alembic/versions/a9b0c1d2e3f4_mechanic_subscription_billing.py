"""Add mechanic subscription billing tables.

Revision ID: a9b0c1d2e3f4
Revises: f9a0b1c2d3e4
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a9b0c1d2e3f4"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "mechanic_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("dashboard_token", sa.String(120), nullable=False),
        sa.Column("stripe_customer_id", sa.String(120), nullable=True),
        sa.Column("status", sa.String(40), server_default="pending_checkout", nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", name="uq_mechanic_accounts_tenant"),
        sa.UniqueConstraint("dashboard_token", name="uq_mechanic_accounts_dashboard_token"),
    )
    for col in ("tenant_id", "organization_id", "email", "dashboard_token", "stripe_customer_id", "status"):
        op.create_index(f"ix_mechanic_accounts_{col}", "mechanic_accounts", [col])

    op.create_table(
        "shop_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("state", sa.String(40), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("services_offered", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("service_area", sa.Text(), nullable=True),
        sa.Column("service_radius_miles", sa.Integer(), server_default="50", nullable=False),
        sa.Column("offers_mobile_service", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("offers_247_service", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("hourly_rate", sa.String(80), nullable=True),
        sa.Column("fallback_phone", sa.String(30), nullable=True),
        sa.Column("calcom_calendar_url", sa.Text(), nullable=True),
        sa.Column("profile_status", sa.String(40), server_default="incomplete", nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", name="uq_shop_profiles_tenant"),
    )
    for col in ("tenant_id", "organization_id", "profile_status"):
        op.create_index(f"ix_shop_profiles_{col}", "shop_profiles", [col])

    op.create_table(
        "stripe_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mechanic_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mechanic_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_id", sa.String(40), nullable=False),
        sa.Column("stripe_customer_id", sa.String(120), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(120), nullable=False),
        sa.Column("stripe_price_id", sa.String(120), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("stripe_subscription_id", name="uq_stripe_subscriptions_subscription_id"),
    )
    for col in ("tenant_id", "mechanic_account_id", "plan_id", "stripe_customer_id", "stripe_subscription_id", "stripe_price_id", "status"):
        op.create_index(f"ix_stripe_subscriptions_{col}", "stripe_subscriptions", [col])

    op.create_table(
        "ai_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("retell_connection_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("retell_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("retell_agent_id", sa.String(120), nullable=True),
        sa.Column("retell_conversation_flow_id", sa.String(120), nullable=True),
        sa.Column("agent_name", sa.String(255), nullable=True),
        sa.Column("activation_status", sa.String(50), server_default="not_subscribed", nullable=False),
        sa.Column("voice_id", sa.String(120), nullable=True),
        sa.Column("prompt_snapshot", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("tenant_id", name="uq_ai_agents_tenant"),
    )
    for col in ("tenant_id", "retell_connection_id", "retell_agent_id", "activation_status"):
        op.create_index(f"ix_ai_agents_{col}", "ai_agents", [col])

    op.create_table(
        "retell_numbers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("retell_phone_number_id", sa.String(120), nullable=True),
        sa.Column("phone_number", sa.String(30), nullable=True),
        sa.Column("routing_status", sa.String(40), server_default="not_connected", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        *_timestamps(),
    )
    for col in ("tenant_id", "retell_phone_number_id", "phone_number", "routing_status"):
        op.create_index(f"ix_retell_numbers_{col}", "retell_numbers", [col])

    op.create_table(
        "sip_trunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(60), server_default="retell", nullable=False),
        sa.Column("trunk_id", sa.String(120), nullable=True),
        sa.Column("status", sa.String(40), server_default="pending", nullable=False),
        sa.Column("forwarding_number", sa.String(30), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        *_timestamps(),
    )
    for col in ("tenant_id", "provider", "trunk_id", "status"):
        op.create_index(f"ix_sip_trunks_{col}", "sip_trunks", [col])

    op.create_table(
        "calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("retell_call_id", sa.String(120), nullable=True),
        sa.Column("caller_phone", sa.String(30), nullable=True),
        sa.Column("call_status", sa.String(40), server_default="received", nullable=False),
        sa.Column("lead_status", sa.String(40), server_default="unqualified", nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("tenant_id", "retell_call_id", "caller_phone", "call_status", "lead_status", "created_at"):
        op.create_index(f"ix_calls_{col}", "calls", [col])

    op.create_table(
        "call_transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transcript_text", sa.Text(), nullable=True),
        sa.Column("transcript_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("call_id", "tenant_id"):
        op.create_index(f"ix_call_transcripts_{col}", "call_transcripts", [col])

    op.create_table(
        "shop_call_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("problem_type", sa.String(80), nullable=True),
        sa.Column("vehicle_type", sa.String(80), nullable=True),
        sa.Column("urgency", sa.String(40), nullable=True),
        sa.Column("lead_value_cents", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("call_id", "tenant_id", "problem_type", "urgency", "created_at"):
        op.create_index(f"ix_shop_call_summaries_{col}", "shop_call_summaries", [col])

    op.create_table(
        "lead_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_id", sa.String(40), nullable=False),
        sa.Column("allocation_month", sa.String(7), nullable=False),
        sa.Column("lead_type", sa.String(60), server_default="roadside", nullable=False),
        sa.Column("status", sa.String(40), server_default="allocated", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    for col in ("tenant_id", "call_id", "plan_id", "allocation_month", "lead_type", "status", "created_at"):
        op.create_index(f"ix_lead_allocations_{col}", "lead_allocations", [col])

    op.create_table(
        "plan_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("usage_month", sa.String(7), nullable=False),
        sa.Column("calls_handled", sa.Integer(), server_default="0", nullable=False),
        sa.Column("leads_allocated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("included_leads", sa.Integer(), server_default="0", nullable=False),
        sa.Column("overage_leads", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("tenant_id", "usage_month", name="uq_plan_usage_tenant_month"),
    )
    for col in ("tenant_id", "usage_month"):
        op.create_index(f"ix_plan_usage_{col}", "plan_usage", [col])


def downgrade() -> None:
    for table, cols in (
        ("plan_usage", ("tenant_id", "usage_month")),
        ("lead_allocations", ("tenant_id", "call_id", "plan_id", "allocation_month", "lead_type", "status", "created_at")),
        ("shop_call_summaries", ("call_id", "tenant_id", "problem_type", "urgency", "created_at")),
        ("call_transcripts", ("call_id", "tenant_id")),
        ("calls", ("tenant_id", "retell_call_id", "caller_phone", "call_status", "lead_status", "created_at")),
        ("sip_trunks", ("tenant_id", "provider", "trunk_id", "status")),
        ("retell_numbers", ("tenant_id", "retell_phone_number_id", "phone_number", "routing_status")),
        ("ai_agents", ("tenant_id", "retell_connection_id", "retell_agent_id", "activation_status")),
        ("stripe_subscriptions", ("tenant_id", "mechanic_account_id", "plan_id", "stripe_customer_id", "stripe_subscription_id", "stripe_price_id", "status")),
        ("shop_profiles", ("tenant_id", "organization_id", "profile_status")),
        ("mechanic_accounts", ("tenant_id", "organization_id", "email", "dashboard_token", "stripe_customer_id", "status")),
    ):
        for col in cols:
            op.drop_index(f"ix_{table}_{col}", table_name=table)
        op.drop_table(table)
