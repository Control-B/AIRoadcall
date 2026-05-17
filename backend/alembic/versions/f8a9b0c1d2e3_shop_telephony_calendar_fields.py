"""shop_telephony_calendar_fields

Revision ID: f8a9b0c1d2e3
Revises: c3d4e5f6a7b9
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa

revision = "f8a9b0c1d2e3"
down_revision = "c3d4e5f6a7b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shop_customers", sa.Column("phone_onboarding_mode", sa.String(length=50), nullable=False, server_default="existing_number"))
    op.add_column("shop_customers", sa.Column("requested_area_code", sa.String(length=10), nullable=True))
    op.add_column("shop_customers", sa.Column("twilio_number_sid", sa.String(length=100), nullable=True))
    op.add_column("shop_customers", sa.Column("twilio_number_status", sa.String(length=50), nullable=False, server_default="not_requested"))
    op.add_column("shop_customers", sa.Column("retell_agent_id", sa.String(length=120), nullable=True))
    op.add_column("shop_customers", sa.Column("retell_phone_number_id", sa.String(length=120), nullable=True))
    op.add_column("shop_customers", sa.Column("retell_flow_id", sa.String(length=120), nullable=True))
    op.add_column("shop_customers", sa.Column("appointment_booking_enabled", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("shop_customers", sa.Column("calcom_calendar_url", sa.Text(), nullable=True))
    op.add_column("shop_customers", sa.Column("calcom_event_type_id", sa.String(length=120), nullable=True))
    op.add_column("shop_customers", sa.Column("after_hours_enabled", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("shop_customers", sa.Column("emergency_dispatch_enabled", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("shop_customers", sa.Column("missed_calls_recovered", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("shop_customers", sa.Column("appointments_booked", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("shop_customers", sa.Column("after_hours_jobs_captured", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("shop_customers", sa.Column("revenue_opportunities_cents", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_shop_customers_retell_agent_id", "shop_customers", ["retell_agent_id"])
    op.create_index("ix_shop_customers_twilio_number_status", "shop_customers", ["twilio_number_status"])


def downgrade() -> None:
    op.drop_index("ix_shop_customers_twilio_number_status", table_name="shop_customers")
    op.drop_index("ix_shop_customers_retell_agent_id", table_name="shop_customers")
    op.drop_column("shop_customers", "revenue_opportunities_cents")
    op.drop_column("shop_customers", "after_hours_jobs_captured")
    op.drop_column("shop_customers", "appointments_booked")
    op.drop_column("shop_customers", "missed_calls_recovered")
    op.drop_column("shop_customers", "emergency_dispatch_enabled")
    op.drop_column("shop_customers", "after_hours_enabled")
    op.drop_column("shop_customers", "calcom_event_type_id")
    op.drop_column("shop_customers", "calcom_calendar_url")
    op.drop_column("shop_customers", "appointment_booking_enabled")
    op.drop_column("shop_customers", "retell_flow_id")
    op.drop_column("shop_customers", "retell_phone_number_id")
    op.drop_column("shop_customers", "retell_agent_id")
    op.drop_column("shop_customers", "twilio_number_status")
    op.drop_column("shop_customers", "twilio_number_sid")
    op.drop_column("shop_customers", "requested_area_code")
    op.drop_column("shop_customers", "phone_onboarding_mode")
