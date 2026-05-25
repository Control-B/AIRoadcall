"""Browser WebRTC call to the Sandy roadside Retell agent with GPS context."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api.deps import get_session
from app.core.config import get_settings
from app.schemas.dispatch_session import DispatchCreateSessionRequest
from app.services.dispatch_session_service import DispatchSessionService
from app.services.geocoding_service import GeocodingService

router = APIRouter(prefix="/retell", tags=["retell-web"])
logger = logging.getLogger(__name__)


class RoadsideWebCallIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_meters: float | None = None
    caller_phone: str | None = None
    captured_at: datetime | None = None


class RoadsideWebCallLocation(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: float | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None


class RoadsideWebCallOut(BaseModel):
    ok: bool
    call_id: str | None
    access_token: str
    session_id: UUID
    agent_id: str
    location: RoadsideWebCallLocation


_DIGITS_RE = re.compile(r"\D")


def _normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = _DIGITS_RE.sub("", value)
    if not digits:
        return None
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if value.startswith("+") and 8 <= len(digits) <= 15:
        return f"+{digits}"
    return None


def _retell_create_web_call(api_key: str, body: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        "https://api.retellai.com/v2/create-web-call",
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:800]
        logger.error("Retell create-web-call HTTP %s: %s", exc.code, detail)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Retell rejected web call ({exc.code}): {detail}",
        ) from exc
    except urllib.error.URLError as exc:
        logger.exception("Retell create-web-call network error")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Retell network error: {exc}",
        ) from exc


@router.post("/roadside-web-call", response_model=RoadsideWebCallOut)
async def create_roadside_web_call(
    payload: RoadsideWebCallIn,
    db: AsyncSession = Depends(get_session),
) -> RoadsideWebCallOut:
    settings = get_settings()
    if not settings.RETELL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retell is not configured for this environment.",
        )
    # Prefer the main Sandy phone agent because it is the canonical agent tied
    # to the GPS-aware conversation flow. A separate web agent can drift stale
    # in Retell and ignore the map call's pre-shared location.
    agent_id = (settings.RETELL_AGENT_ID or settings.RETELL_ROADSIDE_WEB_AGENT_ID or "").strip()
    if not agent_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No Sandy Retell agent is configured (set RETELL_ROADSIDE_WEB_AGENT_ID or RETELL_AGENT_ID).",
        )

    phone_e164 = _normalize_phone(payload.caller_phone)
    reverse = await GeocodingService.reverse_geocode(payload.latitude, payload.longitude) or {}
    address = reverse.get("place_name") or reverse.get("address")
    city = reverse.get("city")
    state = reverse.get("state")

    # Self-contained, always-non-empty phrase the agent can speak verbatim
    # even when Mapbox reverse-geocode fails. Referenced as
    # {{caller_location_phrase}} in the GPS-aware flow opening line.
    if address and city and state:
        location_phrase = f"near {address} in {city}, {state}"
    elif city and state:
        location_phrase = f"in {city}, {state}"
    elif address:
        location_phrase = f"near {address}"
    else:
        location_phrase = (
            f"at the GPS spot you just shared "
            f"(roughly {payload.latitude:.4f}, {payload.longitude:.4f})"
        )

    session = await DispatchSessionService.create_session(
        db,
        DispatchCreateSessionRequest(
            source="retell_web_gps",
            caller_phone=phone_e164,
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_m=payload.accuracy_meters,
            location_source="browser_gps",
            city=reverse.get("city"),
            state=reverse.get("state"),
            address=address,
            metadata={
                "retell_web_session": True,
                "map_location_captured_at": (
                    payload.captured_at or datetime.now(timezone.utc)
                ).isoformat(),
            },
        ),
    )

    dynamic_vars: dict[str, str] = {
        "dispatch_session_id": str(session.dispatch_session_id),
        "gps_latitude": f"{payload.latitude:.6f}",
        "gps_longitude": f"{payload.longitude:.6f}",
        "gps_accuracy_meters": str(int(payload.accuracy_meters)) if payload.accuracy_meters else "",
        "caller_address": address or "",
        "caller_city": reverse.get("city") or "",
        "caller_state": reverse.get("state") or "",
        "caller_location_phrase": location_phrase,
        "web_call_opening_instruction": (
            f"Start by saying: Thanks for reaching Roadcall through the map. "
            f"This is Sandy. I can see you {location_phrase}. Who am I speaking with? "
            "Treat this GPS location as already shared and verified. Do not ask for city, "
            "state, address, nearest road, or a location link unless the caller corrects it."
        ),
        "caller_source": "roadcall_map_button",
        "has_shared_gps": "true",
    }

    body = {
        "agent_id": agent_id,
        "metadata": {
            "source": "roadcall_map_web",
            "dispatch_session_id": str(session.dispatch_session_id),
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "caller_address": address,
            "caller_city": city,
            "caller_state": state,
        },
        "retell_llm_dynamic_variables": dynamic_vars,
        "current_node_id": "start-node",
    }

    response = await asyncio.to_thread(
        _retell_create_web_call, settings.RETELL_API_KEY.strip(), body
    )
    access_token = response.get("access_token")
    if not access_token:
        logger.error("Retell web call returned no access_token: %s", response)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Retell did not return an access token.",
        )

    return RoadsideWebCallOut(
        ok=True,
        call_id=response.get("call_id"),
        access_token=access_token,
        session_id=session.dispatch_session_id,
        agent_id=agent_id,
        location=RoadsideWebCallLocation(
            latitude=payload.latitude,
            longitude=payload.longitude,
            accuracy_meters=payload.accuracy_meters,
            address=address,
            city=reverse.get("city"),
            state=reverse.get("state"),
        ),
    )
