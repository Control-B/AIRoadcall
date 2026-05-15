"""provider geospatial matching fields

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-05-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("mechanics", "base_lat", existing_type=sa.Float(), nullable=True)
    op.alter_column("mechanics", "base_lng", existing_type=sa.Float(), nullable=True)
    op.add_column("mechanics", sa.Column("zip_code", sa.String(length=20), nullable=True))
    op.add_column("mechanics", sa.Column("availability_status", sa.String(length=50), nullable=True, server_default="unknown"))
    op.add_column("mechanics", sa.Column("response_score", sa.Float(), nullable=True))
    op.create_index("ix_mechanics_base_lat_lng", "mechanics", ["base_lat", "base_lng"], unique=False)
    op.create_index("ix_mechanics_zip_code", "mechanics", ["zip_code"], unique=False)
    op.create_index("ix_mechanics_availability_status", "mechanics", ["availability_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mechanics_availability_status", table_name="mechanics")
    op.drop_index("ix_mechanics_zip_code", table_name="mechanics")
    op.drop_index("ix_mechanics_base_lat_lng", table_name="mechanics")
    op.drop_column("mechanics", "response_score")
    op.drop_column("mechanics", "availability_status")
    op.drop_column("mechanics", "zip_code")
    op.alter_column("mechanics", "base_lng", existing_type=sa.Float(), nullable=False)
    op.alter_column("mechanics", "base_lat", existing_type=sa.Float(), nullable=False)
