from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_admin_api_key
from app.core.config import get_settings
from app.schemas.dispatch_session import DispatchCreateSessionRequest
from app.schemas.roadside_match import RoadsideMatchResponse
from app.services.dispatch_session_service import DispatchSessionService
from app.services.geocoding_service import GeocodingService
from app.services.roadside_matching_service import RoadsideMatchingService

router = APIRouter(prefix="/livekit", tags=["livekit"])
logger = logging.getLogger(__name__)


class RoadsideLiveKitSessionIn(BaseModel):
    caller_phone: str | None = Field(default=None, min_length=7, max_length=30)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0)
    captured_at: datetime | None = None


class RoadsideLiveKitLocation(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: float | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None


class RoadsideLiveKitSessionOut(BaseModel):
    ok: bool = True
    session_id: UUID
    room_name: str
    livekit_url: str
    participant_identity: str
    participant_token: str
    expires_at: datetime
    agent_name: str
    location: RoadsideLiveKitLocation
    instruction: str


class RoadsideLiveKitContextOut(BaseModel):
    ok: bool = True
    session_id: UUID
    status: str
    location_confirmed: bool = False
    location: RoadsideLiveKitLocation | None = None
    caller_phone_last4: str | None = None
    problem_type: str | None = None
    vehicle_type: str | None = None
    missing_fields: list[str]
    say: str


class RoadsideLiveKitMatchIn(BaseModel):
    problem_type: str | None = None
    vehicle_type: str | None = None
    problem_description: str | None = None
    limit: int = Field(default=3, ge=1, le=10)


def _normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) < 10:
        return None
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}"


async def _ensure_livekit_room(
    *,
    room_name: str,
    session_id: UUID,
    latitude: float,
    longitude: float,
    address: str | None,
    city: str | None,
    state: str | None,
) -> None:
    """Pre-create the LiveKit room with GPS metadata so Agent Builder {{metadata.*}} variables work."""
    settings = get_settings()
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        return

    now = datetime.now(timezone.utc)
    admin_payload = {
        "iss": settings.LIVEKIT_API_KEY,
        "sub": "roadcall-backend",
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=2)).timestamp()),
        "video": {"roomCreate": True, "roomAdmin": True},
    }
    admin_token = jwt.encode(admin_payload, settings.LIVEKIT_API_SECRET, algorithm="HS256")

    location_label = address or (f"{city}, {state}" if city else "")
    room_metadata = json.dumps({
        "session_id": str(session_id),
        "latitude": latitude,
        "longitude": longitude,
        "location": location_label,
        "city": city or "",
        "state": state or "",
    })

    rest_base = settings.LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"{rest_base}/twirp/livekit.RoomService/CreateRoom",
                json={"name": room_name, "empty_timeout": 3600, "metadata": room_metadata},
                headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            )
            # 200 = created, 409/already-exists = fine
            if resp.status_code not in (200, 409):
                resp.raise_for_status()
    except Exception:
        pass  # Non-fatal: room auto-creates on first join; metadata just won't be pre-set


async def _dispatch_agent_to_room(*, room_name: str, session_id: UUID) -> None:
    """Explicitly dispatch the Agent Builder agent (Sandy) to the WebRTC room."""
    settings = get_settings()
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        return

    now = datetime.now(timezone.utc)
    admin_payload = {
        "iss": settings.LIVEKIT_API_KEY,
        "sub": "roadcall-backend",
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=2)).timestamp()),
        "video": {"roomAdmin": True, "roomCreate": True},
    }
    admin_token = jwt.encode(admin_payload, settings.LIVEKIT_API_SECRET, algorithm="HS256")

    rest_base = settings.LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://")
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"{rest_base}/twirp/livekit.AgentDispatchService/CreateDispatch",
                json={
                    "room_name": room_name,
                    "agent_name": settings.LIVEKIT_AGENT_NAME,
                    "metadata": json.dumps({"session_id": str(session_id)}),
                },
                headers={"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"},
            )
            if resp.status_code >= 400:
                logger.error(
                    "LiveKit agent dispatch failed: status=%s agent=%s room=%s body=%s",
                    resp.status_code,
                    settings.LIVEKIT_AGENT_NAME,
                    room_name,
                    resp.text[:500],
                )
            else:
                logger.info(
                    "LiveKit agent dispatched: agent=%s room=%s", settings.LIVEKIT_AGENT_NAME, room_name
                )
    except Exception as exc:
        logger.exception("LiveKit agent dispatch exception for room=%s: %s", room_name, exc)


def _create_livekit_token(*, room_name: str, identity: str, session_id: UUID, expires_at: datetime) -> str:
    settings = get_settings()
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit is not configured for this environment.",
        )

    now = datetime.now(timezone.utc)
    payload = {
        "iss": settings.LIVEKIT_API_KEY,
        "sub": identity,
        "nbf": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "name": "Roadcall caller",
        "metadata": f'{{"session_id":"{session_id}","role":"caller"}}',
        "video": {
            "roomJoin": True,
            "room": room_name,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True,
        },
    }
    return jwt.encode(payload, settings.LIVEKIT_API_SECRET, algorithm="HS256")


