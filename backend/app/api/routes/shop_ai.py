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
    POST /api/shop-ai/intake-guide
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
from app.models.mechanic_subscription import CallTranscript, ShopCall, ShopCallSummary, ShopProfile
from app.models.tenant_provisioning import Tenant
from app.services.calcom_service import CalComError, service_from_profile
from app.services.lifecycle_service import LifecycleService
from app.services.sms_service import SMSService

logger = logging.getLogger("shop-ai")
settings = get_settings()
lifecycle_service = LifecycleService()

router = APIRouter(prefix="/shop-ai", tags=["shop-ai"])


SYMPTOM_GUIDES: dict[str, dict[str, object]] = {
    "no_start": {
        "label": "No-start / hard-start",
        "questions": [
            "Is it no-crank, or does it crank but not start?",
            "Do the dash lights dim while cranking?",
            "Has anyone tried a jump start, and did it change anything?",
            "How much fuel is in the tank, and were filters recently changed?",
        ],
        "ticket_fields": ["battery_voltage", "jump_attempted", "starter_click", "fuel_level", "recent_filter_work"],
        "emergency_flags": ["unsafe_location", "fuel_leak", "fire_smell"],
    },
    "dpf_derate": {
        "label": "DPF / DEF / derate",
        "questions": [
            "Is the check-engine or stop-engine light on?",
            "Is the truck speed-limited or in limp mode?",
            "Have you attempted a parked regen?",
            "Any DEF level or DEF quality warning?",
        ],
        "ticket_fields": ["warning_lights", "speed_limit_mph", "regen_attempted", "def_warning", "can_limp"],
        "emergency_flags": ["stop_engine_light", "cannot_move", "unsafe_location"],
    },
    "brakes_air": {
        "label": "Air / brake issue",
        "questions": [
            "What is the current air PSI?",
            "Does pressure build above 90 PSI?",
            "Do you hear the leak at the tractor or trailer?",
            "Are the spring brakes locked or dragging?",
        ],
        "ticket_fields": ["current_psi", "builds_above_90", "leak_location", "brakes_locked"],
        "emergency_flags": ["brake_failure", "brakes_locked", "cannot_build_air"],
    },
    "overheating": {
        "label": "Overheating / coolant / oil pressure",
        "questions": [
            "Is the engine shut down now?",
            "Is there steam, coolant on the ground, or an oil pressure warning?",
            "What does the temperature gauge show?",
            "Can you see whether the fan is running?",
        ],
        "ticket_fields": ["engine_shutdown", "steam_or_leak", "temperature_gauge", "oil_pressure_warning", "fan_running"],
        "emergency_flags": ["overheating", "oil_pressure_warning", "active_leak"],
    },
    "tire": {
        "label": "Tire / wheel-end",
        "questions": [
            "Which tire position is affected?",
            "Is it a blowout, flat, low pressure, or tread separation?",
            "Can you read the tire size?",
            "Is the vehicle safely off the road?",
        ],
        "ticket_fields": ["tire_position", "failure_type", "tire_size", "safe_location"],
        "emergency_flags": ["steer_tire_blowout", "unsafe_location", "wheel_fire"],
    },
    "general": {
        "label": "General service intake",
        "questions": [
            "What changed right before the issue started?",
            "Is the vehicle safe to drive?",
            "Are any warning lights or fault codes showing?",
            "What year, make, model, mileage, and VIN can you provide?",
        ],
        "ticket_fields": ["symptom_summary", "safe_to_drive", "warning_lights", "fault_codes", "year_make_model", "mileage", "vin"],
        "emergency_flags": ["unsafe_to_drive", "fire", "injury"],
    },
}


def _symptom_category(text: str | None) -> str:
    normalized = (text or "").lower()
    if any(term in normalized for term in ("no start", "won't start", "wont start", "crank", "starter", "battery")):
        return "no_start"
    if any(term in normalized for term in ("dpf", "def", "derate", "regen", "limp")):
        return "dpf_derate"
    if any(term in normalized for term in ("brake", "air leak", "psi", "spring brake", "locked")):
        return "brakes_air"
    if any(term in normalized for term in ("overheat", "coolant", "oil pressure", "steam", "temperature")):
        return "overheating"
    if any(term in normalized for term in ("tire", "flat", "blowout", "wheel")):
        return "tire"
    return "general"


def _emergency_flags(text: str | None) -> list[str]:
    normalized = (text or "").lower()
    flags: list[str] = []
    for term, flag in (
        ("fire", "fire"),
        ("injur", "injury"),
        ("crash", "crash"),
        ("accident", "accident"),
        ("brake fail", "brake_failure"),
        ("no brakes", "brake_failure"),
        ("stop engine", "stop_engine_light"),
        ("oil pressure", "oil_pressure_warning"),
        ("unsafe", "unsafe_location"),
        ("shoulder", "roadside_exposure"),
    ):
        if term in normalized and flag not in flags:
            flags.append(flag)
    return flags


