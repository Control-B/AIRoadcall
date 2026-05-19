from __future__ import annotations

import math
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.active_call_session import ActiveCallSession
from app.schemas.roadside_match import RoadsideMatchRequest, RoadsideMechanicMatch
from app.services.geocoding_service import GeocodingService
from app.services.roadside_matching_service import RoadsideMatchingService

settings = get_settings()
_PHONE_DIGITS = re.compile(r"\D")


class CallerLocationService:
    SESSION_TTL_MINUTES = 30

    @staticmethod
    def public_location_url(location_code: str) -> str:
        return f"{settings.public_app_base_url}/go?code={location_code}"

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _normalize_phone(value: str | None) -> str | None:
        if not value:
            return None
        digits = _PHONE_DIGITS.sub("", value)
        if len(digits) >= 10:
            return f"+1{digits[-10:]}"
        return value.strip() or None

    @staticmethod
    def _phone_last4(value: str | None) -> str | None:
        if not value:
            return None
        digits = _PHONE_DIGITS.sub("", value)
        return digits[-4:] if len(digits) >= 4 else None

    @classmethod
    async def create_or_refresh_session(
        cls,
        db: AsyncSession,
        *,
        provider_call_id: str,
        caller_phone: str | None,
        call_provider: str = "retell",
    ) -> ActiveCallSession:
        result = await db.execute(select(ActiveCallSession).where(ActiveCallSession.provider_call_id == provider_call_id))
        session = result.scalar_one_or_none()
        if session is None:
            session = ActiveCallSession(
                call_provider=call_provider,
                provider_call_id=provider_call_id,
                caller_phone=cls._normalize_phone(caller_phone),
                location_code=await cls._unique_location_code(db),
                status="waiting_for_location",
                expires_at=cls._now() + timedelta(minutes=cls.SESSION_TTL_MINUTES),
            )
            db.add(session)
        else:
            session.call_provider = call_provider or session.call_provider
            session.caller_phone = cls._normalize_phone(caller_phone) or session.caller_phone
            session.expires_at = cls._now() + timedelta(minutes=cls.SESSION_TTL_MINUTES)
            if session.status in {"failed", "expired"}:
                session.status = "waiting_for_location"
        await db.flush()
        return session

    @classmethod
    async def _unique_location_code(cls, db: AsyncSession) -> str:
        for _ in range(30):
            code = f"{random.randint(0, 9999):04d}"
            existing = await db.execute(select(ActiveCallSession.id).where(ActiveCallSession.location_code == code))
            if existing.scalar_one_or_none() is None:
                return code
        return uuid.uuid4().hex[:8].upper()

    @classmethod
    async def submit_gps_location(
        cls,
        db: AsyncSession,
        *,
        location_code: str,
        phone_last4: str | None,
        latitude: float,
        longitude: float,
        accuracy: float | None,
    ) -> ActiveCallSession:
        session = await cls.session_by_code(db, location_code)
        cls._assert_active(session)
        expected_last4 = cls._phone_last4(session.caller_phone)
        provided_last4 = cls._phone_last4(phone_last4)
        if expected_last4 and provided_last4 and expected_last4 != provided_last4:
            raise PermissionError("Phone verification did not match this call session")

        reverse = await GeocodingService.reverse_geocode(latitude, longitude)
        session.latitude = latitude
        session.longitude = longitude
        session.accuracy = accuracy
        session.address = (reverse or {}).get("place_name") or (reverse or {}).get("address")
        session.city = (reverse or {}).get("city") or session.city
        session.state = (reverse or {}).get("state") or session.state
        session.status = "location_received"
        await db.flush()
        return session

    @classmethod
    async def submit_manual_location(
        cls,
        db: AsyncSession,
        *,
        provider_call_id: str | None = None,
        location_code: str | None = None,
        location_text: str,
    ) -> tuple[ActiveCallSession, dict[str, Any] | None]:
        session = await (cls.session_by_code(db, location_code) if location_code else cls.session_by_provider_call_id(db, provider_call_id))
        cls._assert_active(session)
        geocoded = await GeocodingService.geocode_location(location_text)
        session.manual_location_text = location_text
        session.highway_or_exit = location_text
        if geocoded:
            session.latitude = geocoded.get("latitude")
            session.longitude = geocoded.get("longitude")
            session.address = geocoded.get("normalized_location")
            session.city = geocoded.get("city") or session.city
            session.state = geocoded.get("state") or session.state
            session.accuracy = None
            session.status = "location_received"
        else:
            session.status = "waiting_for_location"
        await db.flush()
        return session, geocoded

    @classmethod
    async def session_by_code(cls, db: AsyncSession, location_code: str | None) -> ActiveCallSession:
        code = (location_code or "").strip().upper()
        if not code:
            raise LookupError("location_code is required")
        result = await db.execute(select(ActiveCallSession).where(ActiveCallSession.location_code == code))
        session = result.scalar_one_or_none()
        if not session:
            raise LookupError("Location code not found")
        if session.expires_at < cls._now() and session.status == "waiting_for_location":
            session.status = "failed"
        return session

    @classmethod
    async def session_by_provider_call_id(cls, db: AsyncSession, provider_call_id: str | None) -> ActiveCallSession:
        if not provider_call_id:
            raise LookupError("provider_call_id is required")
        result = await db.execute(select(ActiveCallSession).where(ActiveCallSession.provider_call_id == provider_call_id))
        session = result.scalar_one_or_none()
        if not session:
            raise LookupError("Active call session not found")
        if session.expires_at < cls._now() and session.status == "waiting_for_location":
            session.status = "failed"
        return session

    @classmethod
    async def match_mechanics(
        cls,
        db: AsyncSession,
        *,
        provider_call_id: str,
        service_type: str,
        vehicle_type: str,
        urgency: str | None = None,
    ) -> tuple[ActiveCallSession, list[dict[str, Any]]]:
        session = await cls.session_by_provider_call_id(db, provider_call_id)
        if session.latitude is None or session.longitude is None:
            raise ValueError("Caller location is not confirmed yet")
        session.status = "matching"
        request = RoadsideMatchRequest(
            message=service_type or "roadside assistance",
            city=session.city,
            state=session.state,
            latitude=session.latitude,
            longitude=session.longitude,
            vehicleType=vehicle_type or "box truck",
            problemType=cls.problem_type_for(service_type),
            callerPhone=session.caller_phone,
            callbackNumber=session.caller_phone,
            limit=3,
        )
        response = await RoadsideMatchingService.match_mechanic(db, request)
        matches = [cls._match_view(match, service_type, urgency) for match in response.matches[:3]]
        session.status = "matched" if matches else "failed"
        await db.flush()
        return session, matches

    @staticmethod
    def _match_view(match: RoadsideMechanicMatch, service_type: str, urgency: str | None) -> dict[str, Any]:
        reasons = []
        if match.distanceMiles is not None:
            reasons.append(f"about {match.distanceMiles:.1f} miles away")
        if match.mobileService:
            reasons.append("offers mobile roadside service")
        if match.emergencyService or urgency in {"urgent", "high", "emergency"}:
            reasons.append("can handle urgent roadside calls")
        if service_type:
            reasons.append(f"matches {service_type}")
        if match.reason:
            reasons.append(match.reason)
        return {
            "mechanic_id": match.mechanicId,
            "business_name": match.businessName,
            "phone": match.phone,
            "distance_miles": match.distanceMiles,
            "match_score": round(match.score, 2),
            "reason_for_match": "; ".join(dict.fromkeys(reasons)),
            "services": match.services,
            "open_now": bool(match.emergencyService),
            "mobile_service": match.mobileService,
            "city": match.city,
            "state": match.state,
        }

    @staticmethod
    def problem_type_for(service_type: str | None) -> str:
        value = (service_type or "").lower()
        if any(term in value for term in ("tire", "flat", "blowout")):
            return "flat_tire"
        if any(term in value for term in ("battery", "jump", "alternator")):
            return "dead_battery"
        if any(term in value for term in ("fuel", "gas", "def")):
            return "fuel_delivery"
        if any(term in value for term in ("tow", "wrecker", "stuck")):
            return "tow_needed"
        if any(term in value for term in ("lock", "keys")):
            return "lockout"
        if any(term in value for term in ("trailer", "reefer", "brake", "air leak")):
            return "trailer_repair"
        if any(term in value for term in ("engine", "diesel", "overheat", "dpf", "derate", "no start")):
            return "engine_trouble"
        return "tow_needed"

    @classmethod
    def _assert_active(cls, session: ActiveCallSession) -> None:
        if session.expires_at < cls._now():
            session.status = "failed"
            raise TimeoutError("Location code has expired")

    @staticmethod
    def location_status(session: ActiveCallSession) -> dict[str, Any]:
        return {
            "status": session.status,
            "latitude": session.latitude,
            "longitude": session.longitude,
            "address": session.address,
            "city": session.city,
            "state": session.state,
            "highway_or_exit": session.highway_or_exit,
            "accuracy": session.accuracy,
            "location_code": session.location_code,
            "location_url": CallerLocationService.public_location_url(session.location_code),
            "expires_at": session.expires_at.isoformat(),
        }
