from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_dispatch_location_token, decode_dispatch_location_token, hash_token
from app.models.dispatch_session import (
    DispatchLocationEvent,
    DispatchLocationToken,
    DispatchMatchResult,
    DispatchSession,
    DispatchSessionEvent,
    DispatchSessionStatus,
)
from app.schemas.dispatch_session import (
    DispatchCreateSessionRequest,
    DispatchCreateSessionResponse,
    DispatchLinkCaseCodeResponse,
    DispatchSessionStatusResponse,
    DispatchUpdateLocationRequest,
    DispatchUpdateLocationResponse,
)
from app.schemas.roadside_match import RoadsideMatchRequest, RoadsideMatchResponse
from app.services.geocoding_service import GeocodingService
from app.services.roadside_matching_service import RoadsideMatchingService
from app.services.session_cache_service import SessionCacheService
from app.utils.us_geo import infer_state_from_coordinates

_PHONE_DIGITS = re.compile(r"\D")

_CODE_PREFIXES = ("RC", "RD", "RA", "RS")


def normalize_phone_us(value: str | None) -> str | None:
    if not value:
        return None
    digits = _PHONE_DIGITS.sub("", value)
    if len(digits) < 10:
        return None
    return digits[-10:]


def phone_hash(value: str | None) -> str | None:
    phone10 = normalize_phone_us(value)
    return hash_token(phone10) if phone10 else None


def normalize_public_code(value: str | None) -> str:
    raw = (value or "").strip().upper()
    compact = re.sub(r"[^A-Z0-9]", "", raw)
    prefixed = re.fullmatch(r"([A-Z]{2})(\d{4})", compact)
    if prefixed:
        return f"{prefixed.group(1)}-{prefixed.group(2)}"
    digits = re.fullmatch(r"\d{4}", compact)
    if digits:
        return f"RC-{compact}"
    return re.sub(r"\s+", " ", raw.replace("-", " "))


def _public_code() -> str:
    prefix = secrets.choice(_CODE_PREFIXES)
    number = 1000 + secrets.randbelow(9000)
    return f"{prefix}-{number}"


def _public_url(token: str) -> str:
    return f"{get_settings().public_app_base_url}/go?t={token}"


