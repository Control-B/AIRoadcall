from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MechanicAccount(Base):
    __tablename__ = "mechanic_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_mechanic_accounts_tenant"),
        UniqueConstraint("dashboard_token", name="uq_mechanic_accounts_dashboard_token"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dashboard_token: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending_checkout", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ShopProfile(Base):
    __tablename__ = "shop_profiles"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_shop_profiles_tenant"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    services_offered: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    service_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    service_radius_miles: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    offers_mobile_service: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    offers_247_service: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hourly_rate: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fallback_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    calcom_calendar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Cal.com OSS / SaaS API integration so the Retell shop agent can book in real time.
    calcom_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    calcom_event_type_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    calcom_base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calcom_default_timezone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    profile_status: Mapped[str] = mapped_column(String(40), default="incomplete", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class StripeSubscription(Base):
    __tablename__ = "stripe_subscriptions"
    __table_args__ = (UniqueConstraint("stripe_subscription_id", name="uq_stripe_subscriptions_subscription_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    mechanic_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("mechanic_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    stripe_price_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class AIAgent(Base):
    __tablename__ = "ai_agents"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_ai_agents_tenant"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    retell_connection_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("retell_connections.id", ondelete="SET NULL"), nullable=True, index=True)
    retell_agent_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    retell_conversation_flow_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activation_status: Mapped[str] = mapped_column(String(50), default="not_subscribed", nullable=False, index=True)
    voice_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class RetellNumber(Base):
    __tablename__ = "retell_numbers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    retell_phone_number_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    routing_status: Mapped[str] = mapped_column(String(40), default="not_connected", nullable=False, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class SipTrunk(Base):
    __tablename__ = "sip_trunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(60), default="retell", nullable=False, index=True)
    trunk_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False, index=True)
    forwarding_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ShopCall(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    retell_call_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    caller_phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    call_status: Mapped[str] = mapped_column(String(40), default="received", nullable=False, index=True)
    lead_status: Mapped[str] = mapped_column(String(40), default="unqualified", nullable=False, index=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class CallTranscript(Base):
    __tablename__ = "call_transcripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ShopCallSummary(Base):
    __tablename__ = "shop_call_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    problem_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    lead_value_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class LeadAllocation(Base):
    __tablename__ = "lead_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_id: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    allocation_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    lead_type: Mapped[str] = mapped_column(String(60), default="roadside", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="allocated", nullable=False, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class PlanUsage(Base):
    __tablename__ = "plan_usage"
    __table_args__ = (UniqueConstraint("tenant_id", "usage_month", name="uq_plan_usage_tenant_month"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    usage_month: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    calls_handled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_allocated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    included_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overage_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
