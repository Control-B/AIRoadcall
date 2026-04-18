from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/airoadcall"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # LiveKit Cloud AI Telephony
    LIVEKIT_API_KEY: str = ""
    LIVEKIT_API_SECRET: str = ""
    LIVEKIT_URL: str = ""  # e.g. wss://your-project.livekit.cloud
    LIVEKIT_SIP_TRUNK_ID: str = ""  # SIP trunk for outbound calls
    LIVEKIT_OUTBOUND_AGENT_ID: str = ""  # Agent dispatch room prefix
    # Must match the LiveKit Agents worker (WorkerOptions.agent_name)
    LIVEKIT_AGENT_NAME: str = "roadcall-agent"
    # Same text as the LiveKit Console "Instructions" for this agent — copied into
    # CreateAgentDispatch metadata so outbound calls match console behavior. For inbound,
    # set the same value on the worker as LIVEKIT_CLOUD_INSTRUCTIONS (or pass via SIP
    # dispatch rule roomConfig.agents[].metadata in the Cloud dashboard).
    LIVEKIT_CLOUD_INSTRUCTIONS: str = ""
    # Optional JSON object merged into agent dispatch metadata (e.g. {"welcome_message": "..."}).
    LIVEKIT_AGENT_DISPATCH_METADATA_EXTRA: str = ""
    LIVEKIT_DISPATCH_RING_TIMEOUT_SECONDS: int = 18

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

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
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-this"

    # App
    APP_BASE_URL: str = "http://localhost:3000"
    MAGIC_LINK_SECRET: str = "change-this-to-a-secure-random-string"
    MAGIC_LINK_EXPIRY_HOURS: int = 24
    MECHANIC_ARRIVAL_THRESHOLD_METERS: float = 200.0
    DEMO_AUTO_ASSIGN_NEAREST_MECHANIC: bool = False
    DEMO_SKIP_PAYMENT_AUTHORIZATION: bool = False
    # Parallel mechanic outreach: SMS with web accept/decline; optional LiveKit per mechanic
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
