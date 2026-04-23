"""initial_schema

Revision ID: 69e9a459
Revises:
Create Date: 2026-04-23

Creates all tables:
  - mechanics (35k+ roadside mechanics with geo coordinates)
  - jobs
  - dispatch_attempts
  - tracking_sessions
  - audit_events
  - call_summaries, outreach_campaigns, shop_customers, shop_call_logs, outreach_messages
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "69e9a459"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enums ─────────────────────────────────────────────────────────────────
    job_status_enum = postgresql.ENUM(
        "created", "awaiting_driver_location", "awaiting_payment_authorization",
        "payment_authorized", "matching_mechanics", "calling_mechanics",
        "mechanic_assigned", "mechanic_en_route", "mechanic_arrived",
        "completed", "canceled",
        name="job_status_enum",
    )
    payment_status_enum = postgresql.ENUM(
        "not_started", "pending", "authorized", "capture_required",
        "captured", "released", "failed",
        name="payment_status_enum",
    )
    issue_type_enum = postgresql.ENUM(
        "flat_tire", "dead_battery", "lockout", "fuel_delivery", "tow_needed",
        "engine_trouble", "overheating", "accident", "stuck_off_road", "other",
        name="issue_type_enum",
    )
    dispatch_status_enum = postgresql.ENUM(
        "queued", "calling", "accepted", "declined", "unavailable",
        "no_answer", "timed_out", "superseded",
        name="dispatch_status_enum",
    )
    tracking_status_enum = postgresql.ENUM(
        "not_started", "pending", "active", "paused", "arrived", "ended",
        name="tracking_status_enum",
    )

    job_status_enum.create(op.get_bind(), checkfirst=True)
    payment_status_enum.create(op.get_bind(), checkfirst=True)
    issue_type_enum.create(op.get_bind(), checkfirst=True)
    dispatch_status_enum.create(op.get_bind(), checkfirst=True)
    tracking_status_enum.create(op.get_bind(), checkfirst=True)

    # ── mechanics ─────────────────────────────────────────────────────────────
    op.create_table(
        "mechanics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False, unique=True),
        sa.Column("service_types", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("vehicle_types_supported", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("base_lat", sa.Float(), nullable=False),
        sa.Column("base_lng", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("accepts_mobile_roadside", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_known_lat", sa.Float(), nullable=True),
        sa.Column("last_known_lng", sa.Float(), nullable=True),
        sa.Column("last_location_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("source_confidence", sa.Float(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("hours_of_operation", sa.JSON(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("state", sa.String(10), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_dispatches", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("successful_dispatches", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_mechanics_city", "mechanics", ["city"])
    op.create_index("ix_mechanics_state", "mechanics", ["state"])
    op.create_index("ix_mechanics_base_lat", "mechanics", ["base_lat"])
    op.create_index("ix_mechanics_base_lng", "mechanics", ["base_lng"])
    # Composite geo index for bounding-box queries
    op.create_index("ix_mechanics_geo", "mechanics", ["base_lat", "base_lng"])

    # ── jobs ──────────────────────────────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("public_job_id", sa.String(20), nullable=False, unique=True),
        sa.Column("magic_link_token", sa.Text(), nullable=False, unique=True),
        sa.Column("magic_link_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("driver_name", sa.String(255), nullable=False),
        sa.Column("driver_phone", sa.String(30), nullable=False),
        sa.Column("vehicle_type", sa.String(100), nullable=True),
        sa.Column("issue_type", sa.Enum("flat_tire", "dead_battery", "lockout", "fuel_delivery",
                                        "tow_needed", "engine_trouble", "overheating", "accident",
                                        "stuck_off_road", "other",
                                        name="issue_type_enum", create_constraint=False), nullable=False),
        sa.Column("issue_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("created", "awaiting_driver_location",
                                     "awaiting_payment_authorization", "payment_authorized",
                                     "matching_mechanics", "calling_mechanics", "mechanic_assigned",
                                     "mechanic_en_route", "mechanic_arrived", "completed", "canceled",
                                     name="job_status_enum", create_constraint=False), nullable=False),
        sa.Column("payment_status", sa.Enum("not_started", "pending", "authorized",
                                             "capture_required", "captured", "released", "failed",
                                             name="payment_status_enum", create_constraint=False), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True, unique=True),
        sa.Column("payment_hold_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("driver_lat", sa.Float(), nullable=True),
        sa.Column("driver_lng", sa.Float(), nullable=True),
        sa.Column("driver_city", sa.String(120), nullable=True),
        sa.Column("driver_state", sa.String(10), nullable=True),
        sa.Column("driver_address", sa.Text(), nullable=True),
        sa.Column("assigned_mechanic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_jobs_public_job_id", "jobs", ["public_job_id"])
    op.create_index("ix_jobs_magic_link_token", "jobs", ["magic_link_token"])

    # ── dispatch_attempts ─────────────────────────────────────────────────────
    op.create_table(
        "dispatch_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("mechanic_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("mechanics.id"), nullable=False),
        sa.Column("rank_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dispatch_status", sa.Enum("queued", "calling", "accepted", "declined",
                                              "unavailable", "no_answer", "timed_out", "superseded",
                                              name="dispatch_status_enum", create_constraint=False), nullable=False),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("availability_eta_minutes", sa.Integer(), nullable=True),
        sa.Column("response_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dispatch_attempts_job_id", "dispatch_attempts", ["job_id"])
    op.create_index("ix_dispatch_attempts_mechanic_id", "dispatch_attempts", ["mechanic_id"])

    # ── tracking_sessions ─────────────────────────────────────────────────────
    op.create_table(
        "tracking_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("mechanic_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("mechanics.id"), nullable=False),
        sa.Column("tracking_status", sa.Enum("not_started", "pending", "active", "paused",
                                              "arrived", "ended",
                                              name="tracking_status_enum", create_constraint=False), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_driver_view_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tracking_sessions_job_id", "tracking_sessions", ["job_id"])

    # ── audit_events ──────────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_audit_events_job_id", "audit_events", ["job_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])

    # ── call_summaries ────────────────────────────────────────────────────────
    op.create_table(
        "call_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("retell_call_id", sa.String(255), nullable=True, unique=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("caller_phone", sa.String(30), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("call_status", sa.String(50), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── shop_customers ────────────────────────────────────────────────────────
    op.create_table(
        "shop_customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── shop_call_logs ────────────────────────────────────────────────────────
    op.create_table(
        "shop_call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("shop_id", sa.String(255), nullable=True),
        sa.Column("retell_call_id", sa.String(255), nullable=True),
        sa.Column("caller_phone", sa.String(30), nullable=True),
        sa.Column("call_status", sa.String(50), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── outreach_campaigns ────────────────────────────────────────────────────
    op.create_table(
        "outreach_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── outreach_messages ─────────────────────────────────────────────────────
    op.create_table(
        "outreach_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("outreach_campaigns.id"), nullable=True),
        sa.Column("recipient_phone", sa.String(30), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("outreach_messages")
    op.drop_table("outreach_campaigns")
    op.drop_table("shop_call_logs")
    op.drop_table("shop_customers")
    op.drop_table("call_summaries")
    op.drop_table("audit_events")
    op.drop_table("tracking_sessions")
    op.drop_table("dispatch_attempts")
    op.drop_table("jobs")
    op.drop_table("mechanics")
    for enum_name in ["job_status_enum", "payment_status_enum", "issue_type_enum",
                       "dispatch_status_enum", "tracking_status_enum"]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
