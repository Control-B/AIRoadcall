"""Add mechanic_reviews + mechanic_claims tables and ownership flags on mechanics.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns(table_name)}
    return column_name in columns


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    constraints = sa.inspect(bind).get_foreign_keys(table_name)
    return constraint_name in {constraint["name"] for constraint in constraints}


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    existing = {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}
    if index_name not in existing:
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    # ── mechanics: add ownership/claim/verification flags ───────────────
    mechanic_columns = (
        ("claimed", sa.Column("claimed", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("claimed_at", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True)),
        ("claimed_by_organization_id", sa.Column("claimed_by_organization_id", postgresql.UUID(as_uuid=True), nullable=True)),
        ("claimed_by_phone", sa.Column("claimed_by_phone", sa.String(length=30), nullable=True)),
        ("subscription_product", sa.Column("subscription_product", sa.String(length=60), nullable=True)),
        ("verified_listing", sa.Column("verified_listing", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("submitted_by_public", sa.Column("submitted_by_public", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("requires_admin_review", sa.Column("requires_admin_review", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
    )
    for column_name, column in mechanic_columns:
        if not _column_exists("mechanics", column_name):
            op.add_column("mechanics", column)
    if not _constraint_exists("mechanics", "fk_mechanics_claimed_org"):
        op.create_foreign_key(
            "fk_mechanics_claimed_org",
            "mechanics", "organizations",
            ["claimed_by_organization_id"], ["id"],
            ondelete="SET NULL",
        )
    _create_index_if_missing("ix_mechanics_claimed", "mechanics", ["claimed"])
    _create_index_if_missing("ix_mechanics_requires_admin_review", "mechanics", ["requires_admin_review"])

    # ── mechanic_reviews ────────────────────────────────────────────────
    if not _table_exists("mechanic_reviews"):
        op.create_table(
            "mechanic_reviews",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("mechanic_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("mechanics.id", ondelete="CASCADE"), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("reviewer_name", sa.String(length=120), nullable=True),
            sa.Column("reviewer_phone", sa.String(length=30), nullable=True),
            sa.Column("reviewer_ip", sa.String(length=64), nullable=True),
            sa.Column("verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("flagged", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
    _create_index_if_missing("ix_mechanic_reviews_mechanic_id", "mechanic_reviews", ["mechanic_id"])
    _create_index_if_missing("ix_mechanic_reviews_reviewer_phone", "mechanic_reviews", ["reviewer_phone"])
    _create_index_if_missing("ix_mechanic_reviews_reviewer_ip", "mechanic_reviews", ["reviewer_ip"])
    _create_index_if_missing("ix_mechanic_reviews_created_at", "mechanic_reviews", ["created_at"])

    # ── mechanic_claims ─────────────────────────────────────────────────
    claim_method = sa.Enum(
        "phone_match", "subscriber_match", "manual_admin", "pending_review",
        name="mechanic_claim_method",
    )
    claim_status = sa.Enum("pending", "approved", "rejected", name="mechanic_claim_status")
    claim_method.create(op.get_bind(), checkfirst=True)
    claim_status.create(op.get_bind(), checkfirst=True)

    if not _table_exists("mechanic_claims"):
        op.create_table(
            "mechanic_claims",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("mechanic_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("mechanics.id", ondelete="CASCADE"), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
            sa.Column("claimant_name", sa.String(length=255), nullable=False),
            sa.Column("claimant_phone", sa.String(length=30), nullable=False),
            sa.Column("claimant_email", sa.String(length=255), nullable=True),
            sa.Column("subscription_product", sa.String(length=60), nullable=True),
            sa.Column("method", claim_method, nullable=False, server_default="pending_review"),
            sa.Column("status", claim_status, nullable=False, server_default="pending"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("verification_token", sa.String(length=64), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                      server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
    _create_index_if_missing("ix_mechanic_claims_mechanic_id", "mechanic_claims", ["mechanic_id"])
    _create_index_if_missing("ix_mechanic_claims_claimant_phone", "mechanic_claims", ["claimant_phone"])
    _create_index_if_missing("ix_mechanic_claims_status", "mechanic_claims", ["status"])
    _create_index_if_missing("ix_mechanic_claims_created_at", "mechanic_claims", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_mechanic_claims_created_at", table_name="mechanic_claims")
    op.drop_index("ix_mechanic_claims_status", table_name="mechanic_claims")
    op.drop_index("ix_mechanic_claims_claimant_phone", table_name="mechanic_claims")
    op.drop_index("ix_mechanic_claims_mechanic_id", table_name="mechanic_claims")
    op.drop_table("mechanic_claims")
    sa.Enum(name="mechanic_claim_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="mechanic_claim_method").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_mechanic_reviews_created_at", table_name="mechanic_reviews")
    op.drop_index("ix_mechanic_reviews_reviewer_ip", table_name="mechanic_reviews")
    op.drop_index("ix_mechanic_reviews_reviewer_phone", table_name="mechanic_reviews")
    op.drop_index("ix_mechanic_reviews_mechanic_id", table_name="mechanic_reviews")
    op.drop_table("mechanic_reviews")

    op.drop_index("ix_mechanics_requires_admin_review", table_name="mechanics")
    op.drop_index("ix_mechanics_claimed", table_name="mechanics")
    op.drop_constraint("fk_mechanics_claimed_org", "mechanics", type_="foreignkey")
    for col in (
        "requires_admin_review", "submitted_by_public", "verified_listing",
        "subscription_product", "claimed_by_phone", "claimed_by_organization_id",
        "claimed_at", "claimed",
    ):
        op.drop_column("mechanics", col)
