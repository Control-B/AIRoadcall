from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
import json as _json
import re as _re

import app.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import get_logger, setup_logging
from app.core.session_middleware import SessionCorrelationMiddleware
from app.api.routes import (
    jobs,
    payments,
    dispatch,
    dispatch_sessions,
    session_codes,
    tracking,
    mechanics,
    webhooks_stripe,
    webhooks_retell,
    retell_dispatch,
    retell_web,
    shop_ai,
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
    ghl,
    lifecycle,
    public_directories,
    provisioning,
    billing,
    go,
    agent_dashboard,
    support_router,
    roadcall_orchestrator,
    caller_location,
    caller_share,
    livekit,
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
# call.from_number folded in as caller_phone / callerPhone / callback_number if not already set).
_RETELL_UNWRAP_PREFIXES = ("/api/",)

_RETELL_PHONE_FIELDS = (
    "from_number",
    "fromNumber",
    "caller_phone",
    "callerPhone",
    "from",
    "caller",
    "phone_number",
    "phoneNumber",
)


def _retell_call_phone(call: dict) -> str | None:
    candidates = [call]
    for nested_key in ("metadata", "call_metadata", "telephony_metadata"):
        nested = call.get(nested_key)
        if isinstance(nested, dict):
            candidates.append(nested)
    for source in candidates:
        for field in _RETELL_PHONE_FIELDS:
            value = source.get(field)
            if isinstance(value, str) and len(_re.sub(r"\D", "", value)) >= 7:
                return value
    return None


def _retell_call_id(call: dict) -> str | None:
    for field in ("call_id", "callId", "retell_call_id", "id"):
        value = call.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return None

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
                    from_num = _retell_call_phone(call)
                    if from_num:
                        args.setdefault("caller_phone", from_num)
                        args.setdefault("callerPhone", from_num)
                        args.setdefault("callback_number", from_num)
                        args.setdefault("callbackNumber", from_num)
                    call_id = _retell_call_id(call)
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
app.include_router(dispatch_sessions.router, prefix="/api")
app.include_router(session_codes.router, prefix="/api")
app.include_router(tracking.router, prefix="/api")
app.include_router(mechanics.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(roadside.router, prefix="/api")
app.include_router(webhooks_stripe.router, prefix="/api")
app.include_router(webhooks_retell.router, prefix="/api")
app.include_router(retell_dispatch.router)
app.include_router(retell_web.router, prefix="/api")
app.include_router(shop_ai.router, prefix="/api")
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
app.include_router(ghl.router, prefix="/api")
app.include_router(lifecycle.router, prefix="/api")
app.include_router(public_directories.router, prefix="/api")
app.include_router(provisioning.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
app.include_router(go.router, prefix="/api")
app.include_router(agent_dashboard.router, prefix="/api")
app.include_router(support_router, prefix="/api")
app.include_router(roadcall_orchestrator.router, prefix="/api")
app.include_router(caller_location.router, prefix="/api")
app.include_router(caller_share.router, prefix="/api")
app.include_router(livekit.router, prefix="/api")


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
        await conn.execute(text("ALTER TABLE mechanics ALTER COLUMN base_lat DROP NOT NULL"))
        await conn.execute(text("ALTER TABLE mechanics ALTER COLUMN base_lng DROP NOT NULL"))
        await conn.execute(
            text(
                "ALTER TABLE mechanics "
                "ADD COLUMN IF NOT EXISTS zip_code VARCHAR(20)"
            )
        )
        await conn.execute(
            text(
                "ALTER TABLE mechanics "
                "ADD COLUMN IF NOT EXISTS availability_status VARCHAR(50) DEFAULT 'unknown'"
            )
        )
        await conn.execute(text("ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS google_maps_url TEXT"))
        await conn.execute(text("ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS verification_status VARCHAR(32) NOT NULL DEFAULT 'unverified'"))
        await conn.execute(
            text(
                "ALTER TABLE mechanics "
                "ADD COLUMN IF NOT EXISTS response_score DOUBLE PRECISION"
            )
        )
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_mechanics_base_lat_lng ON mechanics (base_lat, base_lng)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_mechanics_verification_status ON mechanics (verification_status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_mechanics_zip_code ON mechanics (zip_code)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_mechanics_availability_status ON mechanics (availability_status)"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS phone_onboarding_mode VARCHAR(50) NOT NULL DEFAULT 'existing_number'"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS requested_area_code VARCHAR(10)"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS twilio_number_sid VARCHAR(100)"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS twilio_number_status VARCHAR(50) NOT NULL DEFAULT 'not_requested'"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS retell_agent_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS retell_phone_number_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS retell_flow_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS appointment_booking_enabled BOOLEAN NOT NULL DEFAULT true"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS calcom_calendar_url TEXT"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS calcom_event_type_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS after_hours_enabled BOOLEAN NOT NULL DEFAULT true"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS emergency_dispatch_enabled BOOLEAN NOT NULL DEFAULT false"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS missed_calls_recovered INTEGER NOT NULL DEFAULT 0"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS appointments_booked INTEGER NOT NULL DEFAULT 0"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS after_hours_jobs_captured INTEGER NOT NULL DEFAULT 0"))
        await conn.execute(text("ALTER TABLE shop_customers ADD COLUMN IF NOT EXISTS revenue_opportunities_cents INTEGER NOT NULL DEFAULT 0"))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS retell_connections (
                id UUID PRIMARY KEY,
                tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
                organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                agent_id VARCHAR(120),
                conversation_flow_id VARCHAR(120),
                phone_number_id VARCHAR(120),
                agent_name VARCHAR(255),
                provisioning_status VARCHAR(40) NOT NULL DEFAULT 'not_provisioned',
                last_error TEXT,
                last_synced_at TIMESTAMPTZ,
                metadata_json JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT uq_retell_connections_tenant UNIQUE (tenant_id)
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_retell_connections_tenant_id ON retell_connections (tenant_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_retell_connections_organization_id ON retell_connections (organization_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_retell_connections_agent_id ON retell_connections (agent_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_retell_connections_conversation_flow_id ON retell_connections (conversation_flow_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_retell_connections_provisioning_status ON retell_connections (provisioning_status)"))
        await conn.execute(text("ALTER TABLE ghl_tenant_mappings ADD COLUMN IF NOT EXISTS agency_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE ghl_tenant_mappings ADD COLUMN IF NOT EXISTS ghl_user_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE ghl_tenant_mappings ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE ghl_tenant_mappings ADD COLUMN IF NOT EXISTS scopes JSONB NOT NULL DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE ghl_tenant_mappings ADD COLUMN IF NOT EXISTS token_source VARCHAR(40) NOT NULL DEFAULT 'manual'"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS agency_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS ghl_user_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS calendar_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS calendar_url TEXT"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS pipeline_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS workflow_status VARCHAR(40) NOT NULL DEFAULT 'not_configured'"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS website_status VARCHAR(40) NOT NULL DEFAULT 'not_configured'"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS encrypted_access_token TEXT"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS encrypted_refresh_token TEXT"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE ghl_connections ADD COLUMN IF NOT EXISTS scopes JSONB NOT NULL DEFAULT '[]'::jsonb"))
        await conn.execute(text("ALTER TABLE mechanic_accounts ADD COLUMN IF NOT EXISTS ghl_location_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE mechanic_accounts ADD COLUMN IF NOT EXISTS ghl_company_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE mechanic_accounts ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE mechanic_accounts ADD COLUMN IF NOT EXISTS plan VARCHAR(40) NOT NULL DEFAULT 'standard'"))
        await conn.execute(text("ALTER TABLE shop_profiles ADD COLUMN IF NOT EXISTS ghl_calendar_id VARCHAR(120)"))
        await conn.execute(text("ALTER TABLE shop_profiles ADD COLUMN IF NOT EXISTS ghl_calendar_url TEXT"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_mechanic_accounts_ghl_location_id ON mechanic_accounts (ghl_location_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_mechanic_accounts_stripe_subscription_id ON mechanic_accounts (stripe_subscription_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_service_requests_tenant_id ON service_requests (tenant_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_service_requests_status ON service_requests (status)"))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS active_call_sessions (
                id UUID PRIMARY KEY,
                call_provider VARCHAR(40) NOT NULL DEFAULT 'retell',
                provider_call_id VARCHAR(255) NOT NULL UNIQUE,
                caller_phone VARCHAR(30),
                location_code VARCHAR(12) NOT NULL UNIQUE,
                status VARCHAR(40) NOT NULL DEFAULT 'waiting_for_location',
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                accuracy DOUBLE PRECISION,
                address TEXT,
                city VARCHAR(120),
                state VARCHAR(10),
                highway_or_exit TEXT,
                manual_location_text TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                expires_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_active_call_sessions_call_provider ON active_call_sessions (call_provider)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_active_call_sessions_provider_call_id ON active_call_sessions (provider_call_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_active_call_sessions_caller_phone ON active_call_sessions (caller_phone)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_active_call_sessions_location_code ON active_call_sessions (location_code)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_active_call_sessions_status ON active_call_sessions (status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_active_call_sessions_expires_at ON active_call_sessions (expires_at)"))
    logger.info("Database schema verified")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-roadside-support"}


def _configured(value: str, *, allow_local: bool = False) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return False
    if "xxx" in normalized or "placeholder" in normalized or "change-this" in normalized:
        return False
    if not allow_local and ("localhost" in normalized or "user:password" in normalized):
        return False
    return True


def _integration_checks() -> dict[str, dict[str, bool | str]]:
    return {
        "database": {
            "configured": _configured(settings.DATABASE_URL, allow_local=True),
            "required_for": "all persistent flows",
        },
        "stripe": {
            "configured": _configured(settings.STRIPE_SECRET_KEY) and _configured(settings.STRIPE_WEBHOOK_SECRET),
            "required_for": "checkout, subscription sync, payment gating",
        },
        "retell": {
            "configured": _configured(settings.RETELL_API_KEY) and _configured(settings.RETELL_BACKEND_WEBHOOK_TOKEN),
            "required_for": "AI telephony provisioning and function calls",
        },
        "mapbox": {
            "configured": _configured(settings.MAPBOX_ACCESS_TOKEN),
            "required_for": "reverse geocoding and dispatch maps",
        },
        "sms": {
            "configured": (
                _configured(settings.TWILIO_ACCOUNT_SID)
                and _configured(settings.TWILIO_AUTH_TOKEN)
                and (_configured(settings.TWILIO_FROM_NUMBER) or _configured(settings.TWILIO_MESSAGING_SERVICE_SID))
            )
            or (_configured(settings.TELNYX_API_KEY) and _configured(settings.TELNYX_FROM_NUMBER)),
            "required_for": "magic links, dispatch offers, driver updates",
        },
        "email": {
            "configured": _configured(settings.RESEND_API_KEY),
            "required_for": "lead generation and notification fallback",
        },
    }


@app.get("/health/ready")
async def readiness_check():
    db_ok = False
    db_error = None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # pragma: no cover - exercised in deployed environments
        db_error = str(exc)

    integrations = _integration_checks()
    critical_ready = db_ok and all(
        bool(integrations[name]["configured"])
        for name in ("database", "stripe", "retell", "mapbox", "sms")
    )
    payload = {
        "status": "ready" if critical_ready else "degraded",
        "service": "ai-roadside-support",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "database": {"ok": db_ok, "error": db_error},
        "integrations": integrations,
    }
    return JSONResponse(
        payload,
        status_code=status.HTTP_200_OK if critical_ready else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@app.get("/api/system/status")
async def system_status():
    integrations = _integration_checks()
    return {
        "service": "ai-roadside-support",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "operational_lanes": {
            "ai_roadside_dispatch": {
                "ready": bool(integrations["database"]["configured"] and integrations["mapbox"]["configured"] and integrations["sms"]["configured"]),
                "checks": ["database", "mapbox", "sms"],
            },
            "ai_telephony": {
                "ready": bool(integrations["database"]["configured"] and integrations["retell"]["configured"]),
                "checks": ["database", "retell"],
            },
            "ai_lead_generation": {
                "ready": bool(integrations["database"]["configured"] and integrations["email"]["configured"]),
                "checks": ["database", "email"],
            },
            "truck_service_directory": {
                "ready": bool(integrations["database"]["configured"] and integrations["mapbox"]["configured"]),
                "checks": ["database", "mapbox"],
            },
        },
        "integrations": integrations,
    }
