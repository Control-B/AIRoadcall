from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.config import get_settings


class PlanTier(StrEnum):
    widget_only = "widget_only"
    ai_telephony = "ai_telephony"
    widget_voice = "widget_voice"
    enterprise = "enterprise"
    standard = "standard"
    professional = "professional"
    advanced = "advanced"


class PlanFeature(StrEnum):
    ai_widget = "ai_widget"
    faq_assistant = "faq_assistant"
    booking_assistant = "booking_assistant"
    ai_answering = "ai_answering"
    ai_intake = "ai_intake"
    lead_qualification = "lead_qualification"
    missed_call_text_back = "missed_call_text_back"
    crm_integration = "crm_integration"
    basic_crm_sync = "basic_crm_sync"
    lead_capture = "lead_capture"
    call_summaries = "call_summaries"
    sms_follow_up = "sms_follow_up"
    basic_ai_summaries = "basic_ai_summaries"
    saved_truck_profile = "saved_truck_profile"
    preferred_providers = "preferred_providers"
    dispatch_tracking = "dispatch_tracking"
    map_view = "map_view"
    provider_directory = "provider_directory"
    trucking_company_profile = "trucking_company_profile"
    website_widget = "website_widget"
    ai_website = "ai_website"
    web_chat = "web_chat"
    crm = "crm"
    pipelines = "pipelines"
    workflows = "workflows"
    form_builder = "form_builder"
    calendars = "calendars"
    reputation_management = "reputation_management"
    mobile_app = "mobile_app"
    customer_portal = "customer_portal"
    multi_user_access = "multi_user_access"
    enhanced_automation = "enhanced_automation"
    fleet_dashboard = "fleet_dashboard"
    advanced_reporting = "advanced_reporting"
    email_marketing = "email_marketing"
    survey_builder = "survey_builder"
    content_automation = "content_automation"
    social_media_marketing = "social_media_marketing"
    marketing_funnels = "marketing_funnels"
    crm_campaigns = "crm_campaigns"
    priority_support = "priority_support"
    growth_automation = "growth_automation"
    ghl_saas_mode = "ghl_saas_mode"
    snapshot_deployment = "snapshot_deployment"
    funnels = "funnels"
    advanced_ai_workflows = "advanced_ai_workflows"
    appointment_scheduling = "appointment_scheduling"
    smart_routing = "smart_routing"
    website_voice_assistant = "website_voice_assistant"
    advanced_qualification = "advanced_qualification"
    advanced_analytics = "advanced_analytics"
    team_notifications = "team_notifications"
    custom_workflows = "custom_workflows"
    customer_follow_up = "customer_follow_up"
    review_automation = "review_automation"
    multi_location_support = "multi_location_support"
    gps_capture = "gps_capture"
    roadside_intake = "roadside_intake"
    dispatch_workflow = "dispatch_workflow"
    driver_intake = "driver_intake"
    mechanic_assignment = "mechanic_assignment"
    fleet_notification = "fleet_notification"
    dispatch_dashboard = "dispatch_dashboard"
    emergency_routing = "emergency_routing"
    real_time_roadside_status = "real_time_roadside_status"
    external_dispatch_api = "external_dispatch_api"
    api_ready_infrastructure = "api_ready_infrastructure"


PLAN_ALIASES = {
    "chat": PlanTier.widget_only,
    "ai_chat": PlanTier.widget_only,
    "ai-chat": PlanTier.widget_only,
    "starter": PlanTier.widget_only,
    "widget": PlanTier.widget_only,
    "widget-only": PlanTier.widget_only,
    "voice": PlanTier.ai_telephony,
    "ai-phone": PlanTier.ai_telephony,
    "ai-telephony": PlanTier.ai_telephony,
    "widget+voice": PlanTier.widget_voice,
    "widget-ai-telephony": PlanTier.widget_voice,
    "driver": PlanTier.enterprise,
    "driver_pro": PlanTier.enterprise,
    "driver-pro": PlanTier.enterprise,
    "trucking": PlanTier.enterprise,
    "growth": PlanTier.standard,
    "premium": PlanTier.professional,
    "pro": PlanTier.professional,
}