@router.post("/roadside-session", response_model=RoadsideLiveKitSessionOut)
async def create_roadside_livekit_session(
    payload: RoadsideLiveKitSessionIn,
    db: AsyncSession = Depends(get_session),
) -> RoadsideLiveKitSessionOut:
    settings = get_settings()
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LiveKit is not configured for this environment.",
        )

    phone_e164 = _normalize_phone(payload.caller_phone)
    if payload.caller_phone and not phone_e164:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number must include at least 10 digits.",
        )

    reverse = await GeocodingService.reverse_geocode(payload.latitude, payload.longitude) or {}
    address = reverse.get("place_name") or reverse.get("address")
    captured_at = payload.captured_at or datetime.now(timezone.utc)
    expires_minutes = max(5, min(settings.LIVEKIT_TOKEN_TTL_MINUTES, 240))

    session = await DispatchSessionService.create_session(
        db,
        DispatchCreateSessionRequest(
            source="livekit_map_gps",
            caller_phone=phone_e164,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_meters,
            location_source="browser_gps",
            city=reverse.get("city"),
            state=reverse.get("state"),
            address=address,
            expires_minutes=expires_minutes,
            metadata={
                "livekit_session": True,
                "map_location_captured_at": captured_at.isoformat(),
            },
        ),
    )

    room_name = f"roadcall-{session.dispatch_session_id}"
    identity = f"caller-{session.dispatch_session_id}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)

    # Pre-create room with GPS metadata so Agent Builder {{metadata.*}} template variables work.
    await _ensure_livekit_room(
        room_name=room_name,
        session_id=session.dispatch_session_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address=address,
        city=reverse.get("city"),
        state=reverse.get("state"),
    )

    # Dispatch Sandy (Alex-14b3) to the room so she joins the WebRTC call.
    await _dispatch_agent_to_room(
        room_name=room_name,
        session_id=session.dispatch_session_id,
    )

    token = _create_livekit_token(
        room_name=room_name,
        identity=identity,
        session_id=session.dispatch_session_id,
        expires_at=expires_at,
    )

    return RoadsideLiveKitSessionOut(
        session_id=session.dispatch_session_id,
        room_name=room_name,
        livekit_url=settings.LIVEKIT_URL,
        participant_identity=identity,
        participant_token=token,
        expires_at=expires_at,
        agent_name=settings.LIVEKIT_AGENT_NAME,
        location=RoadsideLiveKitLocation(
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_meters=payload.accuracy_meters,
            address=address,
            city=reverse.get("city"),
            state=reverse.get("state"),
        ),
        instruction="Sandy must load this session first, confirm the GPS location, then search vendors.",
    )


@router.get(
    "/roadside-session/{session_id}/context",
    response_model=RoadsideLiveKitContextOut,
    dependencies=[Depends(require_admin_api_key)],
)
async def get_roadside_livekit_context(
    session_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> RoadsideLiveKitContextOut:
    session = await DispatchSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadcall session not found.")

    request = DispatchSessionService._match_request(session)
    context = RoadsideMatchingService.build_context(request)
    missing_fields = RoadsideMatchingService.missing_fields(context)
    has_location = session.lat is not None and session.lng is not None

    return RoadsideLiveKitContextOut(
        session_id=session.id,
        status=session.status,
        location_confirmed=False,
        location=RoadsideLiveKitLocation(
            latitude=session.lat,
            longitude=session.lng,
            accuracy_meters=session.location_accuracy_m,
            address=session.address,
            city=session.city,
            state=session.state,
        ) if has_location else None,
        caller_phone_last4=session.caller_phone_last4,
        problem_type=session.problem_type,
        vehicle_type=session.vehicle_type,
        missing_fields=missing_fields,
        say="Confirm the stored GPS location with the caller before searching vendors." if has_location else "Ask the caller for their city, state, or nearest cross street before searching vendors.",
    )


@router.post(
    "/roadside-session/{session_id}/match",
    response_model=RoadsideMatchResponse,
    dependencies=[Depends(require_admin_api_key)],
)
async def match_roadside_livekit_session(
    session_id: UUID,
    payload: RoadsideLiveKitMatchIn,
    db: AsyncSession = Depends(get_session),
) -> RoadsideMatchResponse:
    session = await DispatchSessionService.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadcall session not found.")
    if session.lat is None or session.lng is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Roadcall session is missing GPS coordinates.")

    session.problem_type = payload.problem_type or session.problem_type
    session.vehicle_type = payload.vehicle_type or session.vehicle_type
    session.problem_description = payload.problem_description or session.problem_description

    request = DispatchSessionService._match_request(session)
    request.limit = payload.limit
    context = RoadsideMatchingService.build_context(request)
    missing_fields = RoadsideMatchingService.missing_fields(context)
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "More caller details are required before vendor search.", "missing_fields": missing_fields},
        )

    response = await RoadsideMatchingService.match_mechanic(db, request)
    await DispatchSessionService.record_event(
        db,
        session.id,
        "livekit.match.completed",
        "agent",
        {
            "status": response.status,
            "match_count": len(response.matches),
            "search_level": response.searchLevel,
            "has_major_vendor": bool(response.majorVendor),
        },
    )
    return response