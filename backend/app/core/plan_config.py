from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.config import get_settings


class PlanTier(StrEnum):
    widget_only = "widget_only"
    ai_telephony = "ai_telephony"
    widget_voice = "widget_voice"
    driver_pro = "driver_pro"
    fleet_starter = "fleet_starter"
    fleet_professional = "fleet_professional"
    fleet_enterprise = "fleet_enterprise"
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
    ai_dispatch_priority = "ai_dispatch_priority"
    emergency_mode = "emergency_mode"
    route_intelligence = "route_intelligence"
    ai_issue_triage = "ai_issue_triage"
    dispatch_eta_visibility = "dispatch_eta_visibility"
    roadside_event_timeline = "roadside_event_timeline"
    smart_provider_recommendations = "smart_provider_recommendations"
    fleet_incident_management = "fleet_incident_management"
    fleet_activity_feed = "fleet_activity_feed"
    centralized_dispatch_visibility = "centralized_dispatch_visibility"
    provider_preference_management = "provider_preference_management"
    downtime_analytics = "downtime_analytics"
    recurring_issue_detection = "recurring_issue_detection"
    roadside_sla_tracking = "roadside_sla_tracking"
    provider_performance_analytics = "provider_performance_analytics"
    roadside_heatmaps = "roadside_heatmaps"
    maintenance_trend_tracking = "maintenance_trend_tracking"
    operational_intelligence_dashboards = "operational_intelligence_dashboards"
    enterprise_command_center = "enterprise_command_center"
    custom_ai_routing = "custom_ai_routing"
    white_label_options = "white_label_options"
    dedicated_support = "dedicated_support"


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
    "driver": PlanTier.driver_pro,
    "driver_pro": PlanTier.driver_pro,
    "driver-pro": PlanTier.driver_pro,
    "trucking": PlanTier.driver_pro,
    "enterprise": PlanTier.fleet_enterprise,
    "fleet": PlanTier.fleet_starter,
    "fleet-starter": PlanTier.fleet_starter,
    "fleet-professional": PlanTier.fleet_professional,
    "fleet-pro": PlanTier.fleet_professional,
    "fleet-enterprise": PlanTier.fleet_enterprise,
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
    trial_days: int
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

DRIVER_PRO_FEATURES = (
    PlanFeature.ai_dispatch_priority,
    PlanFeature.saved_truck_profile,
    PlanFeature.emergency_mode,
    PlanFeature.roadside_intake,
    PlanFeature.ai_issue_triage,
    PlanFeature.map_view,
    PlanFeature.provider_directory,
    PlanFeature.preferred_providers,
    PlanFeature.dispatch_tracking,
    PlanFeature.dispatch_eta_visibility,
    PlanFeature.route_intelligence,
    PlanFeature.roadside_event_timeline,
    PlanFeature.smart_provider_recommendations,
)

FLEET_STARTER_FEATURES = DRIVER_PRO_FEATURES + (
    PlanFeature.fleet_dashboard,
    PlanFeature.multi_user_access,
    PlanFeature.trucking_company_profile,
    PlanFeature.fleet_notification,
    PlanFeature.dispatch_dashboard,
    PlanFeature.fleet_incident_management,
    PlanFeature.fleet_activity_feed,
    PlanFeature.centralized_dispatch_visibility,
    PlanFeature.provider_preference_management,
)

FLEET_PROFESSIONAL_FEATURES = FLEET_STARTER_FEATURES + (
    PlanFeature.advanced_reporting,
    PlanFeature.advanced_analytics,
    PlanFeature.downtime_analytics,
    PlanFeature.recurring_issue_detection,
    PlanFeature.roadside_sla_tracking,
    PlanFeature.provider_performance_analytics,
    PlanFeature.roadside_heatmaps,
    PlanFeature.maintenance_trend_tracking,
    PlanFeature.operational_intelligence_dashboards,
    PlanFeature.emergency_routing,
)

