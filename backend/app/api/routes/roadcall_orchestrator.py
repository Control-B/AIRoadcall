from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings
from app.services.ghl_service import GHLService
from app.services.roadcall_orchestrator import RoadcallOrchestrator

router = APIRouter(tags=["roadcall-orchestrator"])
settings = get_settings()
orchestrator = RoadcallOrchestrator()
ghl_service = GHLService()


class MechanicProvisionIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=255)
    owner_name: str | None = Field(default=None, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    website: str | None = Field(default=None, max_length=500)
    plan: str = "standard"
    subscription_status: str = "active"
    setup_fee_status: str = "paid"
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    agency_id: str | None = None
    ghl_user_id: str | None = None
    ghl_location_id: str | None = None
    ghl_company_id: str | None = None
    ghl_calendar_id: str | None = None
    ghl_calendar_url: str | None = None
    ghl_pipeline_id: str | None = None
    ghl_access_token: str | None = Field(default=None, repr=False)
    ghl_refresh_token: str | None = Field(default=None, repr=False)
    ghl_token_expires_at: datetime | None = None
    ghl_scopes: list[str] = Field(default_factory=list)
    ghl_webhook_secret: str | None = Field(default=None, repr=False)
    snapshot_id: str | None = None
    snapshot_status: str | None = None
    workflow_status: str | None = None
    website_status: str | None = None


class MechanicProvisionOut(BaseModel):
    ok: bool = True
    mechanic_account_id: str
    tenant_id: str
    organization_id: str
    ghl_location_id: str | None = None
    onboarding_status: str
    default_pipeline_stages: list[str]
    primary_dashboard: str
    roadcall_dashboard_role: str


class SyncOut(BaseModel):
    ok: bool = True
    status: str
    calendars: dict[str, Any] | None = None
    contacts: dict[str, Any] | None = None
    opportunities: dict[str, Any] | None = None
    appointments: dict[str, Any] | None = None


def _signature_header(headers: dict[str, str]) -> str | None:
    return (
        headers.get("x-ghl-signature")
        or headers.get("x-leadconnector-signature")
        or headers.get("x-highlevel-signature")
        or headers.get("x-signature")
    )


def _timestamp_header(headers: dict[str, str]) -> str | None:
    return headers.get("x-ghl-timestamp") or headers.get("x-leadconnector-timestamp") or headers.get("x-timestamp")


async def _ghl_signature_valid(request: Request, raw_body: bytes, payload: dict[str, Any], db: AsyncSession) -> bool:
    location = payload.get("location") if isinstance(payload.get("location"), dict) else {}
    location_id = payload.get("locationId") or payload.get("location_id") or location.get("id")
    mapping = await ghl_service.get_mapping_by_location(db, location_id)
    headers = {key.lower(): value for key, value in request.headers.items()}
    signature = _signature_header(headers)
    timestamp = _timestamp_header(headers)
    if not signature:
        return False
    return ghl_service.verify_signature(mapping, raw_body, signature, timestamp)


def _require_retell_source(authorization: str | None) -> None:
    token = settings.RETELL_BACKEND_WEBHOOK_TOKEN.strip()
    if token and authorization == f"Bearer {token}":
        return
    if not token and settings.ADMIN_API_KEY == "change-this-to-a-secure-admin-key":
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Retell webhook authorization")


@router.post("/webhooks/ghl", status_code=status.HTTP_202_ACCEPTED)
async def receive_ghl_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    signature_valid = await _ghl_signature_valid(request, raw_body, payload, db)
    result = await orchestrator.handle_ghl_event(db, payload, signature_valid=signature_valid)
    await db.commit()
    return result


@router.post("/webhooks/retell", status_code=status.HTTP_202_ACCEPTED)
async def receive_retell_webhook(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    _require_retell_source(authorization)
    payload = await request.json()
    result = await orchestrator.handle_retell_event(db, payload)
    await db.commit()
    return result


@router.post("/mechanics/provision", response_model=MechanicProvisionOut)
async def provision_mechanic(payload: MechanicProvisionIn, db: AsyncSession = Depends(get_db)):
    try:
        result = await orchestrator.provision_mechanic(db, payload.model_dump(exclude_none=True))
        await db.commit()
        return MechanicProvisionOut(**result)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/mechanics/{mechanic_account_id}/sync-ghl", response_model=SyncOut)
async def sync_mechanic_ghl(mechanic_account_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await orchestrator.sync_mechanic_ghl(db, uuid.UUID(mechanic_account_id))
        await db.commit()
        return SyncOut(**result)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/mechanics/{mechanic_account_id}/dashboard")
async def mechanic_ai_operations_dashboard(mechanic_account_id: str, db: AsyncSession = Depends(get_db)):
    try:
        return await orchestrator.mechanic_dashboard(db, uuid.UUID(mechanic_account_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
