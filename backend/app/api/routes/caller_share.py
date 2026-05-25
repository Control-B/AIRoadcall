"""Pre-call location sharing from the public website.

Visitor taps "Share my location & call Sandy" on the map -> we capture their
phone + GPS here so the inbound Retell call can attach it automatically.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.dispatch_session import DispatchCreateSessionRequest
from app.services.geocoding_service import GeocodingService
from app.services.dispatch_session_service import DispatchSessionService
from app.services.shared_caller_location_service import (
    SharedCallerLocationService,
    normalize_phone,
)

router = APIRouter(prefix="/caller", tags=["caller-location"])


class ShareLocationIn(BaseModel):
    phone: str | None = Field(default=None, min_length=7, max_length=30)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)
    captured_at: datetime | None = None


class ShareLocationOut(BaseModel):
    ok: bool = True
    dispatch_session_id: UUID
    phone: str | None = None
    address: str | None = None
    readable_address: str | None = None
    city: str | None = None
    state: str | None = None
    latitude: float
    longitude: float
    accuracy: float | None = None
    captured_at: datetime
    status: str
    expires_in_seconds: int


@router.post("/share-location", response_model=ShareLocationOut)
async def share_location(payload: ShareLocationIn, db: AsyncSession = Depends(get_session)):
    phone_e164 = normalize_phone(payload.phone) if payload.phone else None
    if payload.phone and not phone_e164:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number must include at least 10 digits.",
        )

    reverse = await GeocodingService.reverse_geocode(payload.latitude, payload.longitude) or {}
    address = reverse.get("place_name") or reverse.get("address")
    captured_at = payload.captured_at or datetime.now(timezone.utc)
    session = await DispatchSessionService.create_session(
        db,
        DispatchCreateSessionRequest(
            source="map_phone_button",
            caller_phone=phone_e164,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy,
            location_source="browser_gps",
            city=reverse.get("city"),
            state=reverse.get("state"),
            address=address,
            expires_minutes=30,
            metadata={
                "map_shared_location": True,
                "map_location_captured_at": captured_at.isoformat(),
            },
        ),
    )

    if phone_e164:
        stored = await SharedCallerLocationService.store(
            phone=phone_e164,
            session_id=str(session.dispatch_session_id),
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy=payload.accuracy,
            address=address,
            city=reverse.get("city"),
            state=reverse.get("state"),
        )
        if stored is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Location cache is not available right now.",
            )

    return ShareLocationOut(
        phone=phone_e164,
        dispatch_session_id=session.dispatch_session_id,
        address=address,
        readable_address=address or ", ".join(item for item in [reverse.get("city"), reverse.get("state")] if item) or None,
        city=reverse.get("city"),
        state=reverse.get("state"),
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        captured_at=captured_at,
        status=session.status,
        expires_in_seconds=30 * 60,
    )