def _split_key_points(summary: str | None) -> list[str]:
    if not summary:
        return []
    return [part.strip(" -") for part in summary.replace("\n", ". ").split(".") if part.strip()][:4]


class VehicleIntake(BaseModel):
    year: str | None = None
    make: str | None = None
    model: str | None = None
    mileage: str | None = None
    vin: str | None = None
    unit_number: str | None = None
    truck_type: str | None = None
    trailer_type: str | None = None
    loaded_status: str | None = None
    engine_make: str | None = None
    fault_codes: list[str] = Field(default_factory=list)


class TriageAssessment(BaseModel):
    symptom_category: str | None = None
    classification: str | None = None
    safe_to_drive: bool | None = None
    emergency_flags: list[str] = Field(default_factory=list)
    handoff_required: bool = False
    handoff_reason: str | None = None


class PostCallAutomation(BaseModel):
    send_booking_confirmation: bool = False
    send_directions: bool = False
    send_review_request: bool = False
    notify_owner: bool = False
    notify_fleet_manager: bool = False
    handoff_summary_sent: bool = False


class IntakeGuideIn(BaseModel):
    tenant_id: str
    complaint: str = Field(..., min_length=2)
    vehicle_type: str | None = None
    caller_type: Literal["shop", "fleet"] = "shop"


class IntakeGuideOut(BaseModel):
    ok: bool = True
    symptom_category: str
    label: str
    questions: list[str]
    ticket_fields: list[str]
    emergency_flags: list[str]
    handoff_required: bool
    driver_message: str


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
    vehicle_intake: VehicleIntake | None = None
    triage: TriageAssessment | None = None
    requested_handoff: bool = False
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

@router.post(
    "/intake-guide",
    response_model=IntakeGuideOut,
    dependencies=[Depends(require_retell_auth)],
)
async def intake_guide(payload: IntakeGuideIn, db: AsyncSession = Depends(get_session)) -> IntakeGuideOut:
    tenant = await _load_tenant(db, payload.tenant_id)
    category = _symptom_category(payload.complaint)
    guide = SYMPTOM_GUIDES[category]
    flags = sorted(set([*_emergency_flags(payload.complaint), *(guide.get("emergency_flags") or [])]))
    handoff_required = bool(_emergency_flags(payload.complaint))
    await lifecycle_service.emit_event(
        db,
        event_type="shop_ai.intake_guided",
        source="retell_shop" if payload.caller_type == "shop" else "retell_fleet",
        organization_id=tenant.organization_id,
        entity_type="tenant",
        entity_id=str(tenant.id),
        payload={
            "complaint": payload.complaint,
            "vehicle_type": payload.vehicle_type,
            "caller_type": payload.caller_type,
            "symptom_category": category,
            "handoff_required": handoff_required,
        },
        idempotency_key=None,
    )
    await db.commit()
    return IntakeGuideOut(
        symptom_category=category,
        label=str(guide["label"]),
        questions=list(guide["questions"]),
        ticket_fields=list(guide["ticket_fields"]),
        emergency_flags=flags,
        handoff_required=handoff_required,
        driver_message="Ask one targeted question at a time, then save the structured ticket and call summary.",
    )


