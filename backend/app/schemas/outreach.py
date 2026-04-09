"""Pydantic schemas for the outreach/campaign system."""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ── Campaign Schemas ─────────────────────────────────────

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    channel: str = Field(default="sms", pattern="^(sms|email|voice)$")
    subject: Optional[str] = None
    body_template: str = Field(..., min_length=1)
    segment_filters: Optional[dict] = None
    scheduled_at: Optional[datetime] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    body_template: Optional[str] = None
    segment_filters: Optional[dict] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    channel: str
    status: str
    subject: Optional[str]
    body_template: str
    segment_filters: Optional[dict]
    total_targeted: int
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_replied: int
    total_demo_calls: int
    total_signups: int
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignStats(BaseModel):
    campaign_id: UUID
    name: str
    channel: str
    status: str
    total_targeted: int
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_replied: int
    total_demo_calls: int
    total_signups: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    reply_rate: float
    demo_rate: float
    signup_rate: float


# ── Message Schemas ──────────────────────────────────────

class OutreachMessageResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    mechanic_id: UUID
    channel: str
    to_address: str
    status: str
    provider_message_id: Optional[str]
    error_message: Optional[str]
    opened_at: Optional[datetime]
    clicked_at: Optional[datetime]
    replied_at: Optional[datetime]
    demo_called_at: Optional[datetime]
    signed_up_at: Optional[datetime]
    sent_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Segment / Targeting ──────────────────────────────────

class SegmentFilters(BaseModel):
    """Filters for targeting mechanics."""
    states: Optional[list[str]] = None
    roadside_only: bool = False
    min_rating: Optional[float] = None
    min_reviews: Optional[int] = None
    has_website: bool = False
    service_types: Optional[list[str]] = None
    lead_statuses: Optional[list[str]] = None  # new, contacted, interested, demo_scheduled, etc.
    limit: Optional[int] = None


class SegmentPreview(BaseModel):
    """Preview of how many mechanics match a segment."""
    total_matching: int
    sample: list[dict]  # first 10 matching mechanics


# ── Lead Tracking ────────────────────────────────────────

class MechanicLeadUpdate(BaseModel):
    lead_status: str = Field(..., pattern="^(new|contacted|interested|demo_scheduled|demo_completed|negotiating|signed_up|not_interested|do_not_contact)$")
    lead_notes: Optional[str] = None


# ── Outreach Dashboard Stats ────────────────────────────

class OutreachDashboardStats(BaseModel):
    total_mechanics: int
    total_with_phone: int
    total_with_email: int
    total_with_website: int
    total_campaigns: int
    total_messages_sent: int
    total_demos_booked: int
    total_signups: int
    lead_status_breakdown: dict[str, int]
    top_states: list[dict]