FLEET_ENTERPRISE_FEATURES = FLEET_PROFESSIONAL_FEATURES + (
    PlanFeature.enterprise_command_center,
    PlanFeature.multi_location_support,
    PlanFeature.external_dispatch_api,
    PlanFeature.api_ready_infrastructure,
    PlanFeature.custom_workflows,
    PlanFeature.custom_ai_routing,
    PlanFeature.priority_support,
    PlanFeature.dedicated_support,
    PlanFeature.white_label_options,
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
    trial_days: int = 7,
    snapshot_id: str = "",
    dispatch_permissions: tuple[str, ...] = (),
) -> PlanConfig:
    return PlanConfig(
        id=id,
        name=name,
        price_monthly=price_monthly,
        setup_fee=setup_fee,
        trial_days=trial_days,
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
        "driver_pro": _plan(
            id=PlanTier.driver_pro,
            name="Driver Pro",
            price_monthly=19.99,
            setup_fee=0,
            ecosystem="roadside_intelligence_membership",
            billing_system="stripe",
            onboarding_mode="driver_self_service",
            uses_saas_mode=False,
            features=DRIVER_PRO_FEATURES,
            allowed_modules=("ai_dispatch", "driver_profile", "emergency_mode", "map_view", "provider_directory", "dispatch_tracking"),
            webhook_permissions=("subscription", "roadside.request", "dispatch.status"),
            dashboard_permissions=("map.read", "providers.read", "dispatch.read", "driver_profile.read", "breakdown_history.read"),
            dispatch_permissions=("roadside.request", "dispatch.status.read", "dispatch.priority"),
            ai_feature_permissions=("ai.roadside", "ai.driver_intake", "ai.issue_triage", "ai.provider_recommendations"),
        ),
        "fleet_starter": _plan(
            id=PlanTier.fleet_starter,
            name="Fleet Starter",
            price_monthly=99,
            setup_fee=0,
            ecosystem="fleet_operations_platform",
            billing_system="stripe",
            onboarding_mode="fleet_self_service",
            uses_saas_mode=False,
            features=FLEET_STARTER_FEATURES,
            allowed_modules=("fleet_dashboard", "driver_management", "incident_feed", "dispatch_tracking", "provider_preferences"),
            webhook_permissions=("subscription", "fleet.incident", "fleet.dispatch", "dispatch.status"),
            dashboard_permissions=("fleet.dashboard.read", "drivers.read", "incidents.read", "providers.read", "dispatch.read"),
            dispatch_permissions=("roadside.request", "fleet.dispatch.read", "fleet.dispatch.update"),
            ai_feature_permissions=("ai.roadside", "ai.dispatch", "ai.driver_intake", "ai.provider_recommendations"),
        ),
        "fleet_professional": _plan(
            id=PlanTier.fleet_professional,
            name="Fleet Professional",
            price_monthly=299,
            setup_fee=0,
            ecosystem="fleet_operations_platform",
            billing_system="stripe",
            onboarding_mode="fleet_operations_onboarding",
            uses_saas_mode=False,
            features=FLEET_PROFESSIONAL_FEATURES,
            allowed_modules=("fleet_dashboard", "advanced_dispatch", "analytics", "heatmaps", "route_intelligence", "provider_performance"),
            webhook_permissions=("subscription", "fleet.incident", "fleet.dispatch", "fleet.analytics", "dispatch.status"),
            dashboard_permissions=("fleet.dashboard.read", "analytics.read", "heatmaps.read", "providers.read", "reports.read"),
            dispatch_permissions=("roadside.request", "fleet.dispatch.read", "fleet.dispatch.update", "fleet.dispatch.escalate"),
            ai_feature_permissions=("ai.roadside", "ai.dispatch", "ai.route_intelligence", "ai.issue_detection", "ai.provider_recommendations"),
        ),
        "fleet_enterprise": _plan(
            id=PlanTier.fleet_enterprise,
            name="Fleet Enterprise",
            price_monthly=999,
            setup_fee=0,
            ecosystem="fleet_operations_platform",
            billing_system="stripe",
            onboarding_mode="enterprise_fleet_onboarding",
            uses_saas_mode=False,
            features=FLEET_ENTERPRISE_FEATURES,
            allowed_modules=("command_center", "multi_location_ops", "api_integrations", "custom_workflows", "enterprise_analytics", "white_label"),
            webhook_permissions=("subscription", "fleet.incident", "fleet.dispatch", "fleet.analytics", "enterprise.api", "dispatch.status"),
            dashboard_permissions=("fleet.command.read", "analytics.read", "locations.read", "integrations.read", "reports.read"),
            dispatch_permissions=("roadside.request", "fleet.dispatch.read", "fleet.dispatch.update", "fleet.dispatch.escalate", "fleet.api.dispatch"),
            ai_feature_permissions=("ai.roadside", "ai.dispatch", "ai.route_intelligence", "ai.custom_routing", "ai.fleet_intelligence"),
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
        PlanTier.driver_pro: 0,
        PlanTier.fleet_starter: 0,
        PlanTier.fleet_professional: 0,
        PlanTier.fleet_enterprise: 0,
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
        "trial_days": config.trial_days,
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