@dataclass(frozen=True)
class PlanConfig:
    id: PlanTier
    name: str
    price_monthly: float
    setup_fee: float
    ecosystem: str
    billing_system: str
    onboarding_mode: str
    uses_saas_mode: bool
    automatic_subaccount_provisioning: bool
    features: tuple[PlanFeature, ...]
    snapshot_id: str
    allowed_modules: tuple[str, ...]
    webhook_permissions: tuple[str, ...]
    dashboard_permissions: tuple[str, ...]
    dispatch_permissions: tuple[str, ...]
    ai_feature_permissions: tuple[str, ...]


WIDGET_ONLY_FEATURES = (
    PlanFeature.ai_widget,
    PlanFeature.faq_assistant,
    PlanFeature.lead_capture,
    PlanFeature.appointment_scheduling,
)

AI_TELEPHONY_FEATURES = (
    PlanFeature.ai_answering,
    PlanFeature.ai_intake,
    PlanFeature.lead_qualification,
    PlanFeature.missed_call_text_back,
    PlanFeature.call_summaries,
    PlanFeature.lead_capture,
)

WIDGET_VOICE_FEATURES = WIDGET_ONLY_FEATURES + AI_TELEPHONY_FEATURES

ENTERPRISE_TRUCKING_FEATURES = (
    PlanFeature.map_view,
    PlanFeature.provider_directory,
    PlanFeature.trucking_company_profile,
    PlanFeature.roadside_intake,
    PlanFeature.dispatch_tracking,
    PlanFeature.preferred_providers,
)

STANDARD_FEATURES = WIDGET_VOICE_FEATURES + (
    PlanFeature.ai_website,
    PlanFeature.website_widget,
    PlanFeature.crm,
    PlanFeature.pipelines,
    PlanFeature.workflows,
    PlanFeature.calendars,
    PlanFeature.reputation_management,
    PlanFeature.ghl_saas_mode,
    PlanFeature.snapshot_deployment,
)

PROFESSIONAL_FEATURES = STANDARD_FEATURES + (
    PlanFeature.mobile_app,
    PlanFeature.customer_portal,
    PlanFeature.multi_user_access,
)

ADVANCED_FEATURES = PROFESSIONAL_FEATURES + (
    PlanFeature.social_media_marketing,
    PlanFeature.content_automation,
    PlanFeature.marketing_funnels,
    PlanFeature.crm_campaigns,
)


def _plan(
    *,
    id: PlanTier,
    name: str,
    price_monthly: float,
    setup_fee: float,
    ecosystem: str,
    billing_system: str,
    onboarding_mode: str,
    uses_saas_mode: bool,
    features: tuple[PlanFeature, ...],
    allowed_modules: tuple[str, ...],
    webhook_permissions: tuple[str, ...],
    dashboard_permissions: tuple[str, ...],
    ai_feature_permissions: tuple[str, ...],
    snapshot_id: str = "",
    dispatch_permissions: tuple[str, ...] = (),
) -> PlanConfig:
    return PlanConfig(
        id=id,
        name=name,
        price_monthly=price_monthly,
        setup_fee=setup_fee,
        ecosystem=ecosystem,
        billing_system=billing_system,
        onboarding_mode=onboarding_mode,
        uses_saas_mode=uses_saas_mode,
        automatic_subaccount_provisioning=uses_saas_mode,
        features=features,
        snapshot_id=snapshot_id,
        allowed_modules=allowed_modules,
        webhook_permissions=webhook_permissions,
        dashboard_permissions=dashboard_permissions,
        dispatch_permissions=dispatch_permissions,
        ai_feature_permissions=ai_feature_permissions,
    )


