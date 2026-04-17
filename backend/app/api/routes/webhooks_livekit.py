"""LiveKit Cloud webhook handler.

LiveKit Cloud fires webhooks for room lifecycle, participant events,
and SIP call events. This handler processes the dispatch-related events
to update job/dispatch state.

Key events we handle:
- participant_joined: Mechanic picked up the SIP call
- participant_left: Mechanic hung up or was disconnected
- room_finished: Call room closed (timeout or completed)
- track_published: Agent or participant started media

The AI agent running in the LiveKit room determines the mechanic's response
(accepted/declined/unavailable) and stores it in participant metadata
or data channels. We extract this from the room metadata or participant
attributes when the room finishes.

Webhook docs: https://docs.livekit.io/home/server/webhooks/
"""
import json
import uuid

from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.job import Job
from app.schemas.job import JobCreateRequest
from app.services.job_service import JobService
from app.services.dispatch_service import DispatchService
from app.services.sms_service import SMSService
from app.services.livekit_service import LiveKitService
from app.services.audit_service import AuditService
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()
logger = get_logger(__name__)


@router.post("/livekit")
async def livekit_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Handle LiveKit Cloud webhook events.

    LiveKit sends events for rooms, participants, tracks, and SIP.
    We care about two flows:

    1. INBOUND driver call completed → create job + send magic link
       (Room metadata: type=driver_intake)
    2. OUTBOUND mechanic dispatch call → record mechanic response
       (Room metadata: type=mechanic_dispatch)
    """
    body = await request.body()

    # Verify webhook signature
    auth_header = request.headers.get("Authorization", "")
    if not LiveKitService.verify_webhook_signature(body, auth_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    payload = json.loads(body)
    event_type = payload.get("event", "")

    # Parse room metadata to determine the call type
    room_data = payload.get("room", {})
    room_name = room_data.get("name", "")
    room_metadata_raw = room_data.get("metadata", "{}")

    try:
        room_metadata = json.loads(room_metadata_raw)
    except (json.JSONDecodeError, TypeError):
        room_metadata = {}

    call_type = room_metadata.get("type", "")

    logger.info(
        f"LiveKit webhook: event={event_type} room={room_name} type={call_type}"
    )

    # ── Driver intake call completed ─────────────────────────
    if call_type == "driver_intake" and event_type == "room_finished":
        await _handle_driver_intake_completed(db, room_metadata, payload)

    # ── Mechanic dispatch call events ────────────────────────
    elif call_type == "mechanic_dispatch":
        if event_type == "participant_joined":
            await _handle_mechanic_answered(db, room_metadata, payload)
        elif event_type in ("room_finished", "participant_left"):
            await _handle_dispatch_call_ended(db, room_metadata, payload)

    # ── Shop inbound call events ─────────────────────────────
    elif call_type == "shop_inbound" and event_type == "room_finished":
        await _handle_shop_call_completed(db, room_metadata, payload)

    # ── SIP-specific events ──────────────────────────────────
    elif event_type == "sip_call_status":
        sip_status = payload.get("sip_call_status", {})
        await _handle_sip_status(db, room_metadata, sip_status)

    else:
        logger.debug(f"LiveKit webhook unhandled: event={event_type} type={call_type}")

    return {"received": True}


# ─── Handler: Driver Intake Call ────────────────────────────


async def _handle_driver_intake_completed(
    db: AsyncSession, room_metadata: dict, payload: dict
) -> None:
    """Process completed inbound driver intake call.

    The AI agent running in the LiveKit room collected driver info and
    stored structured data in the room or participant metadata.
    We extract it and create a job.
    """
    # The AI agent stores extracted info in room metadata or
    # in participant attributes. Check both.
    agent_data = room_metadata.get("agent_collected_data", {})

    # Also check participant metadata for the agent participant
    participants = payload.get("participants", [])
    for p in participants:
        if p.get("identity", "").startswith("agent-"):
            try:
                p_meta = json.loads(p.get("metadata", "{}"))
                agent_data = {**agent_data, **p_meta.get("collected_data", {})}
            except (json.JSONDecodeError, TypeError):
                pass

    driver_name = agent_data.get("driver_name", "Unknown Driver")
    driver_phone = agent_data.get("driver_phone", "")
    vehicle_type = agent_data.get("vehicle_type")
    issue_type = agent_data.get("issue_type", "other")
    issue_summary = agent_data.get("issue_summary", "")

    # The caller's phone number may also be in SIP participant info
    if not driver_phone:
        for p in participants:
            if not p.get("identity", "").startswith("agent-"):
                sip_attrs = p.get("attributes", {})
                driver_phone = sip_attrs.get("sip.callId", "") or sip_attrs.get(
                    "sip.from", ""
                )
                break

    if not driver_phone:
        logger.warning(
            "LiveKit driver_intake room_finished: no driver phone, skipping"
        )
        return

    # Clean phone number (remove SIP URI if present)
    if driver_phone.startswith("sip:"):
        driver_phone = driver_phone.split("@")[0].replace("sip:", "")

    job_request = JobCreateRequest(
        driver_name=driver_name,
        driver_phone=driver_phone,
        vehicle_type=vehicle_type,
        issue_type=issue_type,
        issue_summary=issue_summary,
    )

    result = await JobService.create_job(db, job_request)

    await SMSService.send_magic_link(
        phone_number=driver_phone,
        magic_link_url=result.magic_link_url,
        driver_name=driver_name,
    )

    logger.info(
        f"LiveKit intake: created job {result.public_job_id} for {driver_phone}"
    )


# ─── Handler: Mechanic Answered ─────────────────────────────


async def _handle_mechanic_answered(
    db: AsyncSession, room_metadata: dict, payload: dict
) -> None:
    """Mechanic picked up the SIP call.

    This is informational — the AI agent will now speak with the mechanic.
    The actual accept/decline decision comes when the room finishes or
    when the agent updates metadata.
    """
    dispatch_attempt_id = room_metadata.get("dispatch_attempt_id", "")
    mechanic_name = room_metadata.get("mechanic_name", "")

    logger.info(
        f"Mechanic {mechanic_name} answered dispatch call "
        f"(attempt: {dispatch_attempt_id})"
    )


# ─── Handler: Dispatch Call Ended ────────────────────────────


async def _handle_dispatch_call_ended(
    db: AsyncSession, room_metadata: dict, payload: dict
) -> None:
    """Mechanic dispatch call has ended (room_finished or participant_left).

    Extract the mechanic's response from:
    1. Room metadata (updated by the AI agent during the call)
    2. Agent participant metadata
    3. Default to 'no_answer' if we can't determine
    """
    job_id_str = room_metadata.get("job_id")
    dispatch_attempt_id_str = room_metadata.get("dispatch_attempt_id")

    if not job_id_str or not dispatch_attempt_id_str:
        logger.warning("LiveKit dispatch call ended but missing job/attempt IDs")
        return

    # Extract the AI agent's determination of mechanic response
    mechanic_response = "no_answer"
    eta_minutes = None
    notes = ""

    # Check if the agent updated room metadata with the result
    agent_result = room_metadata.get("agent_result", {})
    if agent_result:
        mechanic_response = agent_result.get("response", "no_answer")
        eta_minutes = agent_result.get("eta_minutes")
        notes = agent_result.get("notes", "")

    # Also check participant metadata (agent may store results there)
    participants = payload.get("participants", [])
    for p in participants:
        if p.get("identity", "").startswith("agent-"):
            try:
                p_meta = json.loads(p.get("metadata", "{}"))
                result_data = p_meta.get("dispatch_result", {})
                if result_data:
                    mechanic_response = result_data.get("response", mechanic_response)
                    eta_minutes = result_data.get("eta_minutes", eta_minutes)
                    notes = result_data.get("notes", notes)
            except (json.JSONDecodeError, TypeError):
                pass

    # Check if the call was never answered (SIP no-answer)
    room_data = payload.get("room", {})
    num_participants = room_data.get("num_participants", 0)
    if num_participants <= 1:
        # Only the agent was in the room — mechanic never picked up
        mechanic_response = "no_answer"

    try:
        result = await DispatchService.record_mechanic_response(
            db=db,
            job_id=uuid.UUID(job_id_str),
            attempt_id=uuid.UUID(dispatch_attempt_id_str),
            response=mechanic_response,
            eta_minutes=eta_minutes,
            notes=notes,
        )
        logger.info(
            f"LiveKit dispatch result: {mechanic_response} for job {job_id_str} "
            f"(attempt: {dispatch_attempt_id_str})"
        )

        # Next mechanic outbound call is triggered from DispatchService.record_mechanic_response

        # If mechanic accepted, cancel other active dispatch calls
        if mechanic_response == "accepted":
            room_name = room_data.get("name", "")
            cancelled = await LiveKitService.cancel_dispatch_calls(
                job_id_str, except_room=room_name
            )
            if cancelled:
                logger.info(
                    f"Cancelled {cancelled} other dispatch calls for job {job_id_str}"
                )

    except ValueError as e:
        logger.error(f"LiveKit dispatch call ended error: {e}")


# ─── Handler: SIP Call Status ────────────────────────────────


async def _handle_sip_status(
    db: AsyncSession, room_metadata: dict, sip_status: dict
) -> None:
    """Handle SIP-specific call status updates.

    LiveKit sends these for events like:
    - ringing
    - busy
    - failed
    - no_answer (timeout)
    """
    call_status = sip_status.get("status", "")
    dispatch_attempt_id_str = room_metadata.get("dispatch_attempt_id")
    job_id_str = room_metadata.get("job_id")

    if not dispatch_attempt_id_str or not job_id_str:
        return

    logger.info(
        f"SIP status: {call_status} for dispatch attempt {dispatch_attempt_id_str}"
    )

    # Map SIP failure states to dispatch responses
    sip_failure_map = {
        "busy": "unavailable",
        "failed": "no_answer",
        "no_answer": "no_answer",
        "rejected": "declined",
    }

    if call_status in sip_failure_map:
        try:
            result = await DispatchService.record_mechanic_response(
                db=db,
                job_id=uuid.UUID(job_id_str),
                attempt_id=uuid.UUID(dispatch_attempt_id_str),
                response=sip_failure_map[call_status],
                notes=f"SIP call status: {call_status}",
            )

            # Auto-dispatch next mechanic
            next_attempt = await DispatchService.dispatch_next_mechanic(
                db, uuid.UUID(job_id_str)
            )
            if next_attempt:
                logger.info(
                    f"SIP {call_status} → auto-dispatching next mechanic "
                    f"for job {job_id_str}: {next_attempt.mechanic_company}"
                )

        except ValueError as e:
            logger.error(f"SIP status handler error: {e}")


# ─── Handler: Shop Inbound Call Completed ───────────────────


async def _handle_shop_call_completed(
    db: AsyncSession, room_metadata: dict, payload: dict
) -> None:
    """Process completed shop inbound call.

    The AI agent collected caller info and stored it in participant metadata.
    We extract it and update the call log.
    """
    from app.services.shop_telephony_service import ShopTelephonyService

    shop_id_str = room_metadata.get("shop_id", "")
    caller_phone = room_metadata.get("caller_phone", "unknown")

    if not shop_id_str:
        logger.warning("Shop inbound call completed but no shop_id in metadata")
        return

    # Extract collected data from participant metadata
    collected_data = {}
    transfer_requested = False
    participants = payload.get("room", {}).get("participants", [])
    for p in participants:
        try:
            meta = json.loads(p.get("metadata", "{}"))
            if "call_data" in meta:
                collected_data = meta["call_data"]
            if meta.get("transfer_requested"):
                transfer_requested = True
        except (json.JSONDecodeError, TypeError):
            continue

    # Determine intent
    service_needed = collected_data.get("service_needed", "").lower()
    intent = "general_question"
    if any(w in service_needed for w in ("repair", "fix", "broken")):
        intent = "repair_request"
    elif any(w in service_needed for w in ("tow", "towing")):
        intent = "tow_request"
    elif any(w in service_needed for w in ("emergency", "roadside", "stuck")):
        intent = "emergency"
    elif any(w in service_needed for w in ("price", "cost", "quote")):
        intent = "price_inquiry"
    elif any(w in service_needed for w in ("schedule", "appointment")):
        intent = "scheduling"

    # Score lead quality
    lead_score = 0.0
    if collected_data.get("caller_name"):
        lead_score += 0.3
    if collected_data.get("vehicle_info"):
        lead_score += 0.3
    if collected_data.get("service_needed"):
        lead_score += 0.2
    if collected_data.get("urgency") in ("urgent", "emergency"):
        lead_score += 0.2

    try:
        shop_id = uuid.UUID(shop_id_str)
        await ShopTelephonyService.log_call(
            db,
            shop_id=shop_id,
            caller_phone=caller_phone,
            channel="voice",
            direction="inbound",
            intent=intent,
            intent_summary=collected_data.get("service_needed", ""),
            is_qualified_lead=lead_score >= 0.5,
            lead_score=lead_score,
            vehicle_info={"description": collected_data.get("vehicle_info", "")},
            caller_name=collected_data.get("caller_name"),
            forwarded_to_human=transfer_requested,
            collected_data=collected_data,
            status="completed",
        )

        logger.info(
            f"Shop call completed: shop={shop_id_str} caller={caller_phone} "
            f"intent={intent} lead_score={lead_score:.1f} transfer={transfer_requested}"
        )

    except Exception as e:
        logger.error(f"Failed to log shop call: {e}")
