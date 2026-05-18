"""shop_profile_calcom_credentials

Adds Cal.com API integration fields to shop_profiles so the per-tenant
Retell Shop Receptionist can read live availability and create real
bookings on behalf of the caller.

Revision ID: a1b2c3d4e5f7
Revises: f9a0b1c2d3e4
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f7"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shop_profiles", sa.Column("calcom_api_key", sa.Text(), nullable=True))
    op.add_column("shop_profiles", sa.Column("calcom_event_type_id", sa.String(length=120), nullable=True))
    op.add_column("shop_profiles", sa.Column("calcom_base_url", sa.String(length=255), nullable=True))
    op.add_column("shop_profiles", sa.Column("calcom_default_timezone", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("shop_profiles", "calcom_default_timezone")
    op.drop_column("shop_profiles", "calcom_base_url")
    op.drop_column("shop_profiles", "calcom_event_type_id")
    op.drop_column("shop_profiles", "calcom_api_key")
