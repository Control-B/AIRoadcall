from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings
from app.services.caller_location_service import CallerLocationService

router = APIRouter(tags=["caller-location"])
settings = get_settings()


class StartCallSessionIn(BaseModel):
    call_provider: Literal["retell", "twilio", "ghl"] = "retell"
    provider_call_id: str = Field(min_length=2, max_length=255)
    caller_phone: str | None = Field(default=None, max_length=30)


class StartCallSessionOut(BaseModel):
    session_id: str
    location_code: str
    location_url: str
    status: str
    expires_at: str


class SubmitLocationIn(BaseModel):
    location_code: str = Field(min_length=4, max_length=12)
    phone_last4: str | None = Field(default=None, max_length=8)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)


class ManualLocationIn(BaseModel):
    provider_call_id: str | None = None
    location_code: str | None = Field(default=None, max_length=12)
    location_text: str = Field(min_length=3, max_length=500)


class LocationStatusOut(BaseModel):
    status: str
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    highway_or_exit: str | None = None
    accuracy: float | None = None
    location_code: str
    location_url: str
    expires_at: str


class MatchMechanicsIn(BaseModel):
    provider_call_id: str
    service_type: str = Field(default="roadside assistance", max_length=120)
    vehicle_type: str = Field(default="box truck", max_length=120)
    urgency: str | None = Field(default=None, max_length=40)


class MatchMechanicsOut(BaseModel):
    status: str
    latitude: float | None = None
    longitude: float | None = None
    top_matches: list[dict[str, Any]]


class SubmitLocationOut(BaseModel):
    ok: bool = True
    status: str
    provider_call_id: str
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    accuracy: float | None = None
    confidence: float | None = None


class CreateLocationSessionIn(BaseModel):
    retell_call_id: str = Field(min_length=2, max_length=255)
    caller_id: str | None = Field(default=None, max_length=30)


class CreateLocationSessionOut(BaseModel):
    success: bool = True
    token: str
    location_code: str
    location_url: str
    status: str
    expires_at: str


class ShareLocationSessionIn(BaseModel):
    token: str = Field(min_length=4, max_length=12)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)


class ShareLocationSessionOut(BaseModel):
    success: bool = True
    message: str
    token: str
    status: str
    lat: float
    lng: float
    accuracy: float | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None


class CheckLocationSessionIn(BaseModel):
    retell_call_id: str | None = Field(default=None, max_length=255)
    token: str | None = Field(default=None, max_length=12)


def _require_agent_auth(authorization: str | None) -> None:
    token = settings.RETELL_BACKEND_WEBHOOK_TOKEN.strip()
    if token and authorization == f"Bearer {token}":
        return
    if not token or token == "local-dev-retell-token":
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid call-session authorization")


@router.post("/calls/start", response_model=StartCallSessionOut)
async def start_call_session(
    payload: StartCallSessionIn,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    _require_agent_auth(authorization)
    session = await CallerLocationService.create_or_refresh_session(
        db,
        provider_call_id=payload.provider_call_id,
        caller_phone=payload.caller_phone,
        call_provider=payload.call_provider,
    )
    await db.commit()
    return StartCallSessionOut(
        session_id=str(session.id),
        location_code=session.location_code,
        location_url=CallerLocationService.public_location_url(session.location_code),
        status=session.status,
        expires_at=session.expires_at.isoformat(),
    )


@router.post("/location/session/create", response_model=CreateLocationSessionOut)
async def create_location_session(
    payload: CreateLocationSessionIn,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    _require_agent_auth(authorization)
    session = await CallerLocationService.create_or_refresh_session(
        db,
        provider_call_id=payload.retell_call_id,
        caller_phone=payload.caller_id,
        call_provider="retell",
    )
    await db.commit()
    return CreateLocationSessionOut(
        token=session.location_code,
        location_code=session.location_code,
        location_url=CallerLocationService.public_location_url(session.location_code),
        status=session.status,
        expires_at=session.expires_at.isoformat(),
    )


@router.post("/location/session/share", response_model=ShareLocationSessionOut)
async def share_location_session(payload: ShareLocationSessionIn, db: AsyncSession = Depends(get_db)):
    try:
        session = await CallerLocationService.submit_gps_location(
            db,
            location_code=payload.token,
            phone_last4=None,
            latitude=payload.lat,
            longitude=payload.lng,
            accuracy=payload.accuracy,
        )
        await db.commit()
        return ShareLocationSessionOut(
            message="Location shared with Sandy.",
            token=session.location_code,
            status=session.status,
            lat=session.latitude or payload.lat,
            lng=session.longitude or payload.lng,
            accuracy=session.accuracy,
            address=session.address,
            city=session.city,
            state=session.state,
        )
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TimeoutError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc


@router.post("/retell/tools/check-location-session")
async def check_location_session(
    payload: CheckLocationSessionIn,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _require_agent_auth(authorization)
    try:
        session = await (
            CallerLocationService.session_by_code(db, payload.token)
            if payload.token
            else CallerLocationService.session_by_provider_call_id(db, payload.retell_call_id)
        )
        await db.commit()
        return CallerLocationService.location_status(session)
    except LookupError:
        await db.rollback()
        return {"found": False, "status": "not_found", "message": "No active location session found."}


@router.post("/location/submit", response_model=SubmitLocationOut)
async def submit_location(payload: SubmitLocationIn, db: AsyncSession = Depends(get_db)):
    try:
        session = await CallerLocationService.submit_gps_location(
            db,
            location_code=payload.location_code,
            phone_last4=payload.phone_last4,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy=payload.accuracy,
        )
        await db.commit()
        return SubmitLocationOut(
            status=session.status,
            provider_call_id=session.provider_call_id,
            latitude=session.latitude,
            longitude=session.longitude,
            address=session.address,
            city=session.city,
            state=session.state,
            accuracy=session.accuracy,
        )
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TimeoutError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/location/manual", response_model=SubmitLocationOut)
async def save_manual_location(
    payload: ManualLocationIn,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    if payload.provider_call_id:
        _require_agent_auth(authorization)
    try:
        session, geocoded = await CallerLocationService.submit_manual_location(
            db,
            provider_call_id=payload.provider_call_id,
            location_code=payload.location_code,
            location_text=payload.location_text,
        )
        await db.commit()
        return SubmitLocationOut(
            status=session.status,
            provider_call_id=session.provider_call_id,
            latitude=session.latitude,
            longitude=session.longitude,
            address=session.address,
            city=session.city,
            state=session.state,
            accuracy=session.accuracy,
            confidence=(geocoded or {}).get("confidence"),
        )
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TimeoutError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc


@router.get("/calls/{provider_call_id}/location-status", response_model=LocationStatusOut)
async def location_status(
    provider_call_id: str,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    _require_agent_auth(authorization)
    try:
        session = await CallerLocationService.session_by_provider_call_id(db, provider_call_id)
        await db.commit()
        return LocationStatusOut(**CallerLocationService.location_status(session))
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/match-mechanics", response_model=MatchMechanicsOut)
async def match_mechanics(
    payload: MatchMechanicsIn,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    _require_agent_auth(authorization)
    try:
        session, matches = await CallerLocationService.match_mechanics(
            db,
            provider_call_id=payload.provider_call_id,
            service_type=payload.service_type,
            vehicle_type=payload.vehicle_type,
            urgency=payload.urgency,
        )
        await db.commit()
        return MatchMechanicsOut(
            status=session.status,
            latitude=session.latitude,
            longitude=session.longitude,
            top_matches=matches,
        )
    except LookupError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
