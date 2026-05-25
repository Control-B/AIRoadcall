from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/airoadcall"
    REDIS_URL: str = ""

    # Stripe
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_STARTER_PRICE_ID: str = ""
    STRIPE_GROWTH_PRICE_ID: str = ""
    STRIPE_PRO_PRICE_ID: str = ""
    STRIPE_STANDARD_PRICE_ID: str = ""
    STRIPE_PREMIUM_PRICE_ID: str = ""
    STRIPE_ADVANCED_PRICE_ID: str = ""
    STRIPE_WIDGET_ONLY_PRICE_ID: str = ""
    STRIPE_AI_TELEPHONY_PRICE_ID: str = ""
    STRIPE_AI_CHAT_PRICE_ID: str = ""
    STRIPE_WIDGET_VOICE_PRICE_ID: str = ""
    STRIPE_DRIVER_PRO_PRICE_ID: str = ""
    STRIPE_FLEET_STARTER_PRICE_ID: str = ""
    STRIPE_FLEET_PROFESSIONAL_PRICE_ID: str = ""
    STRIPE_FLEET_ENTERPRISE_PRICE_ID: str = ""
    STRIPE_PROFESSIONAL_PRICE_ID: str = ""
    STRIPE_ENTERPRISE_PRICE_ID: str = ""

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    TWILIO_MESSAGING_SERVICE_SID: str = ""
    TWILIO_STUDIO_FLOW_SID: str = ""
    TWILIO_STUDIO_STATUS_CALLBACK: str = ""

    # Telnyx
    TELNYX_API_KEY: str = ""
    TELNYX_FROM_NUMBER: str = ""

    # Apify
    APIFY_API_TOKEN: str = ""

    # Tavily
    TAVILY_API_KEY: str = ""

    # GoHighLevel (CRM/workflow automation only; Roadcall remains source of truth)
    GHL_BASE_URL: str = "https://services.leadconnectorhq.com"
    GHL_API_KEY: str = ""
    GHL_AGENCY_ID: str = ""
    GHL_OAUTH_CLIENT_ID: str = ""
    GHL_OAUTH_CLIENT_SECRET: str = ""
    GHL_OAUTH_REDIRECT_URI: str = ""
    GHL_LOCATION_ID: str = ""
    GHL_FROM_NUMBER: str = ""
    GHL_ENCRYPTION_KEY: str = ""
    GHL_WEBHOOK_TOLERANCE_SECONDS: int = 300
    GHL_STANDARD_SNAPSHOT_ID: str = ""
    GHL_PROFESSIONAL_SNAPSHOT_ID: str = ""
    GHL_PREMIUM_SNAPSHOT_ID: str = ""
    GHL_ADVANCED_SNAPSHOT_ID: str = ""
    GHL_PROVISIONING_WEBHOOK_URL: str = ""

    # DigitalOcean AI Gradient (text chat)
    DO_AI_ENDPOINT: str = ""  # e.g. https://cluster-api.do-ai.run/v1
    DO_AI_API_KEY: str = ""
    DO_AI_MODEL: str = ""  # e.g. meta-llama/Meta-Llama-3.1-70B-Instruct

    # Resend (email)
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "AI Receptionist <hello@airoadcall.com>"

    # Outreach
    DEMO_PHONE_NUMBER: str = ""  # Toll-free demo number
    ADMIN_API_KEY: str = "change-this-to-a-secure-admin-key"
    RETELL_API_KEY: str = ""
    RETELL_AGENT_ID: str = ""
    RETELL_CONVERSATION_FLOW_ID: str = ""
    # Shop AI receptionist (third Retell agent, separate from Sandy roadside + Fleet roadside)
    RETELL_SHOP_AGENT_ID: str = ""
    RETELL_SHOP_CONVERSATION_FLOW_ID: str = ""
    RETELL_TEST_FROM_NUMBER: str = ""
    RETELL_TEST_OUTBOUND_AGENT_ID: str = ""
    RETELL_FEMALE_VOICE_ID: str = "11labs-Lily"
    RETELL_MALE_VOICE_ID: str = "retell-Cimo"
    RETELL_CLONED_VOICE_ID: str = ""
    # Fleet vertical routing (used by retell_dispatch.create_service_request to fork into RoadsideIncident)
    RETELL_FLEET_AGENT_ID: str = ""

    # LiveKit Cloud (web voice + GPS-backed Sandy beta)
    LIVEKIT_URL: str = ""
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    LIVEKIT_AGENT_NAME: str = "roadcall-agent"
    LIVEKIT_TOKEN_TTL_MINUTES: int = 30

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-this"
    RETELL_BACKEND_WEBHOOK_TOKEN: str = "local-dev-retell-token"

    # App
    APP_BASE_URL: str = "http://localhost:3000"
    MAGIC_LINK_SECRET: str = "change-this-to-a-secure-random-string"
    MAGIC_LINK_EXPIRY_HOURS: int = 24
    ROADCALL_SESSION_CODE_TTL_MINUTES: int = 15
    MECHANIC_ARRIVAL_THRESHOLD_METERS: float = 200.0
    DEMO_AUTO_ASSIGN_NEAREST_MECHANIC: bool = False
    DEMO_SKIP_PAYMENT_AUTHORIZATION: bool = False
    # Parallel mechanic outreach: SMS with web accept/decline; optional voice call per mechanic
    DISPATCH_BATCH_SIZE: int = 3
    DISPATCH_VOICE_ON_BATCH: bool = False
    JOB_DUPLICATE_WINDOW_MINUTES: int = 15

    # Mapbox
    MAPBOX_ACCESS_TOKEN: str = ""

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    @property
    def public_app_base_url(self) -> str:
        app_base_url = (self.APP_BASE_URL or "").strip().rstrip("/")
        frontend_url = (self.FRONTEND_URL or "").strip().rstrip("/")

        if app_base_url and app_base_url != "http://localhost:3000":
            return app_base_url
        if frontend_url:
            return frontend_url
        return app_base_url or "http://localhost:3000"

    def stripe_price_id_for_plan(self, plan_id: str) -> str:
        return {
            "widget_only": self.STRIPE_WIDGET_ONLY_PRICE_ID or self.STRIPE_AI_CHAT_PRICE_ID or self.STRIPE_STARTER_PRICE_ID,
            "ai_telephony": self.STRIPE_AI_TELEPHONY_PRICE_ID,
            "widget_voice": self.STRIPE_WIDGET_VOICE_PRICE_ID or self.STRIPE_STANDARD_PRICE_ID,
            "driver_pro": self.STRIPE_DRIVER_PRO_PRICE_ID or self.STRIPE_ENTERPRISE_PRICE_ID,
            "fleet_starter": self.STRIPE_FLEET_STARTER_PRICE_ID,
            "fleet_professional": self.STRIPE_FLEET_PROFESSIONAL_PRICE_ID or self.STRIPE_PROFESSIONAL_PRICE_ID,
            "fleet_enterprise": self.STRIPE_FLEET_ENTERPRISE_PRICE_ID,
            "ai_chat": self.STRIPE_WIDGET_ONLY_PRICE_ID or self.STRIPE_AI_CHAT_PRICE_ID or self.STRIPE_STARTER_PRICE_ID,
            "enterprise": self.STRIPE_FLEET_ENTERPRISE_PRICE_ID or self.STRIPE_ENTERPRISE_PRICE_ID,
            "starter": self.STRIPE_WIDGET_ONLY_PRICE_ID or self.STRIPE_AI_CHAT_PRICE_ID or self.STRIPE_STARTER_PRICE_ID,
        }.get(plan_id, "")

    model_config = {
        "env_file": (".env", "../.env"),
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
