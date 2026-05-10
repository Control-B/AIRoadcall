"""mechanic_matching_fields

Revision ID: b2c3d4e5f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-10

"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f7a8"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "mechanics",
        sa.Column("emergency_service", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "mechanics",
        sa.Column("service_radius_miles", sa.Integer(), nullable=False, server_default="50"),
    )
    op.add_column(
        "mechanics",
        sa.Column("priority_score", sa.Integer(), nullable=False, server_default="50"),
    )
    op.create_index("ix_mechanics_emergency_service", "mechanics", ["emergency_service"])
    op.create_index("ix_mechanics_priority_score", "mechanics", ["priority_score"])



def downgrade() -> None:
    op.drop_index("ix_mechanics_priority_score", table_name="mechanics")
    op.drop_index("ix_mechanics_emergency_service", table_name="mechanics")
    op.drop_column("mechanics", "priority_score")
    op.drop_column("mechanics", "service_radius_miles")
    op.drop_column("mechanics", "emergency_service")
