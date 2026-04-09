from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.routes import (
    jobs,
    payments,
    dispatch,
    tracking,
    mechanics,
    webhooks_stripe,
    webhooks_livekit,
    data_pipeline,
    shops,
    outreach,
    admin_auth,
)

settings = get_settings()
setup_logging()

app = FastAPI(
    title="AI Roadside Support API",
    description="Backend orchestration for AI-powered roadside assistance dispatch",
    version="0.1.0",
)

# CORS
allowed_origins = [settings.FRONTEND_URL]
# Also allow common dev origins
if "localhost" in settings.FRONTEND_URL:
    allowed_origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(jobs.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(dispatch.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(mechanics.router, prefix="/api")
app.include_router(webhooks_stripe.router, prefix="/api")
app.include_router(webhooks_livekit.router, prefix="/api")
app.include_router(data_pipeline.router, prefix="/api")
app.include_router(shops.router, prefix="/api")
app.include_router(outreach.router, prefix="/api")
app.include_router(admin_auth.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-roadside-support"}