def get_plan_configs() -> dict[str, PlanConfig]:
    settings = get_settings()
    return {
        "widget_only": _plan(
            id=PlanTier.widget_only,
            name="Widget Only",
            price_monthly=99.99,
            setup_fee=49.99,
            ecosystem="simple_ai_services",
            billing_system="stripe",
            onboarding_mode="lightweight_widget",
            uses_saas_mode=False,
            features=WIDGET_ONLY_FEATURES,
            allowed_modules=("ai_widget", "lead_capture", "booking"),
            webhook_permissions=("subscription", "widget.lead", "widget.conversation"),
            dashboard_permissions=("dashboard.read", "widget.read", "leads.read"),
            ai_feature_permissions=("ai.widget", "ai.faq", "ai.booking_assistant"),
        ),
        "ai_telephony": _plan(
            id=PlanTier.ai_telephony,
            name="AI Telephony Only",
            price_monthly=99.99,
            setup_fee=49.99,
            ecosystem="simple_ai_services",
            billing_system="stripe",
            onboarding_mode="lightweight_voice",
            uses_saas_mode=False,
            features=AI_TELEPHONY_FEATURES,
            allowed_modules=("ai_phone", "lead_capture", "sms", "call_summaries"),
            webhook_permissions=("subscription", "call.summary", "missed_call"),
            dashboard_permissions=("dashboard.read", "calls.read", "leads.read"),
            ai_feature_permissions=("ai.telephony", "ai.intake", "ai.missed_call_text_back"),
        ),
        "widget_voice": _plan(
            id=PlanTier.widget_voice,
            name="Widget + AI Telephony",
            price_monthly=149.99,
            setup_fee=97.99,
            ecosystem="simple_ai_services",
            billing_system="stripe",
            onboarding_mode="lightweight_widget_voice",
            uses_saas_mode=False,
            features=WIDGET_VOICE_FEATURES,
            allowed_modules=("ai_widget", "ai_phone", "lead_capture", "sms", "call_summaries"),
            webhook_permissions=("subscription", "widget.lead", "call.summary", "missed_call"),
            dashboard_permissions=("dashboard.read", "widget.read", "calls.read", "leads.read"),
            ai_feature_permissions=("ai.widget", "ai.telephony", "ai.intake", "ai.missed_call_text_back"),
        ),
        "enterprise": _plan(
            id=PlanTier.enterprise,
            name="Enterprise",
            price_monthly=19.99,
            setup_fee=0,
            ecosystem="simple_trucking_services",
            billing_system="stripe",
            onboarding_mode="trucking_self_service",
            uses_saas_mode=False,
            features=ENTERPRISE_TRUCKING_FEATURES,
            allowed_modules=("map_view", "provider_directory", "trucking_profile", "dispatch_tracking"),
            webhook_permissions=("subscription", "roadside.request", "dispatch.status"),
            dashboard_permissions=("map.read", "providers.read", "dispatch.read"),
            dispatch_permissions=("roadside.request", "dispatch.status.read"),
            ai_feature_permissions=("ai.roadside", "ai.driver_intake"),
        ),
        "standard": _plan(
            id=PlanTier.standard,
            name="Standard",
            price_monthly=297,
            setup_fee=149,
            ecosystem="ghl_business_os",
            billing_system="ghl",
            onboarding_mode="ghl_saas_snapshot",
            uses_saas_mode=True,
            features=STANDARD_FEATURES,
            snapshot_id=settings.GHL_STANDARD_SNAPSHOT_ID or settings.GHL_PROFESSIONAL_SNAPSHOT_ID or "TODO_GHL_STANDARD_SNAPSHOT_ID",
            allowed_modules=("ai_website", "ai_widget", "ai_phone", "crm", "pipelines", "workflows", "calendar", "sms"),
            webhook_permissions=("subscription", "ghl.contact", "ghl.opportunity", "ghl.appointment", "call.summary"),
            dashboard_permissions=("dashboard.read", "leads.read", "crm.read", "calendar.read", "website.read"),
            ai_feature_permissions=("ai.telephony", "ai.widget", "ai.web_chat", "ai.lead_qualification"),
        ),
        "professional": _plan(
            id=PlanTier.professional,
            name="Professional",
            price_monthly=497,
            setup_fee=199,
            ecosystem="ghl_business_os",
            billing_system="ghl",
            onboarding_mode="ghl_saas_snapshot",
            uses_saas_mode=True,
            features=PROFESSIONAL_FEATURES,
            snapshot_id=settings.GHL_PROFESSIONAL_SNAPSHOT_ID or settings.GHL_PREMIUM_SNAPSHOT_ID or "TODO_GHL_PROFESSIONAL_SNAPSHOT_ID",
            allowed_modules=("mobile_app", "customer_portal", "ai_phone", "ai_widget", "crm", "calendar", "sms", "website", "automation"),
            webhook_permissions=("subscription", "ghl.contact", "ghl.opportunity", "ghl.appointment", "ghl.workflow", "call.summary"),
            dashboard_permissions=("dashboard.read", "leads.read", "crm.read", "calendar.read", "portal.read"),
            ai_feature_permissions=("ai.telephony", "ai.widget", "ai.web_chat", "ai.advanced_workflows"),
        ),
        "advanced": _plan(
            id=PlanTier.advanced,
            name="Advanced",
            price_monthly=997,
            setup_fee=299,
            ecosystem="ghl_business_os",
            billing_system="ghl",
            onboarding_mode="ghl_saas_snapshot_plus_marketing",
            uses_saas_mode=True,
            features=ADVANCED_FEATURES,
            snapshot_id=settings.GHL_ADVANCED_SNAPSHOT_ID or settings.GHL_PREMIUM_SNAPSHOT_ID or "TODO_GHL_ADVANCED_SNAPSHOT_ID",
            allowed_modules=("mobile_app", "customer_portal", "social_media", "content", "funnels", "crm_campaigns", "automation"),
            webhook_permissions=("subscription", "ghl.contact", "ghl.opportunity", "ghl.appointment", "ghl.social", "ghl.funnel", "ghl.campaign"),
            dashboard_permissions=("dashboard.read", "leads.read", "crm.read", "calendar.read", "social.read", "campaigns.read"),
            ai_feature_permissions=("ai.telephony", "ai.widget", "ai.marketing_automation"),
        ),
    }


