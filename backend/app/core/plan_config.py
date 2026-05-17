from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.config import get_settings


class PlanTier(StrEnum):
    starter = "starter"
    growth = "growth"
    pro = "pro"


class PlanFeature(StrEnum):
    ai_answering = "ai_answering"
    missed_call_text_back = "missed_call_text_back"
    basic_crm_sync = "basic_crm_sync"
    lead_capture = "lead_capture"
    sms_follow_up = "sms_follow_up"
    basic_ai_summaries = "basic_ai_summaries"
    website_widget = "website_widget"
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
    "standard": PlanTier.starter,
    "professional": PlanTier.growth,
    "premium": PlanTier.pro,
}


@dataclass(frozen=True)
class PlanConfig:
    id: PlanTier
    name: str
    price_monthly: int
    setup_fee: int
    features: tuple[PlanFeature, ...]
    snapshot_id: str
    allowed_modules: tuple[str, ...]
    webhook_permissions: tuple[str, ...]
    dashboard_permissions: tuple[str, ...]
    dispatch_permissions: tuple[str, ...]
    ai_feature_permissions: tuple[str, ...]


STARTER_FEATURES = (
    PlanFeature.ai_answering,
    PlanFeature.missed_call_text_back,
    PlanFeature.basic_crm_sync,
    PlanFeature.lead_capture,
    PlanFeature.sms_follow_up,
    PlanFeature.basic_ai_summaries,
    PlanFeature.website_widget,
)

GROWTH_FEATURES = STARTER_FEATURES + (
    PlanFeature.advanced_ai_workflows,
    PlanFeature.appointment_scheduling,
    PlanFeature.smart_routing,
    PlanFeature.website_voice_assistant,
    PlanFeature.advanced_qualification,
    PlanFeature.advanced_analytics,
    PlanFeature.team_notifications,
    PlanFeature.custom_workflows,
    PlanFeature.customer_follow_up,
    PlanFeature.review_automation,
    PlanFeature.multi_location_support,
)

PRO_FEATURES = GROWTH_FEATURES + (
    PlanFeature.gps_capture,
    PlanFeature.roadside_intake,
    PlanFeature.dispatch_workflow,
    PlanFeature.driver_intake,
    PlanFeature.mechanic_assignment,
    PlanFeature.fleet_notification,
    PlanFeature.dispatch_dashboard,
    PlanFeature.emergency_routing,
    PlanFeature.real_time_roadside_status,
    PlanFeature.external_dispatch_api,
    PlanFeature.api_ready_infrastructure,
)


def get_plan_configs() -> dict[PlanTier, PlanConfig]:
    settings = get_settings()
    return {
        PlanTier.starter: PlanConfig(
            id=PlanTier.starter,
            name="Starter",
            price_monthly=149,
            setup_fee=99,
            features=STARTER_FEATURES,
            snapshot_id=settings.GHL_STANDARD_SNAPSHOT_ID or "TODO_GHL_STANDARD_SNAPSHOT_ID",
            allowed_modules=("ai_phone", "crm", "leads", "sms", "widget"),
            webhook_permissions=("subscription", "ghl.contact", "ghl.opportunity", "call.summary"),
            dashboard_permissions=("dashboard.read", "leads.read", "crm.read", "widget.read"),
            dispatch_permissions=(),
            ai_feature_permissions=("ai.answering", "ai.summary", "ai.widget"),
        ),
        PlanTier.growth: PlanConfig(
            id=PlanTier.growth,
            name="Growth",
            price_monthly=299,
            setup_fee=99,
            features=GROWTH_FEATURES,
            snapshot_id=settings.GHL_PROFESSIONAL_SNAPSHOT_ID or "TODO_GHL_PROFESSIONAL_SNAPSHOT_ID",
            allowed_modules=("ai_phone", "crm", "leads", "sms", "widget", "appointments", "analytics", "team"),
            webhook_permissions=("subscription", "ghl.contact", "ghl.opportunity", "ghl.appointment", "call.summary"),
            dashboard_permissions=("dashboard.read", "leads.read", "crm.read", "appointments.read", "analytics.read", "team.read"),
            dispatch_permissions=(),
            ai_feature_permissions=("ai.answering", "ai.summary", "ai.qualification", "ai.routing", "ai.voice_assistant"),
        ),
        PlanTier.pro: PlanConfig(
            id=PlanTier.pro,
            name="Pro",
            price_monthly=499,
            setup_fee=99,
            features=PRO_FEATURES,
            snapshot_id=settings.GHL_PREMIUM_SNAPSHOT_ID or "TODO_GHL_PREMIUM_SNAPSHOT_ID",
            allowed_modules=(
                "ai_phone",
                "crm",
                "leads",
                "sms",
                "widget",
                "appointments",
                "analytics",
                "team",
                "roadside",
                "dispatch",
                "fleet",
                "external_api",
            ),
            webhook_permissions=(
                "subscription",
                "ghl.contact",
                "ghl.opportunity",
                "ghl.appointment",
                "roadside.location",
                "roadside.dispatch",
                "ai.voice",
            ),
            dashboard_permissions=(
                "dashboard.read",
                "leads.read",
                "crm.read",
                "appointments.read",
                "analytics.read",
                "team.read",
                "dispatch.read",
                "fleet.read",
            ),
            dispatch_permissions=("gps_capture", "roadside_intake", "mechanic_assignment", "fleet_notification", "external_dispatch_api"),
            ai_feature_permissions=("ai.answering", "ai.summary", "ai.qualification", "ai.routing", "ai.dispatch", "ai.emergency"),
        ),
    }


def get_plan_config(plan_id: str | PlanTier) -> PlanConfig:
    try:
        plan_key = str(plan_id).lower()
        tier = PLAN_ALIASES.get(plan_key) or PlanTier(plan_key)
    except ValueError as exc:
        raise KeyError(f"Unknown Roadcall plan: {plan_id}") from exc
    return get_plan_configs()[tier]


def canonical_plan_id(plan_id: str | PlanTier) -> str:
    return get_plan_config(plan_id).id.value


def included_leads_for(plan_id: str | PlanTier) -> int:
    tier = get_plan_config(plan_id).id
    return {
        PlanTier.starter: 10,
        PlanTier.growth: 35,
        PlanTier.pro: 100,
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
        "enabled_features": [feature.value for feature in config.features],
        "ghl_snapshot_id": config.snapshot_id,
        "allowed_modules": list(config.allowed_modules),
        "webhook_permissions": list(config.webhook_permissions),
        "dashboard_permissions": list(config.dashboard_permissions),
        "dispatch_permissions": list(config.dispatch_permissions),
        "ai_feature_permissions": list(config.ai_feature_permissions),
    }