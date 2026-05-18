from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class PlanConfigView(BaseModel):
    id: str
    name: str
    price_monthly: int
    setup_fee: int
    enabled_features: list[str]
    ghl_snapshot_id: str
    allowed_modules: list[str]
    webhook_permissions: list[str]
    dashboard_permissions: list[str]
    dispatch_permissions: list[str]
    ai_feature_permissions: list[str]


class ProvisionTenantIn(BaseModel):
    plan_id: str = Field(pattern="^(starter|growth|pro|standard|professional|premium)$")
    organization_id: str | None = None
    organization_name: str
    organization_slug: str | None = None
    vertical_type: str = "shops"
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    website: str | None = None
    subscription_status: str = "active"
    setup_fee_status: str = "unpaid"
    onboarding_status: str = "not_started"
    ghl_location_id: str | None = None
    ghl_subaccount_name: str | None = None
    ghl_snapshot_id: str | None = None
    provision_retell: bool = True
    retell_agent_id: str | None = None
    retell_conversation_flow_id: str | None = None
    retell_phone_number_id: str | None = None
    retell_voice_id: str = "11labs-Lily"
    access_token: str | None = Field(default=None, repr=False)
    refresh_token: str | None = Field(default=None, repr=False)
    webhook_secret: str | None = Field(default=None, repr=False)
    external_customer_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GHLConnectionView(BaseModel):
    location_id: str | None = None
    subaccount_name: str | None = None
    snapshot_id: str | None = None
    snapshot_status: str
    connection_status: str
    last_synced_at: datetime | None = None


class RetellConnectionView(BaseModel):
    agent_id: str | None = None
    conversation_flow_id: str | None = None
    phone_number_id: str | None = None
    agent_name: str | None = None
    provisioning_status: str
    last_error: str | None = None
    last_synced_at: datetime | None = None
    dynamic_variables: dict[str, Any] = Field(default_factory=dict)


class TenantView(BaseModel):
    id: str
    organization_id: str
    name: str
    slug: str
    contact_email: str | None = None
    contact_phone: str | None = None
    current_plan: str
    subscription_status: str
    onboarding_status: str
    setup_fee_status: str
    enabled_features: list[str]
    locked_features: list[str] = Field(default_factory=list)
    ghl_connection: GHLConnectionView | None = None
    retell_connection: RetellConnectionView | None = None
    latest_activity_type: str | None = None
    latest_activity_status: str | None = None
    latest_activity_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProvisionTenantOut(BaseModel):
    ok: bool = True
    tenant: TenantView
    plan: PlanConfigView
    provisioning_event_id: str | None = None
    ghl_result: dict[str, Any] | None = None
    retell_result: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class TenantListResponse(BaseModel):
    tenants: list[TenantView]
    plans: list[PlanConfigView]


class TenantPlanUpdateIn(BaseModel):
    plan_id: str = Field(pattern="^(starter|growth|pro|standard|professional|premium)$")
    subscription_status: str | None = None
    setup_fee_status: str | None = None
    onboarding_status: str | None = None
    ghl_snapshot_id: str | None = None


class TenantGHLRepairIn(BaseModel):
    location_id: str | None = None
    subaccount_name: str | None = None
    snapshot_id: str | None = None
    snapshot_status: str | None = None
    connection_status: str | None = None


class TenantRetellProvisionIn(BaseModel):
    agent_id: str | None = None
    conversation_flow_id: str | None = None
    phone_number_id: str | None = None
    voice_id: str = "11labs-Lily"
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeatureFlagUpdateIn(BaseModel):
    feature: str
    enabled: bool
    reason: str | None = None


class ProvisioningEventView(BaseModel):
    id: str
    tenant_id: str | None = None
    organization_id: str | None = None
    event_type: str
    source: str
    status: str
    error_message: str | None = None
    retry_count: int
    created_at: datetime


class DispatchEventView(BaseModel):
    id: str
    tenant_id: str | None = None
    organization_id: str | None = None
    incident_id: str | None = None
    job_id: str | None = None
    event_type: str
    status: str
    payload_json: dict[str, Any] | None = None
    created_at: datetime


class RoadsideSessionView(BaseModel):
    id: str
    tenant_id: str
    organization_id: str
    incident_id: str | None = None
    session_type: str
    status: str
    payload_json: dict[str, Any] | None = None
    created_at: datetime


class PlanAccessView(BaseModel):
    allowed: bool
    tenant_id: str | None = None
    plan_id: str | None = None
    feature: str
    upgrade_required: str | None = None
    detail: str