def get_plan_config(plan_id: str | PlanTier) -> PlanConfig:
    try:
        plan_key = str(plan_id).lower()
        tier = PLAN_ALIASES.get(plan_key) or PlanTier(plan_key)
    except ValueError as exc:
        raise KeyError(f"Unknown Roadcall plan: {plan_id}") from exc
    return get_plan_configs()[tier.value]


def canonical_plan_id(plan_id: str | PlanTier) -> str:
    return get_plan_config(plan_id).id.value


def included_leads_for(plan_id: str | PlanTier) -> int:
    tier = get_plan_config(plan_id).id
    return {
        PlanTier.widget_only: 25,
        PlanTier.ai_telephony: 50,
        PlanTier.widget_voice: 75,
        PlanTier.enterprise: 0,
        PlanTier.standard: 250,
        PlanTier.professional: 750,
        PlanTier.advanced: 2500,
    }[tier]


def feature_in_plan(plan_id: str | PlanTier, feature: str | PlanFeature) -> bool:
    config = get_plan_config(plan_id)
    return PlanFeature(str(feature)) in config.features


def plan_payload(config: PlanConfig) -> dict[str, object]:
    return {
        "id": config.id.value,
        "name": config.name,
        "price_monthly": config.price_monthly,
        "setup_fee": config.setup_fee,
        "ecosystem": config.ecosystem,
        "billing_system": config.billing_system,
        "onboarding_mode": config.onboarding_mode,
        "uses_saas_mode": config.uses_saas_mode,
        "automatic_subaccount_provisioning": config.automatic_subaccount_provisioning,
        "enabled_features": [feature.value for feature in config.features],
        "ghl_snapshot_id": config.snapshot_id,
        "allowed_modules": list(config.allowed_modules),
        "webhook_permissions": list(config.webhook_permissions),
        "dashboard_permissions": list(config.dashboard_permissions),
        "dispatch_permissions": list(config.dispatch_permissions),
        "ai_feature_permissions": list(config.ai_feature_permissions),
    }