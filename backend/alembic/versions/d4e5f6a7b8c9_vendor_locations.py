"""vendor_locations table for major chain truck service vendors

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    existing = {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    if not _table_exists("vendor_locations"):
        op.create_table(
            "vendor_locations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("brand_name", sa.String(120), nullable=False),
            sa.Column("location_name", sa.String(255), nullable=True),
            sa.Column("phone", sa.String(40), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("city", sa.String(120), nullable=True),
            sa.Column("state", sa.String(10), nullable=True),
            sa.Column("zip_code", sa.String(10), nullable=True),
            sa.Column("latitude", sa.Float(), nullable=True),
            sa.Column("longitude", sa.Float(), nullable=True),
            sa.Column("interstate", sa.String(40), nullable=True),
            sa.Column("exit_number", sa.String(40), nullable=True),
            sa.Column("services", postgresql.ARRAY(sa.String()), nullable=True),
            sa.Column("heavy_duty", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("rv_service", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("towing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("tire_service", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("mobile_service", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("is_24_7", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("source", sa.String(120), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("priority_score", sa.Integer(), nullable=False, server_default="80"),
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
    _create_index_if_missing("ix_vendor_locations_brand_name", "vendor_locations", ["brand_name"])
    _create_index_if_missing("ix_vendor_locations_city", "vendor_locations", ["city"])
    _create_index_if_missing("ix_vendor_locations_state", "vendor_locations", ["state"])
    _create_index_if_missing("ix_vendor_locations_interstate", "vendor_locations", ["interstate"])


def downgrade() -> None:
    op.drop_index("ix_vendor_locations_interstate", table_name="vendor_locations")
    op.drop_index("ix_vendor_locations_state", table_name="vendor_locations")
    op.drop_index("ix_vendor_locations_city", table_name="vendor_locations")
    op.drop_index("ix_vendor_locations_brand_name", table_name="vendor_locations")
    op.drop_table("vendor_locations")