class SaveCallSummaryIn(BaseModel):
    tenant_id: str
    retell_call_id: str
    caller_phone: str | None = None
    caller_name: str | None = None
    summary: str
    intent: str | None = None
    urgency: str | None = None
    problem_type: str | None = None
    vehicle_type: str | None = None
    duration_seconds: int | None = None
    key_points: list[str] = Field(default_factory=list)
    vehicle_intake: VehicleIntake | None = None
    triage: TriageAssessment | None = None
    post_call_automation: PostCallAutomation = Field(default_factory=PostCallAutomation)
    handoff_requested: bool = False
    handoff_reason: str | None = None
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
    triage = payload.triage or TriageAssessment(
        symptom_category=_symptom_category(" ".join(item for item in (payload.problem_type, payload.summary) if item)),
        emergency_flags=_emergency_flags(payload.summary),
        handoff_required=payload.handoff_requested,
        handoff_reason=payload.handoff_reason,
    )
    handoff_required = payload.handoff_requested or triage.handoff_required or bool(triage.emergency_flags)
    key_points = payload.key_points or _split_key_points(payload.summary)
    call_result = await db.execute(
        select(ShopCall).where(
            ShopCall.tenant_id == tenant.id,
            ShopCall.retell_call_id == payload.retell_call_id,
        )
    )
    call = call_result.scalar_one_or_none()
    if call is None:
        call = ShopCall(
            tenant_id=tenant.id,
            retell_call_id=payload.retell_call_id,
            caller_phone=payload.caller_phone,
            call_status="handoff_requested" if handoff_required else "completed",
            lead_status="qualified" if payload.urgency in {"high", "emergency"} or triage.emergency_flags else "captured",
            duration_seconds=payload.duration_seconds,
            metadata_json={
                "caller_name": payload.caller_name,
                "intent": payload.intent,
                "urgency": payload.urgency,
                "key_points": key_points,
                "vehicle_intake": payload.vehicle_intake.model_dump(exclude_none=True) if payload.vehicle_intake else {},
                "triage": triage.model_dump(exclude_none=True),
                "post_call_automation": payload.post_call_automation.model_dump(),
                "handoff_requested": handoff_required,
                "handoff_reason": payload.handoff_reason or triage.handoff_reason,
                "source": "retell_shop",
            },
        )
        db.add(call)
        await db.flush()
    else:
        call.caller_phone = payload.caller_phone or call.caller_phone
        call.call_status = "handoff_requested" if handoff_required else "completed"
        call.lead_status = "qualified" if payload.urgency in {"high", "emergency"} or triage.emergency_flags else call.lead_status
        call.duration_seconds = payload.duration_seconds or call.duration_seconds
        call.metadata_json = {
            **(call.metadata_json or {}),
            "caller_name": payload.caller_name or (call.metadata_json or {}).get("caller_name"),
            "intent": payload.intent or (call.metadata_json or {}).get("intent"),
            "urgency": payload.urgency or (call.metadata_json or {}).get("urgency"),
            "key_points": key_points or (call.metadata_json or {}).get("key_points") or [],
            "vehicle_intake": payload.vehicle_intake.model_dump(exclude_none=True) if payload.vehicle_intake else (call.metadata_json or {}).get("vehicle_intake") or {},
            "triage": triage.model_dump(exclude_none=True),
            "post_call_automation": payload.post_call_automation.model_dump(),
            "handoff_requested": handoff_required,
            "handoff_reason": payload.handoff_reason or triage.handoff_reason or (call.metadata_json or {}).get("handoff_reason"),
            "source": "retell_shop",
        }

    summary_result = await db.execute(
        select(ShopCallSummary).where(
            ShopCallSummary.tenant_id == tenant.id,
            ShopCallSummary.call_id == call.id,
        )
    )
    call_summary = summary_result.scalar_one_or_none()
    if call_summary is None:
        call_summary = ShopCallSummary(tenant_id=tenant.id, call_id=call.id)
        db.add(call_summary)
    call_summary.summary = payload.summary
    call_summary.problem_type = payload.problem_type or triage.symptom_category or payload.intent
    call_summary.vehicle_type = payload.vehicle_type or (payload.vehicle_intake.truck_type if payload.vehicle_intake else None)
    call_summary.urgency = "emergency" if triage.emergency_flags else payload.urgency

    if payload.transcript:
        transcript = CallTranscript(
            call_id=call.id,
            tenant_id=tenant.id,
            transcript_text=payload.transcript,
            transcript_json={"source": "retell_shop", "retell_call_id": payload.retell_call_id},
        )
        db.add(transcript)

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
    if handoff_required:
        profile = (await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant.id))).scalar_one_or_none()
        advisor_phone = (profile.fallback_phone or profile.phone) if profile else tenant.contact_phone
        advisor_body = (
            f"Roadcall handoff: {payload.caller_name or 'Caller'} {payload.caller_phone or ''}. "
            f"{payload.summary[:220]}"
        ).strip()
        sms_sent = False
        if advisor_phone:
            try:
                sms_sent = await SMSService.send_sms(advisor_phone, advisor_body)
            except Exception as exc:  # pragma: no cover - provider/network errors
                logger.warning("handoff SMS failed tenant=%s: %s", tenant.id, exc)
        await lifecycle_service.emit_event(
            db,
            event_type="shop_ai.handoff_requested",
            source="retell_shop",
            organization_id=tenant.organization_id,
            entity_type="tenant",
            entity_id=str(tenant.id),
            payload={
                "retell_call_id": payload.retell_call_id,
                "caller_phone": payload.caller_phone,
                "caller_name": payload.caller_name,
                "reason": payload.handoff_reason or triage.handoff_reason,
                "emergency_flags": triage.emergency_flags,
                "advisor_phone_configured": bool(advisor_phone),
                "sms_sent": sms_sent,
                "summary": payload.summary,
            },
            idempotency_key=f"shop_ai_handoff:{payload.retell_call_id}",
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
