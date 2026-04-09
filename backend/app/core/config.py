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

    # App
    APP_BASE_URL: str = "http://localhost:3000"
    MAGIC_LINK_SECRET: str = "change-this-to-a-secure-random-string"
    MAGIC_LINK_EXPIRY_HOURS: int = 24
    MECHANIC_ARRIVAL_THRESHOLD_METERS: float = 200.0

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "case_sensitive": True}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
