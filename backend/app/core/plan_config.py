from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.core.config import get_settings


class PlanTier(StrEnum):
    standard = "standard"
    premium = "premium"
    advanced = "advanced"


class PlanFeature(StrEnum):
    ai_answering = "ai_answering"
    missed_call_text_back = "missed_call_text_back"
    basic_crm_sync = "basic_crm_sync"
    lead_capture = "lead_capture"
    sms_follow_up = "sms_follow_up"
    basic_ai_summaries = "basic_ai_summaries"
    website_widget = "website_widget"
    web_chat = "web_chat"
    form_builder = "form_builder"
    email_marketing = "email_marketing"
    survey_builder = "survey_builder"
    social_media_marketing = "social_media_marketing"
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
    "starter": PlanTier.standard,
    "growth": PlanTier.premium,
    "professional": PlanTier.premium,
    "pro": PlanTier.advanced,
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
    PlanFeature.appointment_scheduling,
    PlanFeature.form_builder,
)

GROWTH_FEATURES = STARTER_FEATURES + (
    PlanFeature.website_widget,
    PlanFeature.web_chat,
    PlanFeature.email_marketing,
    PlanFeature.survey_builder,
)

PRO_FEATURES = GROWTH_FEATURES + (
    PlanFeature.social_media_marketing,
    PlanFeature.funnels,
    PlanFeature.custom_workflows,
    PlanFeature.advanced_ai_workflows,
    PlanFeature.customer_follow_up,
)


def get_plan_configs() -> dict[str, PlanConfig]:
    settings = get_settings()
    return {
        "standard": PlanConfig(
            id=PlanTier.standard,
            name="Standard",
            price_monthly=299,
            setup_fee=99,
            features=STARTER_FEATURES,
            snapshot_id=settings.GHL_STANDARD_SNAPSHOT_ID or "TODO_GHL_STANDARD_SNAPSHOT_ID",
            allowed_modules=("ai_phone", "crm", "leads", "calendar", "forms", "sms"),
            webhook_permissions=("subscription", "ghl.contact", "ghl.opportunity", "call.summary"),
            dashboard_permissions=("dashboard.read", "leads.read", "crm.read", "calendar.read", "forms.read"),
            dispatch_permissions=(),
            ai_feature_permissions=("ai.telephony", "ai.answering", "ai.missed_call_text_back"),
        ),
        "premium": PlanConfig(
            id=PlanTier.premium,
            name="Professional",
            price_monthly=499,
            setup_fee=199,
            features=GROWTH_FEATURES,
            snapshot_id=settings.GHL_PREMIUM_SNAPSHOT_ID or settings.GHL_PROFESSIONAL_SNAPSHOT_ID or "TODO_GHL_PREMIUM_SNAPSHOT_ID",
            allowed_modules=("ai_phone", "crm", "leads", "calendar", "forms", "sms", "website", "web_chat", "email", "surveys"),
            webhook_permissions=("subscription", "ghl.contact", "ghl.opportunity", "ghl.appointment", "call.summary"),
            dashboard_permissions=("dashboard.read", "leads.read", "crm.read", "calendar.read", "website.read", "email.read", "surveys.read"),
            dispatch_permissions=(),
            ai_feature_permissions=("ai.telephony", "ai.answering", "ai.web_chat", "ai.email_follow_up"),
        ),
        "advanced": PlanConfig(
            id=PlanTier.advanced,
            name="Advanced",
            price_monthly=999,
            setup_fee=299,
            features=PRO_FEATURES,
            snapshot_id=settings.GHL_ADVANCED_SNAPSHOT_ID or settings.GHL_PREMIUM_SNAPSHOT_ID or "TODO_GHL_ADVANCED_SNAPSHOT_ID",
            allowed_modules=(
                "ai_phone",
                "crm",
                "leads",
                "calendar",
                "forms",
                "sms",
                "website",
                "web_chat",
                "email",
                "surveys",
                "social_media",
                "funnels",
                "automation",
            ),
            webhook_permissions=(
                "subscription",
                "ghl.contact",
                "ghl.opportunity",
                "ghl.appointment",
                "ghl.social",
                "ghl.funnel",
                "ai.voice",
            ),
            dashboard_permissions=(
                "dashboard.read",
                "leads.read",
                "crm.read",
                "calendar.read",
                "website.read",
                "email.read",
                "surveys.read",
                "social.read",
                "funnels.read",
            ),
            dispatch_permissions=(),
            ai_feature_permissions=("ai.telephony", "ai.answering", "ai.web_chat", "ai.email_follow_up", "ai.marketing_automation"),
        ),
    }


def get_plan_config(plan_id: str | PlanTier) -> PlanConfig:
    try:
        plan_key = str(plan_id).lower()
        tier = PLAN_ALIASES.get(plan_key) or PlanTier(plan_key)
    except ValueError as exc:
        raise KeyError(f"Unknown Roadcall plan: {plan_id}") from exc
    plan_config_key = {
        PlanTier.standard: "standard",
        PlanTier.premium: "premium",
        PlanTier.advanced: "advanced",
    }[tier]
    return get_plan_configs()[plan_config_key]


def canonical_plan_id(plan_id: str | PlanTier) -> str:
    return get_plan_config(plan_id).id.value


def included_leads_for(plan_id: str | PlanTier) -> int:
    tier = get_plan_config(plan_id).id
    return {
        PlanTier.standard: 10,
        PlanTier.premium: 35,
        PlanTier.advanced: 100,
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