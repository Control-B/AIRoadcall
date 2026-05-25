"""Caller profiles keyed by phone

Revision ID: fc3d4e5f6a7b
Revises: fb2c3d4e5f6a
Create Date: 2026-05-25

"""
from alembic import op
import sqlalchemy as sa


revision = "fc3d4e5f6a7b"
down_revision = "fb2c3d4e5f6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "caller_profiles",
        sa.Column("phone", sa.String(length=20), primary_key=True),
        sa.Column("driver_name", sa.String(length=160), nullable=True),
        sa.Column("vehicle_type", sa.String(length=120), nullable=True),
        sa.Column("truck_number", sa.String(length=60), nullable=True),
        sa.Column("trailer_number", sa.String(length=60), nullable=True),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_call_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("caller_profiles")
