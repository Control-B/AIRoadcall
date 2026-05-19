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


class ShopSnapshotProvisionIn(BaseModel):
    snapshot_key: str = Field(default="shop_ai_intake_v1", max_length=80)
    plan_id: str = Field(default="growth", pattern="^(starter|growth|pro|standard|professional|premium)$")
    business_name: str = Field(min_length=2, max_length=255)
    organization_slug: str | None = Field(default=None, max_length=120)
    owner_name: str | None = Field(default=None, max_length=255)
    owner_email: EmailStr
    owner_phone: str | None = Field(default=None, max_length=30)
    shop_phone: str | None = Field(default=None, max_length=30)
    website: str | None = Field(default=None, max_length=500)
    address: str | None = None
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=40)
    timezone: str | None = Field(default="America/New_York", max_length=80)
    services_offered: list[str] = Field(default_factory=list)
    disabled_services: list[str] = Field(default_factory=list)
    service_area: str | None = None
    service_radius_miles: int = Field(default=50, ge=1, le=500)
    business_hours: dict[str, Any] | None = None
    intake_qualification: dict[str, Any] = Field(default_factory=dict)
    offers_mobile_service: bool = True
    offers_247_service: bool = False
    hourly_rate: str | None = Field(default=None, max_length=80)
    fallback_phone: str | None = Field(default=None, max_length=30)
    calcom_calendar_url: str | None = None
    calcom_event_type_id: str | None = Field(default=None, max_length=120)
    calcom_username: str | None = Field(default=None, max_length=120)
    calcom_event_slug: str | None = Field(default="roadcall-service", max_length=120)
    calcom_api_key: str | None = Field(default=None, repr=False)
    calcom_base_url: str | None = Field(default=None, max_length=255)
    twilio_from_number: str | None = Field(default=None, max_length=30)
    twilio_messaging_service_sid: str | None = Field(default=None, max_length=120)
    sms_templates: dict[str, str] = Field(default_factory=dict)
    retell_agent_id: str | None = Field(default=None, max_length=120)
    retell_conversation_flow_id: str | None = Field(default=None, max_length=120)
    retell_phone_number_id: str | None = Field(default=None, max_length=120)
    retell_phone_number: str | None = Field(default=None, max_length=30)
    sip_trunk_id: str | None = Field(default=None, max_length=120)
    call_forwarding_phone: str | None = Field(default=None, max_length=30)
    call_routing: dict[str, Any] = Field(default_factory=dict)
    disabled_workflows: list[str] = Field(default_factory=list)
    workflow_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    attach_existing_leads: bool = True
    lead_source_id: str | None = Field(default=None, max_length=120)
    estimated_lead_count: int | None = Field(default=None, ge=0)
    imported_leads: list[dict[str, Any]] = Field(default_factory=list)
    subscription_status: str = Field(default="pending_checkout", max_length=40)
    setup_fee_status: str = Field(default="unpaid", max_length=40)
    stripe_customer_id: str | None = Field(default=None, max_length=120)
    stripe_subscription_id: str | None = Field(default=None, max_length=120)
    stripe_price_id: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ShopSnapshotRecordView(BaseModel):
    id: str
    snapshot_key: str
    snapshot_version: int
    status: str
    snapshot_json: dict[str, Any]
    readiness_json: dict[str, Any]
    updated_at: datetime


class ShopMessagingConfigView(BaseModel):
    provider: str
    from_number: str | None = None
    messaging_service_sid: str | None = None
    status: str
    templates_json: dict[str, Any]


class ShopAutomationWorkflowView(BaseModel):
    id: str
    workflow_key: str
    name: str
    trigger_event: str
    channel: str
    enabled: bool
    status: str
    config_json: dict[str, Any]


class ShopOnboardingTaskView(BaseModel):
    id: str
    task_key: str
    title: str
    category: str
    status: str
    manual_required: bool
    instructions: str | None = None
    metadata_json: dict[str, Any]
    completed_at: datetime | None = None


class ShopSnapshotProvisionOut(BaseModel):
    ok: bool = True
    tenant: TenantView
    snapshot: ShopSnapshotRecordView
    messaging: ShopMessagingConfigView
    retell_connection: RetellConnectionView | None = None
    workflows: list[ShopAutomationWorkflowView]
    onboarding_tasks: list[ShopOnboardingTaskView]
    readiness: dict[str, Any]


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