from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
import json as _json

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import get_logger, setup_logging
from app.core.session_middleware import SessionCorrelationMiddleware
from app.api.routes import (
    jobs,
    payments,
    dispatch,
    tracking,
    mechanics,
    webhooks_stripe,
    webhooks_retell,
    retell_dispatch,
    data_pipeline,
    shops,
    outreach,
    admin_auth,
    rag,
    roadside,
    call_summaries,
    fleet,
    shops_vertical,
    leads,
    major_vendors,
    marketplace,
    admin_enrichment,
    business_directories,
)

settings = get_settings()
setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="AI Roadside Support API",
    description="Backend orchestration for AI-powered roadside assistance dispatch",
    version="0.1.0",
)

# CORS
allowed_origins = [settings.FRONTEND_URL, "https://roadcall.ai", "https://www.roadcall.ai"]
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

# Session correlation: set anonymous client_session_id, attach all roadcall_*
# IDs to request.state, echo X-Roadcall-* headers, log structured traces.
app.add_middleware(SessionCorrelationMiddleware)


# ── Retell payload unwrapper ──────────────────────────────────────────────────
# Retell custom-function tools POST {"name": ..., "args": {...}, "call": {...}}.
# Our endpoints expect the args at the top level. This middleware detects that
# envelope on /api/* POSTs and rewrites the body to be just the args (with
# call.from_number folded in as caller_phone / callerPhone if not already set).
_RETELL_UNWRAP_PREFIXES = ("/api/",)

@app.middleware("http")
async def unwrap_retell_envelope(request: Request, call_next):
    if (
        request.method == "POST"
        and any(request.url.path.startswith(p) for p in _RETELL_UNWRAP_PREFIXES)
        and "application/json" in (request.headers.get("content-type") or "").lower()
    ):
        body = await request.body()
        if body:
            try:
                data = _json.loads(body)
            except Exception:
                data = None
            if isinstance(data, dict) and isinstance(data.get("args"), dict) and "name" in data:
                args = dict(data["args"])
                call = data.get("call") or {}
                if isinstance(call, dict):
                    from_num = call.get("from_number") or call.get("caller_phone")
                    if from_num:
                        args.setdefault("caller_phone", from_num)
                        args.setdefault("callerPhone", from_num)
                    call_id = call.get("call_id")
                    if call_id:
                        args.setdefault("retell_call_id", call_id)
                    agent_id = call.get("agent_id")
                    if agent_id:
                        args.setdefault("agent_id", agent_id)
                new_body = _json.dumps(args).encode()
                # Rewrite the request body so downstream handlers see the unwrapped args.
                # Starlette caches body on `_body`, and Pydantic/FastAPI re-reads via the
                # receive callable — patch both.
                request._body = new_body  # type: ignore[attr-defined]
                async def _receive():
                    return {"type": "http.request", "body": new_body, "more_body": False}
                request._receive = _receive  # type: ignore[attr-defined]
                # Update content-length header to match
                hdrs = [
                    (k, v) if k.lower() != b"content-length" else (k, str(len(new_body)).encode())
                    for k, v in request.scope.get("headers", [])
                ]
                if not any(k.lower() == b"content-length" for k, _ in hdrs):
                    hdrs.append((b"content-length", str(len(new_body)).encode()))
                request.scope["headers"] = hdrs
    return await call_next(request)

# Routes
app.include_router(jobs.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(dispatch.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(mechanics.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(roadside.router, prefix="/api")
app.include_router(webhooks_stripe.router, prefix="/api")
app.include_router(webhooks_retell.router, prefix="/api")
app.include_router(retell_dispatch.router)
app.include_router(data_pipeline.router, prefix="/api")
app.include_router(shops.router, prefix="/api")
app.include_router(outreach.router, prefix="/api")
app.include_router(admin_auth.router, prefix="/api")
app.include_router(call_summaries.router, prefix="/api")
app.include_router(fleet.router, prefix="/api")
app.include_router(shops_vertical.router, prefix="/api")
app.include_router(leads.router, prefix="/api")
app.include_router(major_vendors.router, prefix="/api")
app.include_router(marketplace.router, prefix="/api")
app.include_router(admin_enrichment.router, prefix="/api")
app.include_router(business_directories.router, prefix="/api")


@app.on_event("startup")
async def ensure_database_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "ALTER TABLE jobs "
                "ADD COLUMN IF NOT EXISTS assigned_mechanic_id UUID"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE jobs "
                "ADD COLUMN IF NOT EXISTS driver_eta_decision VARCHAR(32)"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE mechanics "
                "ADD COLUMN IF NOT EXISTS emergency_service BOOLEAN NOT NULL DEFAULT false"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE mechanics "
                "ADD COLUMN IF NOT EXISTS service_radius_miles INTEGER NOT NULL DEFAULT 50"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE mechanics "
                "ADD COLUMN IF NOT EXISTS priority_score INTEGER NOT NULL DEFAULT 50"
            )
        )
    logger.info("Database schema verified")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-roadside-support"}
