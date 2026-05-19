from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class BillingPlanView(BaseModel):
    id: str
    name: str
    price_monthly: int
    setup_fee: int
    included_leads: int | None = None
    stripe_price_id_configured: bool
    features: list[str]


class CheckoutSessionCreateIn(BaseModel):
    plan_id: str = Field(pattern="^(starter|growth|pro|standard|professional|premium)$")
    business_name: str = Field(min_length=2, max_length=255)
    owner_name: str | None = Field(default=None, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    website: str | None = Field(default=None, max_length=500)


class CheckoutSessionCreateOut(BaseModel):
    checkout_url: str
    checkout_session_id: str
    tenant_id: str
    dashboard_url: str


class CustomerPortalCreateIn(BaseModel):
    tenant_id: str
    dashboard_token: str


class ResendDashboardLinkIn(BaseModel):
    email: EmailStr
    vertical: str = Field(default="shop", pattern="^(shop|fleet|admin)$")


class ResendDashboardLinkOut(BaseModel):
    status: str = "ok"
    message: str


class CustomerPortalCreateOut(BaseModel):
    portal_url: str


class ShopProfileUpdateIn(BaseModel):
    business_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = None
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=40)
    website: str | None = Field(default=None, max_length=500)
    services_offered: list[str] = Field(default_factory=list)
    service_area: str | None = None
    service_radius_miles: int = Field(default=50, ge=1, le=500)
    business_hours: dict[str, Any] | None = None
    intake_qualification: dict[str, Any] | None = None
    offers_mobile_service: bool = True
    offers_247_service: bool = False
    hourly_rate: str | None = Field(default=None, max_length=80)
    fallback_phone: str | None = Field(default=None, max_length=30)
    calcom_calendar_url: str | None = None
    calcom_api_key: str | None = None
    calcom_event_type_id: str | None = Field(default=None, max_length=120)
    calcom_base_url: str | None = Field(default=None, max_length=255)
    calcom_default_timezone: str | None = Field(default=None, max_length=80)


class SubscriptionView(BaseModel):
    plan_id: str
    status: str
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False


class AIAgentView(BaseModel):
    activation_status: str
    retell_agent_id: str | None = None
    retell_conversation_flow_id: str | None = None
    agent_name: str | None = None
    last_error: str | None = None


class UsageView(BaseModel):
    usage_month: str
    calls_handled: int
    leads_allocated: int
    included_leads: int
    overage_leads: int


class DashboardCallSummaryView(BaseModel):
    id: str
    call_id: str | None = None
    retell_call_id: str | None = None
    caller_phone: str | None = None
    caller_name: str | None = None
    call_status: str | None = None
    lead_status: str | None = None
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    problem_type: str | None = None
    vehicle_type: str | None = None
    urgency: str | None = None
    duration_seconds: int | None = None
    created_at: datetime


class MechanicDashboardView(BaseModel):
    tenant_id: str
    business_name: str
    account_status: str
    subscription: SubscriptionView | None = None
    profile: dict[str, Any] | None = None
    profile_complete: bool
    ai_agent: AIAgentView | None = None
    usage: UsageView | None = None
    call_summaries: list[DashboardCallSummaryView] = Field(default_factory=list)
    activation_steps: list[dict[str, str | bool]]


class AIActivationOut(BaseModel):
    activation_status: str
    detail: str
    retell_agent_id: str | None = None
    retell_conversation_flow_id: str | None = None
