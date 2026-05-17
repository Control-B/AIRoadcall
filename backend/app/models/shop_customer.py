"""Shop Customer model — mechanic shops that subscribe to AI telephony.

Each shop gets a personalized AI agent that answers their phone calls,
qualifies leads, handles customer service, and dispatches jobs.

The agent is powered by Retell AI for voice and DO AI Gradient for text chat.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, Boolean, DateTime, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ShopCustomer(Base):
    __tablename__ = "shop_customers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Business Identity ──────────────────────────────────
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_phone: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True, index=True
    )
    business_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── AI Agent Configuration ─────────────────────────────
    # The system prompt template — personalized per shop
    agent_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Greeting the agent says when answering a call
    agent_greeting: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="Thank you for calling. How can I help you today?",
    )
    # ElevenLabs voice ID or Retell voice preset
    voice_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # DO AI Gradient agent/model ID for text chat
    text_agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Service Configuration ──────────────────────────────
    # What services this shop offers (for the agent to know)
    services_offered: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Service area description
    service_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Operating hours for the agent to reference
    hours_of_operation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Whether the shop does mobile/roadside
    offers_roadside: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Custom FAQ or knowledge base entries
    knowledge_base: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── SIP Configuration ────────────────────────────────────
    # The SIP phone number assigned to this shop
    sip_phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # SIP trunk ID for this shop's number
    sip_trunk_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Forward calls to this number if agent can't handle
    fallback_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # ── AI Telephony & Calendar Extension ──────────────────
    phone_onboarding_mode: Mapped[str] = mapped_column(
        String(50), default="existing_number", nullable=False
    )
    requested_area_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    twilio_number_sid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    twilio_number_status: Mapped[str] = mapped_column(
        String(50), default="not_requested", nullable=False
    )
    retell_agent_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    retell_phone_number_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    retell_flow_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    appointment_booking_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    calcom_calendar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    calcom_event_type_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    after_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    emergency_dispatch_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    missed_calls_recovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    appointments_booked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    after_hours_jobs_captured: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    revenue_opportunities_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Subscription & Status ──────────────────────────────
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    plan: Mapped[str] = mapped_column(
        String(50), default="starter", nullable=False
    )  # starter, pro, enterprise
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ── Usage Metrics ──────────────────────────────────────
    total_calls_handled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_leads_captured: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_chats_handled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_calls_forwarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Timestamps ─────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
