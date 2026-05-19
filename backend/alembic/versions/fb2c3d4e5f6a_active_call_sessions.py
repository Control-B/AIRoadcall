"""Active call sessions for caller GPS location

Revision ID: fb2c3d4e5f6a
Revises: fa1b2c3d4e5f
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "fb2c3d4e5f6a"
down_revision = "fa1b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "active_call_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("call_provider", sa.String(length=40), nullable=False, server_default="retell"),
        sa.Column("provider_call_id", sa.String(length=255), nullable=False),
        sa.Column("caller_phone", sa.String(length=30), nullable=True),
        sa.Column("location_code", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="waiting_for_location"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=10), nullable=True),
        sa.Column("highway_or_exit", sa.Text(), nullable=True),
        sa.Column("manual_location_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider_call_id", name="uq_active_call_sessions_provider_call_id"),
        sa.UniqueConstraint("location_code", name="uq_active_call_sessions_location_code"),
    )
    for col in ("call_provider", "provider_call_id", "caller_phone", "location_code", "status", "city", "state", "created_at", "expires_at"):
        op.create_index(f"ix_active_call_sessions_{col}", "active_call_sessions", [col])


def downgrade() -> None:
    for col in ("call_provider", "provider_call_id", "caller_phone", "location_code", "status", "city", "state", "created_at", "expires_at"):
        op.drop_index(f"ix_active_call_sessions_{col}", table_name="active_call_sessions")
    op.drop_table("active_call_sessions")
