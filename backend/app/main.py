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
)

settings = get_settings()
setup_logging()

app = FastAPI(
    title="AI Roadside Support API",
    description="Backend orchestration for AI-powered roadside assistance dispatch",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
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


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-roadside-support"}
