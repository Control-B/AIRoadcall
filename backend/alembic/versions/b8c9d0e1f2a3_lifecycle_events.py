"""lifecycle events

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2025-02-14 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lifecycle_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=80), server_default="roadcall", nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("idempotency_key", sa.String(length=180), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("processing_status", sa.String(length=40), server_default="recorded", nullable=False),
        sa.Column("ghl_status", sa.String(length=40), nullable=True),
        sa.Column("ghl_result_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lifecycle_events_created_at", "lifecycle_events", ["created_at"], unique=False)
    op.create_index("ix_lifecycle_events_entity_id", "lifecycle_events", ["entity_id"], unique=False)
    op.create_index("ix_lifecycle_events_entity_type", "lifecycle_events", ["entity_type"], unique=False)
    op.create_index("ix_lifecycle_events_event_type", "lifecycle_events", ["event_type"], unique=False)
    op.create_index("ix_lifecycle_events_ghl_status", "lifecycle_events", ["ghl_status"], unique=False)
    op.create_index("ix_lifecycle_events_idempotency_key", "lifecycle_events", ["idempotency_key"], unique=True)
    op.create_index("ix_lifecycle_events_organization_id", "lifecycle_events", ["organization_id"], unique=False)
    op.create_index("ix_lifecycle_events_processing_status", "lifecycle_events", ["processing_status"], unique=False)
    op.create_index("ix_lifecycle_events_source", "lifecycle_events", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lifecycle_events_source", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_processing_status", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_organization_id", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_idempotency_key", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_ghl_status", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_event_type", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_entity_type", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_entity_id", table_name="lifecycle_events")
    op.drop_index("ix_lifecycle_events_created_at", table_name="lifecycle_events")
    op.drop_table("lifecycle_events")
