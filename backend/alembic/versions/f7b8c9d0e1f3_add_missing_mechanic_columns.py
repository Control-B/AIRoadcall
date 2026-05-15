"""add missing mechanic columns: zip_code, availability_status, response_score

Revision ID: f7b8c9d0e1f3
Revises: f6a7b8c9d0e1
Create Date: 2026-05-15

These columns were declared in the Mechanic model but were never migrated to the
database, causing /api/mechanics/marketplace and several other endpoints that
use SQLAlchemy ORM eager-load to throw `column mechanics.zip_code does not exist`
500 errors on every request.
"""
from alembic import op
import sqlalchemy as sa


revision = "f7b8c9d0e1f3"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {col["name"] for col in insp.get_columns("mechanics")}

    if "zip_code" not in existing:
        op.add_column("mechanics", sa.Column("zip_code", sa.String(length=20), nullable=True))
        op.create_index("ix_mechanics_zip_code", "mechanics", ["zip_code"], unique=False)

    if "availability_status" not in existing:
        op.add_column(
            "mechanics",
            sa.Column(
                "availability_status",
                sa.String(length=50),
                nullable=True,
                server_default="unknown",
            ),
        )
        op.create_index(
            "ix_mechanics_availability_status",
            "mechanics",
            ["availability_status"],
            unique=False,
        )

    if "response_score" not in existing:
        op.add_column("mechanics", sa.Column("response_score", sa.Float(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {col["name"] for col in insp.get_columns("mechanics")}
    existing_indexes = {idx["name"] for idx in insp.get_indexes("mechanics")}

    if "response_score" in existing:
        op.drop_column("mechanics", "response_score")
    if "availability_status" in existing:
        if "ix_mechanics_availability_status" in existing_indexes:
            op.drop_index("ix_mechanics_availability_status", table_name="mechanics")
        op.drop_column("mechanics", "availability_status")
    if "zip_code" in existing:
        if "ix_mechanics_zip_code" in existing_indexes:
            op.drop_index("ix_mechanics_zip_code", table_name="mechanics")
        op.drop_column("mechanics", "zip_code")