class DispatchSessionService:
    @staticmethod
    async def create_session(db: AsyncSession, payload: DispatchCreateSessionRequest) -> DispatchCreateSessionResponse:
        existing = await DispatchSessionService._find_existing_session(db, payload)
        session = existing or DispatchSession(
            public_code=await DispatchSessionService._unique_public_code(db),
            status=DispatchSessionStatus.awaiting_location.value,
            source=payload.source or "api",
        )
        DispatchSessionService._apply_intake(session, payload)
        db.add(session)
        await db.flush()

        token_row, signed_token = await DispatchSessionService._issue_location_token(db, session, payload.expires_minutes)
        session.active_location_token_id = token_row.id
        await DispatchSessionService.record_event(db, session.id, "session.created" if not existing else "session.reused", "system", {
            "source": session.source,
            "has_retell_call_id": bool(session.retell_call_id),
            "has_twilio_call_sid": bool(session.twilio_call_sid),
        })
        await DispatchSessionService.record_event(db, session.id, "location.requested", "system", {"location_token_id": str(token_row.id)})
        await SessionCacheService.mirror_session(session, ttl_seconds=payload.expires_minutes * 60)
        return DispatchCreateSessionResponse(
            dispatch_session_id=session.id,
            public_code=session.public_code,
            status=session.status,
            location_url=_public_url(signed_token),
            location_token=signed_token,
            expires_at=token_row.expires_at,
        )

    @staticmethod
    async def update_location(db: AsyncSession, payload: DispatchUpdateLocationRequest) -> DispatchUpdateLocationResponse:
        claims = decode_dispatch_location_token(payload.token)
        if not claims:
            raise ValueError("Invalid or expired location token")
        token_id = uuid.UUID(str(claims["location_token_id"]))
        session_id = uuid.UUID(str(claims["dispatch_session_id"]))

        token_result = await db.execute(select(DispatchLocationToken).where(DispatchLocationToken.id == token_id))
        token_row = token_result.scalar_one_or_none()
        if not token_row or token_row.dispatch_session_id != session_id:
            raise ValueError("Location token does not match a dispatch session")
        if token_row.token_hash != hash_token(payload.token):
            raise ValueError("Location token signature mismatch")
        if token_row.revoked_at or token_row.expires_at < datetime.now(timezone.utc):
            raise ValueError("Location token is expired or revoked")

        session = await DispatchSessionService.get_session(db, session_id)
        if not session:
            raise ValueError("Dispatch session not found")

        city = payload.city
        state = payload.state
        address = payload.address
        rev = await GeocodingService.reverse_geocode(payload.latitude, payload.longitude)
        if rev:
            city = city or rev.get("city")
            state = state or rev.get("state")
            address = address or rev.get("address") or rev.get("place_name")
        if not state:
            state = infer_state_from_coordinates(payload.latitude, payload.longitude)

        session.lat = payload.latitude
        session.lng = payload.longitude
        session.location_accuracy_m = payload.accuracy_m
        session.location_source = payload.source
        session.location_captured_at = datetime.now(timezone.utc)
        session.city = city or session.city
        session.state = state or session.state
        session.address = address or session.address
        session.problem_type = payload.problem_type or session.problem_type
        session.problem_description = payload.problem_description or session.problem_description
        session.vehicle_type = payload.vehicle_type or session.vehicle_type
        session.status = DispatchSessionStatus.matching.value
        token_row.used_at = token_row.used_at or datetime.now(timezone.utc)

        db.add(DispatchLocationEvent(
            dispatch_session_id=session.id,
            lat=payload.latitude,
            lng=payload.longitude,
            accuracy_m=payload.accuracy_m,
            source=payload.source,
            raw_payload=payload.model_dump(exclude={"token"}, exclude_none=True),
        ))
        await DispatchSessionService.record_event(db, session.id, "location.updated", "caller", {
            "source": payload.source,
            "city": session.city,
            "state": session.state,
            "accuracy_m": payload.accuracy_m,
        }, is_public=True)

        match_response = await DispatchSessionService._run_match_if_ready(db, session)
        if match_response and match_response.status == "matched":
            session.status = DispatchSessionStatus.matched.value
        elif not match_response:
            session.status = DispatchSessionStatus.intake.value

        await SessionCacheService.mirror_session(session)
        return DispatchUpdateLocationResponse(ok=True, session=await DispatchSessionService.status_response(db, session))

    @staticmethod
    async def status_response(db: AsyncSession, session: DispatchSession) -> DispatchSessionStatusResponse:
        latest_match = await DispatchSessionService._latest_match(db, session.id)
        best_match = None
        missing_fields: list[str] = []
        match_status = None
        if latest_match:
            match_status = latest_match.status
            candidates = latest_match.candidates or []
            best_match = DispatchSessionService._ai_safe_best_match(candidates[0]) if candidates else None
        else:
            context = RoadsideMatchingService.build_context(DispatchSessionService._match_request(session))
            missing_fields = RoadsideMatchingService.missing_fields(context)

        return DispatchSessionStatusResponse(
            dispatch_session_id=session.id,
            public_code=session.public_code,
            status=session.status,
            location_captured=bool(session.location_captured_at),
            city=session.city,
            state=session.state,
            latitude=session.lat,
            longitude=session.lng,
            problem_type=session.problem_type,
            vehicle_type=session.vehicle_type,
            payment_status=session.payment_status,
            match_status=match_status,
            best_match=best_match,
            missing_fields=missing_fields,
            say=DispatchSessionService._say(session, best_match, missing_fields),
        )

    @staticmethod
    async def persist_go_dispatch(
        db: AsyncSession,
        *,
        caller_phone: str,
        caller_name: str | None,
        problem_description: str | None,
        problem_type: str | None,
        vehicle_type: str | None,
        latitude: float | None,
        longitude: float | None,
        accuracy_m: float | None,
        city: str | None,
        state: str | None,
        address: str | None,
        location_source: str,
        match_response: RoadsideMatchResponse,
    ) -> DispatchSession:
        create_payload = DispatchCreateSessionRequest(
            source="web_go",
            caller_phone=caller_phone,
            caller_name=caller_name,
            problem_type=problem_type,
            problem_description=problem_description,
            vehicle_type=vehicle_type,
            city=city,
            state=state,
            latitude=latitude,
            longitude=longitude,
            metadata={"go_flow": True},
        )
        existing = await DispatchSessionService._find_existing_session(db, create_payload)
        session = existing or DispatchSession(
            public_code=await DispatchSessionService._unique_public_code(db),
            status=DispatchSessionStatus.matched.value if match_response.status == "matched" else DispatchSessionStatus.intake.value,
            source="web_go",
        )
        DispatchSessionService._apply_intake(session, create_payload)
        session.lat = latitude
        session.lng = longitude
        session.location_accuracy_m = accuracy_m
        session.city = city or session.city
        session.state = state or session.state
        session.address = address or session.address
        session.location_source = location_source
        session.location_captured_at = datetime.now(timezone.utc) if latitude is not None and longitude is not None else session.location_captured_at
        session.status = DispatchSessionStatus.matched.value if match_response.status == "matched" else DispatchSessionStatus.intake.value
        db.add(session)
        await db.flush()

        if latitude is not None and longitude is not None:
            db.add(DispatchLocationEvent(
                dispatch_session_id=session.id,
                lat=latitude,
                lng=longitude,
                accuracy_m=accuracy_m,
                source=location_source,
                raw_payload={
                    "source": "go_dispatch",
                    "city": city,
                    "state": state,
                    "accuracy_m": accuracy_m,
                },
            ))
            await DispatchSessionService.record_event(db, session.id, "location.updated", "caller", {
                "source": location_source,
                "city": city,
                "state": state,
                "accuracy_m": accuracy_m,
            }, is_public=True)

        db.add(DispatchMatchResult(
            dispatch_session_id=session.id,
            request_context={
                "source": "go_dispatch",
                "city": city,
                "state": state,
                "latitude": latitude,
                "longitude": longitude,
                "problem_type": problem_type,
                "vehicle_type": vehicle_type,
            },
            search_level=match_response.searchLevel,
            status=match_response.status,
            candidates=[candidate.model_dump(mode="json") for candidate in match_response.matches],
            selected_mechanic_id=DispatchSessionService._safe_uuid(match_response.matches[0].mechanicId) if match_response.matches else None,
        ))
        await DispatchSessionService.record_event(db, session.id, "match.completed", "system", {
            "status": match_response.status,
            "match_count": len(match_response.matches),
            "search_level": match_response.searchLevel,
            "source": "go_dispatch",
        })
        return session

    @staticmethod
    async def latest_by_phone(db: AsyncSession, caller_phone: str) -> DispatchSession | None:
        phash = phone_hash(caller_phone)
        if not phash:
            return None
        result = await db.execute(
            select(DispatchSession)
            .where(DispatchSession.caller_phone_hash == phash)
            .order_by(desc(DispatchSession.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def link_case_code(db: AsyncSession, public_code: str, caller_phone_last4: str | None, expires_minutes: int) -> DispatchLinkCaseCodeResponse:
        result = await db.execute(select(DispatchSession).where(DispatchSession.public_code == normalize_public_code(public_code)))
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("Dispatch session not found")
        created_at = session.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at + timedelta(minutes=expires_minutes) < datetime.now(timezone.utc):
            raise ValueError("Roadcall session code has expired")
        if session.caller_phone_last4 and caller_phone_last4 and session.caller_phone_last4 != caller_phone_last4:
            raise ValueError("Case code does not match caller verification")
        token_row, signed_token = await DispatchSessionService._issue_location_token(db, session, expires_minutes)
        session.active_location_token_id = token_row.id
        await DispatchSessionService.record_event(db, session.id, "location.case_code_linked", "caller", {"location_token_id": str(token_row.id)})
        await SessionCacheService.mirror_session(session, ttl_seconds=expires_minutes * 60)
        return DispatchLinkCaseCodeResponse(
            dispatch_session_id=session.id,
            public_code=session.public_code,
            location_url=_public_url(signed_token),
            location_token=signed_token,
            expires_at=token_row.expires_at,
        )

    @staticmethod
    async def get_session(db: AsyncSession, session_id: uuid.UUID) -> DispatchSession | None:
        result = await db.execute(select(DispatchSession).where(DispatchSession.id == session_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def record_event(db: AsyncSession, session_id: uuid.UUID, event_type: str, actor_type: str, payload: dict[str, Any], *, is_public: bool = False) -> None:
        db.add(DispatchSessionEvent(
            dispatch_session_id=session_id,
            event_type=event_type,
            actor_type=actor_type,
            payload=payload,
            is_public=is_public,
        ))

    @staticmethod
    async def _find_existing_session(db: AsyncSession, payload: DispatchCreateSessionRequest) -> DispatchSession | None:
        clauses = []
        if payload.retell_call_id:
            clauses.append(DispatchSession.retell_call_id == payload.retell_call_id)
        if payload.twilio_call_sid:
            clauses.append(DispatchSession.twilio_call_sid == payload.twilio_call_sid)
        phash = phone_hash(payload.caller_phone)
        if phash:
            since = datetime.now(timezone.utc) - timedelta(minutes=30)
            clauses.append((DispatchSession.caller_phone_hash == phash) & (DispatchSession.created_at >= since))
        if not clauses:
            return None
        result = await db.execute(select(DispatchSession).where(or_(*clauses)).order_by(desc(DispatchSession.created_at)).limit(1))
        return result.scalar_one_or_none()

    @staticmethod
    async def _unique_public_code(db: AsyncSession) -> str:
        for _ in range(10):
            code = _public_code()
            result = await db.execute(select(DispatchSession.id).where(DispatchSession.public_code == code))
            if not result.scalar_one_or_none():
                return code
        return f"RC-{secrets.token_hex(4).upper()}"

    @staticmethod
    def _apply_intake(session: DispatchSession, payload: DispatchCreateSessionRequest) -> None:
        phone10 = normalize_phone_us(payload.caller_phone)
        session.source = payload.source or session.source
        session.retell_call_id = payload.retell_call_id or session.retell_call_id
        session.twilio_call_sid = payload.twilio_call_sid or session.twilio_call_sid
        session.caller_name = payload.caller_name or session.caller_name
        session.caller_phone_hash = phone_hash(payload.caller_phone) or session.caller_phone_hash
        session.caller_phone_encrypted = phone10 or session.caller_phone_encrypted
        session.caller_phone_last4 = phone10[-4:] if phone10 else session.caller_phone_last4
        session.problem_type = payload.problem_type or session.problem_type
        session.problem_description = payload.problem_description or session.problem_description
        session.vehicle_type = payload.vehicle_type or session.vehicle_type
        session.vehicle_description = payload.vehicle_description or session.vehicle_description
        session.city = payload.city or session.city
        session.state = payload.state or session.state
        session.lat = payload.latitude if payload.latitude is not None else session.lat
        session.lng = payload.longitude if payload.longitude is not None else session.lng
        session.metadata_json = {**(session.metadata_json or {}), **payload.metadata}
        if session.lat is not None and session.lng is not None:
            session.location_captured_at = session.location_captured_at or datetime.now(timezone.utc)

    @staticmethod
    async def _issue_location_token(db: AsyncSession, session: DispatchSession, expires_minutes: int) -> tuple[DispatchLocationToken, str]:
        placeholder_id = uuid.uuid4()
        token = create_dispatch_location_token(str(session.id), session.public_code, str(placeholder_id), expires_minutes=expires_minutes)
        token_row = DispatchLocationToken(
            id=placeholder_id,
            dispatch_session_id=session.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        )
        db.add(token_row)
        await db.flush()
        return token_row, token

    @staticmethod
    async def _run_match_if_ready(db: AsyncSession, session: DispatchSession) -> RoadsideMatchResponse | None:
        request = DispatchSessionService._match_request(session)
        context = RoadsideMatchingService.build_context(request)
        missing = RoadsideMatchingService.missing_fields(context)
        if missing:
            await DispatchSessionService.record_event(db, session.id, "intake.missing_fields", "system", {"missing_fields": missing})
            return None
        response = await RoadsideMatchingService.match_mechanic(db, request)
        db.add(DispatchMatchResult(
            dispatch_session_id=session.id,
            request_context=request.model_dump(exclude_none=True),
            search_level=response.searchLevel,
            status=response.status,
            candidates=[candidate.model_dump(mode="json") for candidate in response.matches],
            selected_mechanic_id=DispatchSessionService._safe_uuid(response.matches[0].mechanicId) if response.matches else None,
        ))
        await DispatchSessionService.record_event(db, session.id, "match.completed", "system", {
            "status": response.status,
            "match_count": len(response.matches),
            "search_level": response.searchLevel,
        })
        return response

    @staticmethod
    def _match_request(session: DispatchSession) -> RoadsideMatchRequest:
        return RoadsideMatchRequest(
            message=session.problem_description or "",
            city=session.city,
            state=session.state,
            latitude=session.lat,
            longitude=session.lng,
            vehicleType=session.vehicle_type,
            problemType=session.problem_type,
            callerPhone=session.caller_phone_encrypted,
            callbackNumber=session.caller_phone_encrypted,
            limit=3,
        )

    @staticmethod
    async def _latest_match(db: AsyncSession, session_id: uuid.UUID) -> DispatchMatchResult | None:
        result = await db.execute(
            select(DispatchMatchResult)
            .where(DispatchMatchResult.dispatch_session_id == session_id)
            .order_by(desc(DispatchMatchResult.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _ai_safe_best_match(candidate: dict[str, Any]) -> dict[str, Any]:
        return {
            "mechanic_id": candidate.get("mechanicId"),
            "company_name": candidate.get("businessName"),
            "city": candidate.get("city"),
            "state": candidate.get("state"),
            "distance_miles": candidate.get("distanceMiles"),
            "score": candidate.get("score"),
            "phone_available": bool(candidate.get("phone")),
            "reason": candidate.get("reason"),
        }

    @staticmethod
    def _safe_uuid(value: str | None) -> uuid.UUID | None:
        if not value:
            return None
        try:
            return uuid.UUID(str(value))
        except ValueError:
            return None

    @staticmethod
    def _say(session: DispatchSession, best_match: dict[str, Any] | None, missing_fields: list[str]) -> str:
        if missing_fields:
            if "location" in missing_fields or "state" in missing_fields:
                return "I still need your city and state, or you can use the secure GPS link."
            if "problemType" in missing_fields:
                return "What problem are you having — tire, engine, battery, fuel, towing, or something else?"
            if "vehicleType" in missing_fields:
                return "What type of vehicle is it — car, pickup, box truck, semi, trailer, RV, or fleet vehicle?"
        if best_match:
            location = ", ".join(item for item in [best_match.get("city"), best_match.get("state")] if item)
            return f"I found {best_match['company_name']} near {location or 'your area'}. I’m confirming availability now."
        if session.location_captured_at:
            return "I have your location and I’m checking the best nearby provider now."
        return f"I created your Roadcall session code {session.public_code}. Please go to roadcall.ai slash go and enter that code so I can find nearby help."