"""Public website-first dispatch flow used by roadcall.ai/go.

Replaces SMS-based magic link while Twilio A2P is pending.

Flow:
  Driver opens roadcall.ai/go on their phone
  → enters phone number, taps Submit
  → browser captures GPS via navigator.geolocation
  → POST /api/go/dispatch  { phone, latitude, longitude, accuracy?, problem?, vehicle_type? }
  → backend reverse-geocodes via Mapbox, runs RoadsideMatchingService.match_mechanic,
    caches the result for the polling endpoint, returns the top mechanic options.
  → page displays tap-to-call options + status. The Retell agent on the live call
    can poll /api/go/status/{phone} (or use match_mechanic directly with the resolved
    city/state) to read the same options to the driver.
"""
from __future__ import annotations

import re
import time
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.roadside_match import RoadsideMatchRequest, RoadsideMatchResponse
from app.services.geocoding_service import GeocodingService
from app.services.roadside_matching_service import RoadsideMatchingService
from app.utils.us_geo import infer_state_from_coordinates

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/go", tags=["go"])

_PHONE_DIGITS = re.compile(r"\D")
# In-memory cache: phone (10-digit) -> (timestamp, response_dict)
_DISPATCH_CACHE: dict[str, tuple[float, dict]] = {}
_DISPATCH_CACHE_TTL_SECONDS = 600  # 10 min — driver should be matched well before this


def _normalize_phone_us(value: Optional[str]) -> Optional[str]:
    """Return last-10 digits of a US phone number, or None."""
    if not value:
        return None
    digits = _PHONE_DIGITS.sub("", value)
    if len(digits) < 10:
        return None
    return digits[-10:]


def _format_e164_us(ten_digit: str) -> str:
    return f"+1{ten_digit}"


# ──────────────────────────────────────────────────────────
# Request / response models
# ──────────────────────────────────────────────────────────
class GoDispatchRequest(BaseModel):
    phone: str = Field(..., description="Driver's phone number — any format")
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    accuracy_m: Optional[float] = Field(default=None, description="GPS accuracy in meters from browser geolocation")
    # Manual fallback if geolocation denied
    city: Optional[str] = None
    state: Optional[str] = None
    problem: Optional[str] = Field(default=None, description="Free-text problem description")
    vehicle_type: Optional[str] = None
    name: Optional[str] = None


class ResolvedLocation(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    place_name: Optional[str] = None
    accuracy_m: Optional[float] = None
    source: str  # "browser_gps" | "manual_form" | "mixed"


class GoDispatchResponse(BaseModel):
    work_order_id: str  # Phone-as-WO-id (10-digit)
    status: str  # "matched" | "needs_more_info" | "manual_dispatch_required"
    location: ResolvedLocation
    match: RoadsideMatchResponse


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────
@router.post("/dispatch", response_model=GoDispatchResponse)
async def go_dispatch(
    payload: GoDispatchRequest,
    db: AsyncSession = Depends(get_session),
):
    """Driver hits Submit on /go — kick off mechanic matching."""
    phone10 = _normalize_phone_us(payload.phone)
    if not phone10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid 10-digit US phone number.",
        )

    has_gps = payload.latitude is not None and payload.longitude is not None
    has_manual = bool((payload.city or "").strip() and (payload.state or "").strip())
    if not has_gps and not has_manual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need either GPS location or city + state.",
        )

    # Resolve location
    resolved_city = (payload.city or "").strip() or None
    resolved_state = (payload.state or "").strip() or None
    resolved_address: Optional[str] = None
    resolved_place_name: Optional[str] = None
    source = "manual_form"

    if has_gps:
        rev = await GeocodingService.reverse_geocode(payload.latitude, payload.longitude)  # type: ignore[arg-type]
        if rev:
            resolved_city = rev.get("city") or resolved_city
            resolved_state = rev.get("state") or resolved_state
            resolved_address = rev.get("address")
            resolved_place_name = rev.get("place_name")
            source = "browser_gps" if not has_manual else "mixed"
        else:
            # Mapbox failed but we still have raw coordinates — matching can still proceed
            source = "browser_gps" if not has_manual else "mixed"

    if has_gps and not resolved_state:
        resolved_state = infer_state_from_coordinates(payload.latitude, payload.longitude)

    # Build matching request.
    # If the driver didn't tell us the problem yet, fall back to a generic
    # "other" classification so the matcher still returns nearby mechanics
    # ranked by location/trust. The /go UX would otherwise dead-end on
    # needs_more_info=problemType, which the user reads as a failure.
    effective_problem = (payload.problem or "tow_needed").strip() or "tow_needed"
    match_req = RoadsideMatchRequest(
        message=payload.problem or "",
        city=resolved_city,
        state=resolved_state,
        latitude=payload.latitude,
        longitude=payload.longitude,
        vehicleType=payload.vehicle_type or "box truck",
        problemType=effective_problem,
        callerPhone=_format_e164_us(phone10),
        callbackNumber=_format_e164_us(phone10),
        limit=3,
    )

    try:
        match_resp = await RoadsideMatchingService.match_mechanic(db, match_req)
    except Exception as exc:
        logger.exception("go_dispatch_match_failed phone=%s err=%s", phone10, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="We could not run the mechanic search right now. Please call us back.",
        ) from exc

    if not resolved_city and match_resp.matches:
        resolved_city = match_resp.matches[0].city
    if not resolved_state and match_resp.matches:
        resolved_state = match_resp.matches[0].state

    location = ResolvedLocation(
        latitude=payload.latitude,
        longitude=payload.longitude,
        city=resolved_city,
        state=resolved_state,
        address=resolved_address,
        place_name=resolved_place_name,
        accuracy_m=payload.accuracy_m,
        source=source,
    )

    response = GoDispatchResponse(
        work_order_id=phone10,
        status=match_resp.status,
        location=location,
        match=match_resp,
    )

    # Cache for the status endpoint
    _DISPATCH_CACHE[phone10] = (time.monotonic(), response.model_dump(mode="json"))

    logger.info(
        "go_dispatch phone=%s city=%s state=%s source=%s status=%s matches=%d major_vendor=%s",
        phone10,
        resolved_city,
        resolved_state,
        source,
        match_resp.status,
        len(match_resp.matches),
        bool(match_resp.majorVendor),
    )
    return response


@router.get("/status/{phone}", response_model=GoDispatchResponse)
async def go_status(phone: str):
    """Return the most recent dispatch result for this phone number.

    Used by the /go page itself to poll for status changes, and by the Retell
    agent (via existing get_dispatch_status tool) to read options aloud once
    the driver hits Submit.
    """
    phone10 = _normalize_phone_us(phone)
    if not phone10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid phone number.")
    cached = _DISPATCH_CACHE.get(phone10)
    if not cached:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No dispatch found for that number yet.",
        )
    ts, data = cached
    if time.monotonic() - ts > _DISPATCH_CACHE_TTL_SECONDS:
        _DISPATCH_CACHE.pop(phone10, None)
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Dispatch session expired. Please re-submit on roadcall.ai/go.",
        )
    return data
