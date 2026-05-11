"""lead_captures table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f7a8
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lead_captures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("vertical", sa.String(30), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("unsubscribed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("welcome_sent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_lead_captures_email", "lead_captures", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_lead_captures_email", table_name="lead_captures")
    op.drop_table("lead_captures")
