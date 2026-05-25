"""Pre-call location sharing from the public website.

Visitor taps "Share my location & call Sandy" on the map -> we capture their
phone + GPS here so the inbound Retell call can attach it automatically.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.geocoding_service import GeocodingService
from app.services.shared_caller_location_service import (
    SharedCallerLocationService,
    normalize_phone,
)

router = APIRouter(prefix="/caller", tags=["caller-location"])


class ShareLocationIn(BaseModel):
    phone: str = Field(min_length=7, max_length=30)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)


class ShareLocationOut(BaseModel):
    ok: bool = True
    phone: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    expires_in_seconds: int


@router.post("/share-location", response_model=ShareLocationOut)
async def share_location(payload: ShareLocationIn):
    phone_e164 = normalize_phone(payload.phone)
    if not phone_e164:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Phone number must include at least 10 digits.",
        )

    reverse = await GeocodingService.reverse_geocode(payload.latitude, payload.longitude) or {}
    stored = await SharedCallerLocationService.store(
        phone=phone_e164,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        address=reverse.get("place_name") or reverse.get("address"),
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
        address=stored.get("address"),
        city=stored.get("city"),
        state=stored.get("state"),
        expires_in_seconds=stored.get("ttl_seconds", 0),
    )
