from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.dispatch_session import DispatchSession
from app.schemas.dispatch_session import DispatchCreateSessionRequest, DispatchUpdateLocationRequest
from app.services.dispatch_session_service import DispatchSessionService, normalize_public_code

router = APIRouter(tags=["roadcall-session-codes"])


class SessionCreateIn(BaseModel):
    callSid: str = Field(min_length=2, max_length=255)
    phoneNumber: str | None = Field(default=None, max_length=30)
    source: str = Field(default="ai_voice", max_length=40)


class SessionCreateOut(BaseModel):
    success: bool = True
    sessionCode: str
    dispatchSessionId: str
    expiresAt: str


class SessionValidateIn(BaseModel):
    sessionCode: str = Field(min_length=4, max_length=20)


class SessionValidateOut(BaseModel):
    success: bool = True
    sessionExists: bool
    sessionCode: str | None = None
    status: str | None = None
    expiresAt: str | None = None


class SessionLocationUpdateIn(BaseModel):
    sessionCode: str = Field(min_length=4, max_length=20)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)
    problemType: str | None = Field(default=None, max_length=80)
    problemDescription: str | None = Field(default=None, max_length=1000)
    vehicleType: str | None = Field(default=None, max_length=80)


class SessionLocationUpdateOut(BaseModel):
    success: bool = True
    session: dict[str, Any]


SESSION_CODE_TTL_MINUTES = 15


def _expires_at(session: DispatchSession) -> datetime:
    created_at = session.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at + timedelta(minutes=SESSION_CODE_TTL_MINUTES)


def _is_expired(session: DispatchSession) -> bool:
    return _expires_at(session) < datetime.now(timezone.utc)


async def _session_by_code(db: AsyncSession, code: str) -> DispatchSession | None:
    normalized = normalize_public_code(code)
    from sqlalchemy import select

    result = await db.execute(select(DispatchSession).where(DispatchSession.public_code == normalized))
    return result.scalar_one_or_none()


async def _session_view(db: AsyncSession, session: DispatchSession) -> dict[str, Any]:
    status = await DispatchSessionService.status_response(db, session)
    return {
        "callSid": session.retell_call_id or session.twilio_call_sid,
        "sessionCode": session.public_code,
        "dispatchSessionId": str(session.id),
        "phoneNumber": session.caller_phone_encrypted,
        "status": "expired" if _is_expired(session) and not status.location_captured else status.status,
        "gps": None if status.latitude is None or status.longitude is None else {
            "latitude": status.latitude,
            "longitude": status.longitude,
            "accuracy": session.location_accuracy_m,
        },
        "mechanicMatches": [] if not status.best_match else [status.best_match],
        "createdAt": session.created_at.isoformat(),
        "expiresAt": _expires_at(session).isoformat(),
        "locationCaptured": status.location_captured,
        "city": status.city,
        "state": status.state,
        "problemType": status.problem_type,
        "vehicleType": status.vehicle_type,
        "say": status.say,
    }


@router.post("/session/create", response_model=SessionCreateOut)
async def create_session(payload: SessionCreateIn, db: AsyncSession = Depends(get_session)):
    created = await DispatchSessionService.create_session(
        db,
        DispatchCreateSessionRequest(
            source=payload.source,
            retell_call_id=payload.callSid,
            caller_phone=payload.phoneNumber,
            expires_minutes=SESSION_CODE_TTL_MINUTES,
        ),
    )
    return SessionCreateOut(
        sessionCode=created.public_code,
        dispatchSessionId=str(created.dispatch_session_id),
        expiresAt=created.expires_at.isoformat(),
    )


@router.post("/session/validate", response_model=SessionValidateOut)
async def validate_session(payload: SessionValidateIn, db: AsyncSession = Depends(get_session)):
    session = await _session_by_code(db, payload.sessionCode)
    if not session or _is_expired(session):
        return SessionValidateOut(success=True, sessionExists=False)
    return SessionValidateOut(
        sessionExists=True,
        sessionCode=session.public_code,
        status=session.status,
        expiresAt=_expires_at(session).isoformat(),
    )


@router.post("/location/update", response_model=SessionLocationUpdateOut)
async def update_location(payload: SessionLocationUpdateIn, db: AsyncSession = Depends(get_session)):
    try:
        linked = await DispatchSessionService.link_case_code(db, payload.sessionCode, None, SESSION_CODE_TTL_MINUTES)
        updated = await DispatchSessionService.update_location(
            db,
            DispatchUpdateLocationRequest(
                token=linked.location_token,
                latitude=payload.latitude,
                longitude=payload.longitude,
                accuracy_m=payload.accuracy,
                source="browser_gps_short_code",
                problem_type=payload.problemType,
                problem_description=payload.problemDescription,
                vehicle_type=payload.vehicleType,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SessionLocationUpdateOut(session=updated.session.model_dump(mode="json"))


@router.get("/session/{code}")
async def get_session_by_code(code: str, db: AsyncSession = Depends(get_session)):
    session = await _session_by_code(db, code)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadcall session code not found")
    return await _session_view(db, session)


@router.get("/session/{code}/events")
async def session_events(code: str, db: AsyncSession = Depends(get_session)):
    async def stream():
        last_payload = ""
        for _ in range(450):
            session = await _session_by_code(db, code)
            if not session:
                yield "event: error\ndata: {\"detail\":\"Roadcall session code not found\"}\n\n"
                return
            payload = json.dumps(await _session_view(db, session), default=str)
            if payload != last_payload:
                yield f"event: session\ndata: {payload}\n\n"
                last_payload = payload
            if _is_expired(session) and session.location_captured_at is None:
                yield f"event: expired\ndata: {payload}\n\n"
                return
            await asyncio.sleep(2)
    return StreamingResponse(stream(), media_type="text/event-stream")
