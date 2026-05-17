"""retell_connections

Revision ID: f9a0b1c2d3e4
Revises: f8a9b0c1d2e3
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f9a0b1c2d3e4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "retell_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", sa.String(length=120), nullable=True),
        sa.Column("conversation_flow_id", sa.String(length=120), nullable=True),
        sa.Column("phone_number_id", sa.String(length=120), nullable=True),
        sa.Column("agent_name", sa.String(length=255), nullable=True),
        sa.Column("provisioning_status", sa.String(length=40), nullable=False, server_default="not_provisioned"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", name="uq_retell_connections_tenant"),
    )
    op.create_index("ix_retell_connections_tenant_id", "retell_connections", ["tenant_id"])
    op.create_index("ix_retell_connections_organization_id", "retell_connections", ["organization_id"])
    op.create_index("ix_retell_connections_agent_id", "retell_connections", ["agent_id"])
    op.create_index("ix_retell_connections_conversation_flow_id", "retell_connections", ["conversation_flow_id"])
    op.create_index("ix_retell_connections_provisioning_status", "retell_connections", ["provisioning_status"])


def downgrade() -> None:
    op.drop_index("ix_retell_connections_provisioning_status", table_name="retell_connections")
    op.drop_index("ix_retell_connections_conversation_flow_id", table_name="retell_connections")
    op.drop_index("ix_retell_connections_agent_id", table_name="retell_connections")
    op.drop_index("ix_retell_connections_organization_id", table_name="retell_connections")
    op.drop_index("ix_retell_connections_tenant_id", table_name="retell_connections")
    op.drop_table("retell_connections")
