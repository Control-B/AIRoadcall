"""Pydantic schemas for the Shop Telephony product."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Shop Customer Schemas ────────────────────────────────


class ShopCustomerCreate(BaseModel):
    """Create a new shop telephony customer."""

    business_name: str = Field(..., min_length=1, max_length=255)
    owner_name: Optional[str] = None
    business_phone: str = Field(..., min_length=10, max_length=30)
    business_email: Optional[str] = None
    business_address: Optional[str] = None

    # Agent configuration
    agent_prompt: Optional[str] = None  # Will be auto-generated if not provided
    agent_greeting: str = "Thank you for calling. How can I help you today?"
    voice_id: Optional[str] = None
    text_agent_id: Optional[str] = None

    # Service config
    services_offered: Optional[list[str]] = None
    service_area: Optional[str] = None
    hours_of_operation: Optional[dict] = None
    offers_roadside: bool = False
    knowledge_base: Optional[dict] = None

    # SIP config
    sip_phone_number: Optional[str] = None
    sip_trunk_id: Optional[str] = None
    fallback_phone: Optional[str] = None

    # AI telephony/calendar extension
    phone_onboarding_mode: str = "existing_number"
    requested_area_code: Optional[str] = None
    twilio_number_sid: Optional[str] = None
    twilio_number_status: str = "not_requested"
    retell_agent_id: Optional[str] = None
    retell_phone_number_id: Optional[str] = None
    retell_flow_id: Optional[str] = None
    appointment_booking_enabled: bool = True
    calcom_calendar_url: Optional[str] = None
    calcom_event_type_id: Optional[str] = None
    after_hours_enabled: bool = True
    emergency_dispatch_enabled: bool = False

    plan: str = "starter"


class ShopCustomerUpdate(BaseModel):
    """Update an existing shop telephony customer."""

    business_name: Optional[str] = None
    owner_name: Optional[str] = None
    business_phone: Optional[str] = None
    business_email: Optional[str] = None
    business_address: Optional[str] = None

    agent_prompt: Optional[str] = None
    agent_greeting: Optional[str] = None
    voice_id: Optional[str] = None
    text_agent_id: Optional[str] = None

    services_offered: Optional[list[str]] = None
    service_area: Optional[str] = None
    hours_of_operation: Optional[dict] = None
    offers_roadside: Optional[bool] = None
    knowledge_base: Optional[dict] = None

    sip_phone_number: Optional[str] = None
    sip_trunk_id: Optional[str] = None
    fallback_phone: Optional[str] = None

    phone_onboarding_mode: Optional[str] = None
    requested_area_code: Optional[str] = None
    twilio_number_sid: Optional[str] = None
    twilio_number_status: Optional[str] = None
    retell_agent_id: Optional[str] = None
    retell_phone_number_id: Optional[str] = None
    retell_flow_id: Optional[str] = None
    appointment_booking_enabled: Optional[bool] = None
    calcom_calendar_url: Optional[str] = None
    calcom_event_type_id: Optional[str] = None
    after_hours_enabled: Optional[bool] = None
    emergency_dispatch_enabled: Optional[bool] = None

    active: Optional[bool] = None
    plan: Optional[str] = None


class ShopCustomerResponse(BaseModel):
    """Shop customer response."""

    id: UUID
    business_name: str
    owner_name: Optional[str]
    business_phone: str
    business_email: Optional[str]
    business_address: Optional[str]

    agent_greeting: str
    voice_id: Optional[str]
    text_agent_id: Optional[str]

    services_offered: Optional[list]
    service_area: Optional[str]
    hours_of_operation: Optional[dict]
    offers_roadside: bool

    sip_phone_number: Optional[str]
    fallback_phone: Optional[str]

    phone_onboarding_mode: str
    requested_area_code: Optional[str]
    twilio_number_status: str
    retell_agent_id: Optional[str]
    retell_phone_number_id: Optional[str]
    retell_flow_id: Optional[str]
    appointment_booking_enabled: bool
    calcom_calendar_url: Optional[str]
    calcom_event_type_id: Optional[str]
    after_hours_enabled: bool
    emergency_dispatch_enabled: bool

    active: bool
    plan: str

    total_calls_handled: int
    total_leads_captured: int
    total_chats_handled: int
    total_calls_forwarded: int
    missed_calls_recovered: int
    appointments_booked: int
    after_hours_jobs_captured: int
    revenue_opportunities_cents: int

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Call Log Schemas ─────────────────────────────────────


class ShopCallLogResponse(BaseModel):
    """Call log entry response."""

    id: UUID
    shop_id: UUID
    caller_phone: str
    caller_name: Optional[str]
    direction: str
    channel: str

    duration_seconds: Optional[int]
    intent: Optional[str]
    intent_summary: Optional[str]

    is_qualified_lead: bool
    lead_score: Optional[float]
    vehicle_info: Optional[dict]

    appointment_scheduled: bool
    forwarded_to_human: bool
    callback_requested: bool

    collected_data: Optional[dict]
    status: str

    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Text Chat Schemas ────────────────────────────────────


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str


class ChatRequest(BaseModel):
    """Text chat request to a shop's AI agent."""

    shop_id: UUID
    message: str
    conversation_id: Optional[str] = None  # For multi-turn conversations
    caller_phone: Optional[str] = None  # If from SMS integration


class ChatResponse(BaseModel):
    """Text chat response from the AI agent."""

    reply: str
    conversation_id: str
    intent: Optional[str] = None
    is_qualified_lead: bool = False
    suggested_actions: Optional[list[str]] = None


# ── Incoming Call Routing ────────────────────────────────


class IncomingCallRequest(BaseModel):
    """Incoming call webhook from SIP trunk."""

    called_number: str  # The shop's SIP number that was called
    caller_number: str  # The caller's phone number
    call_id: Optional[str] = None
    trunk_id: Optional[str] = None
