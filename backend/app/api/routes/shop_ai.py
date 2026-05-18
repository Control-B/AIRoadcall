"""Shop AI Receptionist tool endpoints.

These endpoints are called by the third Retell agent (per-tenant Shop
Receptionist) during a live call. They are protected by the same shared
secret as the Sandy/Fleet agents (``RETELL_BACKEND_WEBHOOK_TOKEN``).

The agent is provisioned per shop tenant. The tenant_id is injected into
the agent's dynamic variables at provisioning time, and the agent passes
it back in every tool call so we can scope lead capture / call summary
events to the correct tenant.

Tools:
  POST /api/shop-ai/save-lead
  POST /api/shop-ai/save-call-summary
  POST /api/shop-ai/check-availability
  POST /api/shop-ai/book-appointment
  POST /api/shop-ai/send-sms-followup
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.models.mechanic_subscription import ShopProfile
from app.models.tenant_provisioning import Tenant
from app.services.calcom_service import CalComError, service_from_profile
from app.services.lifecycle_service import LifecycleService
from app.services.sms_service import SMSService

logger = logging.getLogger("shop-ai")
settings = get_settings()
lifecycle_service = LifecycleService()

router = APIRouter(prefix="/shop-ai", tags=["shop-ai"])


def require_retell_auth(authorization: str | None = Header(default=None)) -> None:
    expected = f"Bearer {settings.RETELL_BACKEND_WEBHOOK_TOKEN}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Retell webhook authorization",
        )


async def _load_tenant(db: AsyncSession, tenant_id: str) -> Tenant:
    try:
        tid = uuid.UUID(tenant_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid tenant_id") from exc
    tenant = await db.get(Tenant, tid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


# ── Save Lead ────────────────────────────────────────────────────────────────

class SaveLeadIn(BaseModel):
    tenant_id: str = Field(..., description="Roadcall tenant UUID (from agent dynamic_variables)")
    retell_call_id: str | None = None
    caller_name: str
    caller_phone: str
    service_type: str | None = None
    vehicle: str | None = None
    preferred_language: str | None = None
    intent: Literal[
        "new_lead", "appointment_request", "existing_customer", "quote_request", "other"
    ] = "new_lead"
    urgency: Literal["low", "normal", "high", "emergency"] = "normal"
    notes: str | None = None


class SaveLeadOut(BaseModel):
    ok: bool
    lead_event_id: str
    driver_message: str


@router.post(
    "/save-lead",
    response_model=SaveLeadOut,
    dependencies=[Depends(require_retell_auth)],
)
async def save_lead(payload: SaveLeadIn, db: AsyncSession = Depends(get_session)) -> SaveLeadOut:
    tenant = await _load_tenant(db, payload.tenant_id)
    event = await lifecycle_service.emit_event(
        db,
        event_type="shop_ai.lead_captured",
        source="retell_shop",
        organization_id=tenant.organization_id,
        entity_type="tenant",
        entity_id=str(tenant.id),
        payload=payload.model_dump(exclude_none=True),
        idempotency_key=f"shop_ai_lead:{payload.retell_call_id or uuid.uuid4().hex}",
    )
    await db.commit()
    logger.info("shop_ai save_lead tenant=%s lead_event=%s", tenant.id, event.id)
    return SaveLeadOut(
        ok=True,
        lead_event_id=str(event.id),
        driver_message="Got it. I have your details on file and the team will follow up shortly.",
    )


# ── Save Call Summary ───────────────────────────────────────────────────────

class SaveCallSummaryIn(BaseModel):
    tenant_id: str
    retell_call_id: str
    caller_phone: str | None = None
    summary: str
    intent: str | None = None
    urgency: str | None = None
    transcript: str | None = None


class SaveCallSummaryOut(BaseModel):
    ok: bool
    event_id: str


@router.post(
    "/save-call-summary",
    response_model=SaveCallSummaryOut,
    dependencies=[Depends(require_retell_auth)],
)
async def save_call_summary(
    payload: SaveCallSummaryIn, db: AsyncSession = Depends(get_session)
) -> SaveCallSummaryOut:
    tenant = await _load_tenant(db, payload.tenant_id)
    event = await lifecycle_service.emit_event(
        db,
        event_type="shop_ai.call_summary",
        source="retell_shop",
        organization_id=tenant.organization_id,
        entity_type="tenant",
        entity_id=str(tenant.id),
        payload=payload.model_dump(exclude_none=True),
        idempotency_key=f"shop_ai_summary:{payload.retell_call_id}",
    )
    await db.commit()
    return SaveCallSummaryOut(ok=True, event_id=str(event.id))


# ── Check Availability ──────────────────────────────────────────────────────

class CheckAvailabilityIn(BaseModel):
    tenant_id: str
    requested_window: str | None = Field(
        default=None,
        description="Caller phrase like 'tomorrow morning' or 'next Tuesday'",
    )
    timezone: str | None = Field(default=None, description="IANA tz of the caller if known")
    days_ahead: int = Field(default=7, ge=1, le=30)


class AvailabilitySlot(BaseModel):
    start: str
    human: str


class CheckAvailabilityOut(BaseModel):
    ok: bool
    booking_url: str | None = None
    slots: list[AvailabilitySlot] = Field(default_factory=list)
    source: Literal["calcom_api", "calcom_url", "manual"] = "manual"
    driver_message: str


@router.post(
    "/check-availability",
    response_model=CheckAvailabilityOut,
    dependencies=[Depends(require_retell_auth)],
)
async def check_availability(
    payload: CheckAvailabilityIn, db: AsyncSession = Depends(get_session)
) -> CheckAvailabilityOut:
    tenant = await _load_tenant(db, payload.tenant_id)
    profile = (
        await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant.id))
    ).scalar_one_or_none()
    booking_url = profile.calcom_calendar_url if profile else None

    calcom = service_from_profile(profile) if profile else None
    if calcom is not None:
        from datetime import timedelta as _td

        start_dt = datetime.now(timezone.utc)
        end_dt = start_dt + _td(days=payload.days_ahead)
        try:
            raw_slots = await calcom.get_available_slots(
                start=start_dt,
                end=end_dt,
                timezone_name=payload.timezone,
                limit=5,
            )
        except CalComError as exc:
            logger.warning("calcom slots failed tenant=%s: %s", tenant.id, exc)
            raw_slots = []
        if raw_slots:
            slot_models = [AvailabilitySlot(start=s["start"], human=s["human"]) for s in raw_slots]
            spoken = ", ".join(s.human for s in slot_models[:3])
            return CheckAvailabilityOut(
                ok=True,
                booking_url=booking_url,
                slots=slot_models,
                source="calcom_api",
                driver_message=(
                    f"I have a few openings: {spoken}. Which one works for you?"
                ),
            )

    if booking_url:
        return CheckAvailabilityOut(
            ok=True,
            booking_url=booking_url,
            source="calcom_url",
            driver_message=(
                "I can text you our live booking link — pick any open slot and you're confirmed."
            ),
        )
    return CheckAvailabilityOut(
        ok=True,
        source="manual",
        driver_message=(
            "I'll capture your preferred time and have a team member confirm the slot by text."
        ),
    )


# ── Book Appointment ────────────────────────────────────────────────────────

class BookAppointmentIn(BaseModel):
    tenant_id: str
    retell_call_id: str | None = None
    caller_name: str
    caller_phone: str
    caller_email: str | None = None
    service_type: str | None = None
    vehicle: str | None = None
    requested_slot: str | None = Field(
        default=None,
        description="Caller's preferred time as free text (e.g. 'tomorrow at 9'). "
        "Used when no slot_start_iso is provided.",
    )
    slot_start_iso: str | None = Field(
        default=None,
        description="Exact ISO start time returned by check_availability. Required for live Cal.com booking.",
    )
    timezone: str | None = None
    notes: str | None = None


class BookAppointmentOut(BaseModel):
    ok: bool
    event_id: str
    booking_url: str | None = None
    booking_uid: str | None = None
    booking_status: Literal["confirmed", "requested", "pending"] = "requested"
    source: Literal["calcom_api", "calcom_url", "manual"] = "manual"
    driver_message: str


@router.post(
    "/book-appointment",
    response_model=BookAppointmentOut,
    dependencies=[Depends(require_retell_auth)],
)
async def book_appointment(
    payload: BookAppointmentIn, db: AsyncSession = Depends(get_session)
) -> BookAppointmentOut:
    tenant = await _load_tenant(db, payload.tenant_id)
    profile = (
        await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant.id))
    ).scalar_one_or_none()
    booking_url = profile.calcom_calendar_url if profile else None

    booking_uid: str | None = None
    booking_status: Literal["confirmed", "requested", "pending"] = "requested"
    source: Literal["calcom_api", "calcom_url", "manual"] = (
        "calcom_url" if booking_url else "manual"
    )
    booking_payload: dict[str, object] = {}

    calcom = service_from_profile(profile) if profile else None
    if calcom is not None and payload.slot_start_iso:
        try:
            result = await calcom.create_booking(
                start_iso=payload.slot_start_iso,
                attendee_name=payload.caller_name,
                attendee_phone=payload.caller_phone,
                attendee_email=payload.caller_email,
                timezone_name=payload.timezone,
                notes=payload.notes,
                metadata={
                    "tenant_id": str(tenant.id),
                    "retell_call_id": payload.retell_call_id,
                    "service_type": payload.service_type,
                    "vehicle": payload.vehicle,
                },
            )
            booking_data = (result.get("data") if isinstance(result, dict) else None) or result or {}
            booking_uid = (
                booking_data.get("uid")
                or booking_data.get("bookingUid")
                or booking_data.get("id")
            )
            booking_status = "confirmed"
            source = "calcom_api"
            booking_payload = {"calcom_response": booking_data}
        except CalComError as exc:
            logger.warning(
                "calcom create_booking failed tenant=%s slot=%s: %s",
                tenant.id,
                payload.slot_start_iso,
                exc,
            )
            booking_payload = {"calcom_error": str(exc)}

    event = await lifecycle_service.emit_event(
        db,
        event_type="shop_ai.appointment_requested",
        source="retell_shop",
        organization_id=tenant.organization_id,
        entity_type="tenant",
        entity_id=str(tenant.id),
        payload={
            **payload.model_dump(exclude_none=True),
            "booking_url": booking_url,
            "booking_uid": booking_uid,
            "booking_status": booking_status,
            "source": source,
            **booking_payload,
        },
        idempotency_key=f"shop_ai_appt:{payload.retell_call_id or uuid.uuid4().hex}",
    )
    await db.commit()

    if source == "calcom_api":
        message = (
            f"You're booked. I'll text {payload.caller_phone[-4:] if payload.caller_phone else 'you'} a confirmation."
        )
    elif source == "calcom_url":
        message = "I just texted you our booking link. Tap it to confirm your slot."
    else:
        message = "Your request is in. A team member will confirm your appointment by text shortly."

    return BookAppointmentOut(
        ok=True,
        event_id=str(event.id),
        booking_url=booking_url,
        booking_uid=booking_uid,
        booking_status=booking_status,
        source=source,
        driver_message=message,
    )


# ── Send SMS Follow-up ──────────────────────────────────────────────────────

class SendSmsFollowupIn(BaseModel):
    tenant_id: str
    caller_phone: str
    body: str = Field(..., max_length=320)
    retell_call_id: str | None = None


class SendSmsFollowupOut(BaseModel):
    ok: bool
    sms_sent: bool
    driver_message: str


@router.post(
    "/send-sms-followup",
    response_model=SendSmsFollowupOut,
    dependencies=[Depends(require_retell_auth)],
)
async def send_sms_followup(
    payload: SendSmsFollowupIn, db: AsyncSession = Depends(get_session)
) -> SendSmsFollowupOut:
    tenant = await _load_tenant(db, payload.tenant_id)
    sms_sent = False
    try:
        sms_sent = await SMSService.send_sms(payload.caller_phone, payload.body)
    except Exception as exc:  # pragma: no cover - network/provider errors
        logger.warning("shop_ai send_sms failed for tenant=%s: %s", tenant.id, exc)
    await lifecycle_service.emit_event(
        db,
        event_type="shop_ai.sms_followup",
        source="retell_shop",
        organization_id=tenant.organization_id,
        entity_type="tenant",
        entity_id=str(tenant.id),
        payload={
            "caller_phone": payload.caller_phone,
            "body": payload.body,
            "retell_call_id": payload.retell_call_id,
            "sms_sent": sms_sent,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        },
        idempotency_key=None,
    )
    await db.commit()
    return SendSmsFollowupOut(
        ok=True,
        sms_sent=sms_sent,
        driver_message="Texted." if sms_sent else "I'll have the team text you the details.",
    )
