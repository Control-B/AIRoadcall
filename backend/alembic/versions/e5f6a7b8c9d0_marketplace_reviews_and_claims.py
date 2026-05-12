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


def upgrade() -> None:
    # ── mechanics: add ownership/claim/verification flags ───────────────
    op.add_column("mechanics", sa.Column("claimed", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("mechanics", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("mechanics", sa.Column("claimed_by_organization_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("mechanics", sa.Column("claimed_by_phone", sa.String(length=30), nullable=True))
    op.add_column("mechanics", sa.Column("subscription_product", sa.String(length=60), nullable=True))
    op.add_column("mechanics", sa.Column("verified_listing", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("mechanics", sa.Column("submitted_by_public", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("mechanics", sa.Column("requires_admin_review", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_foreign_key(
        "fk_mechanics_claimed_org",
        "mechanics", "organizations",
        ["claimed_by_organization_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_mechanics_claimed", "mechanics", ["claimed"])
    op.create_index("ix_mechanics_requires_admin_review", "mechanics", ["requires_admin_review"])

    # ── mechanic_reviews ────────────────────────────────────────────────
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
    op.create_index("ix_mechanic_reviews_mechanic_id", "mechanic_reviews", ["mechanic_id"])
    op.create_index("ix_mechanic_reviews_reviewer_phone", "mechanic_reviews", ["reviewer_phone"])
    op.create_index("ix_mechanic_reviews_reviewer_ip", "mechanic_reviews", ["reviewer_ip"])
    op.create_index("ix_mechanic_reviews_created_at", "mechanic_reviews", ["created_at"])

    # ── mechanic_claims ─────────────────────────────────────────────────
    claim_method = sa.Enum(
        "phone_match", "subscriber_match", "manual_admin", "pending_review",
        name="mechanic_claim_method",
    )
    claim_status = sa.Enum("pending", "approved", "rejected", name="mechanic_claim_status")
    claim_method.create(op.get_bind(), checkfirst=True)
    claim_status.create(op.get_bind(), checkfirst=True)

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
    op.create_index("ix_mechanic_claims_mechanic_id", "mechanic_claims", ["mechanic_id"])
    op.create_index("ix_mechanic_claims_claimant_phone", "mechanic_claims", ["claimant_phone"])
    op.create_index("ix_mechanic_claims_status", "mechanic_claims", ["status"])
    op.create_index("ix_mechanic_claims_created_at", "mechanic_claims", ["created_at"])


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
