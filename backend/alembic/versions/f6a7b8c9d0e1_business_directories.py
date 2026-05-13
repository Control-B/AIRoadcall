"""Add trucking companies and national vendors directories.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trucking_companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=10), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("categories", sa.Text(), nullable=True),
        sa.Column("dot_number", sa.String(length=40), nullable=True),
        sa.Column("mc_number", sa.String(length=40), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("phone", name="uq_trucking_companies_phone"),
    )
    op.create_index("ix_trucking_companies_company_name", "trucking_companies", ["company_name"])
    op.create_index("ix_trucking_companies_phone", "trucking_companies", ["phone"])
    op.create_index("ix_trucking_companies_email", "trucking_companies", ["email"])
    op.create_index("ix_trucking_companies_city", "trucking_companies", ["city"])
    op.create_index("ix_trucking_companies_state", "trucking_companies", ["state"])
    op.create_index("ix_trucking_companies_dot_number", "trucking_companies", ["dot_number"])
    op.create_index("ix_trucking_companies_mc_number", "trucking_companies", ["mc_number"])

    op.create_table(
        "national_vendors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_name", sa.String(length=120), nullable=False),
        sa.Column("location_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("state", sa.String(length=10), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("categories", sa.Text(), nullable=True),
        sa.Column("services", sa.Text(), nullable=True),
        sa.Column("is_national_chain", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("brand_name", "phone", "address", name="uq_national_vendors_brand_phone_address"),
    )
    op.create_index("ix_national_vendors_brand_name", "national_vendors", ["brand_name"])
    op.create_index("ix_national_vendors_location_name", "national_vendors", ["location_name"])
    op.create_index("ix_national_vendors_phone", "national_vendors", ["phone"])
    op.create_index("ix_national_vendors_email", "national_vendors", ["email"])
    op.create_index("ix_national_vendors_city", "national_vendors", ["city"])
    op.create_index("ix_national_vendors_state", "national_vendors", ["state"])


def downgrade() -> None:
    for index_name in (
        "ix_national_vendors_state",
        "ix_national_vendors_city",
        "ix_national_vendors_email",
        "ix_national_vendors_phone",
        "ix_national_vendors_location_name",
        "ix_national_vendors_brand_name",
    ):
        op.drop_index(index_name, table_name="national_vendors")
    op.drop_table("national_vendors")

    for index_name in (
        "ix_trucking_companies_mc_number",
        "ix_trucking_companies_dot_number",
        "ix_trucking_companies_state",
        "ix_trucking_companies_city",
        "ix_trucking_companies_email",
        "ix_trucking_companies_phone",
        "ix_trucking_companies_company_name",
    ):
        op.drop_index(index_name, table_name="trucking_companies")
    op.drop_table("trucking_companies")
