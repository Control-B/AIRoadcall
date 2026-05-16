"""dispatch sessions

Revision ID: c3d4e5f6a7b9
Revises: f7b8c9d0e1f3
Create Date: 2026-05-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f6a7b9"
down_revision = "f7b8c9d0e1f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispatch_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("public_code", sa.String(length=20), nullable=False, unique=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("caller_phone_hash", sa.String(length=128), nullable=True),
        sa.Column("caller_phone_encrypted", sa.String(length=64), nullable=True),
        sa.Column("caller_phone_last4", sa.String(length=4), nullable=True),
        sa.Column("caller_name", sa.String(length=255), nullable=True),
        sa.Column("retell_call_id", sa.String(length=255), nullable=True),
        sa.Column("twilio_call_sid", sa.String(length=255), nullable=True),
        sa.Column("active_location_token_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("problem_type", sa.String(length=80), nullable=True),
        sa.Column("problem_description", sa.Text(), nullable=True),
        sa.Column("vehicle_type", sa.String(length=80), nullable=True),
        sa.Column("vehicle_description", sa.String(length=255), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("location_accuracy_m", sa.Float(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=10), nullable=True),
        sa.Column("location_source", sa.String(length=50), nullable=True),
        sa.Column("location_captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("selected_mechanic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_status", sa.String(length=40), nullable=False, server_default="not_required"),
        sa.Column("stripe_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dispatch_sessions_public_code", "dispatch_sessions", ["public_code"])
    op.create_index("ix_dispatch_sessions_retell_call_id", "dispatch_sessions", ["retell_call_id"])
    op.create_index("ix_dispatch_sessions_twilio_call_sid", "dispatch_sessions", ["twilio_call_sid"])
    op.create_index("ix_dispatch_sessions_phone_created", "dispatch_sessions", ["caller_phone_hash", "created_at"])
    op.create_index("ix_dispatch_sessions_status_updated", "dispatch_sessions", ["status", "updated_at"])

    op.create_table(
        "dispatch_location_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dispatch_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dispatch_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dispatch_location_tokens_session", "dispatch_location_tokens", ["dispatch_session_id"])
    op.create_index("ix_dispatch_location_tokens_token_hash", "dispatch_location_tokens", ["token_hash"])

    op.create_table(
        "dispatch_location_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dispatch_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dispatch_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("accuracy_m", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dispatch_location_events_session", "dispatch_location_events", ["dispatch_session_id"])

    op.create_table(
        "dispatch_match_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dispatch_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dispatch_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("search_level", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("selected_mechanic_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dispatch_match_results_session", "dispatch_match_results", ["dispatch_session_id"])

    op.create_table(
        "dispatch_session_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dispatch_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dispatch_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("actor_type", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_dispatch_session_events_session", "dispatch_session_events", ["dispatch_session_id"])
    op.create_index("ix_dispatch_session_events_type", "dispatch_session_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("dispatch_session_events")
    op.drop_table("dispatch_match_results")
    op.drop_table("dispatch_location_events")
    op.drop_table("dispatch_location_tokens")
    op.drop_table("dispatch_sessions")