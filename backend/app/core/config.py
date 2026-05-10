from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/airoadcall"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    TWILIO_MESSAGING_SERVICE_SID: str = ""

    # Telnyx
    TELNYX_API_KEY: str = ""
    TELNYX_FROM_NUMBER: str = ""

    # Apify
    APIFY_API_TOKEN: str = ""

    # Tavily
    TAVILY_API_KEY: str = ""

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
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-this"
    RETELL_BACKEND_WEBHOOK_TOKEN: str = "local-dev-retell-token"

    # App
    APP_BASE_URL: str = "http://localhost:3000"
    MAGIC_LINK_SECRET: str = "change-this-to-a-secure-random-string"
    MAGIC_LINK_EXPIRY_HOURS: int = 24
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

    model_config = {"env_file": ".env", "case_sensitive": True}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
