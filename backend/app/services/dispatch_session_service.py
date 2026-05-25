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
    ActiveCallContext,
    ActiveCallContextRequest,
    ActiveCallContextResponse,
    DispatchCreateSessionRequest,
    DispatchCreateSessionResponse,
    DispatchLinkCaseCodeResponse,
    DispatchSessionStatusResponse,
    DispatchUpdateLocationRequest,
    DispatchUpdateLocationResponse,
    SharedLocationContext,
)
from app.schemas.roadside_match import RoadsideMatchRequest, RoadsideMatchResponse
from app.services.geocoding_service import GeocodingService
from app.services.roadside_matching_service import RoadsideMatchingService
from app.services.session_cache_service import SessionCacheService
from app.services.shared_caller_location_service import SharedCallerLocationService
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
    async def active_call_context(db: AsyncSession, payload: ActiveCallContextRequest) -> ActiveCallContextResponse:
        created = await DispatchSessionService.create_session(
            db,
            DispatchCreateSessionRequest(
                source=payload.source or "retell",
                retell_call_id=payload.retell_call_id,
                caller_phone=payload.caller_phone,
                expires_minutes=payload.expires_minutes,
                metadata={"active_call_context_requested": True},
            ),
        )
        session = await DispatchSessionService.get_session(db, created.dispatch_session_id)
        if not session:
            raise ValueError("Dispatch session not found after active call context creation")
        context = DispatchSessionService._active_call_context(session)
        return ActiveCallContextResponse(
            active_call_context=context,
            say=DispatchSessionService._active_call_context_say(context),
        )

    @staticmethod
    async def create_session(db: AsyncSession, payload: DispatchCreateSessionRequest) -> DispatchCreateSessionResponse:
        existing = await DispatchSessionService._find_existing_session(db, payload)
        map_fallback_attached = False
        if DispatchSessionService._is_retell_session(payload) and (not existing or existing.lat is None or existing.lng is None):
            map_session = await DispatchSessionService._find_recent_map_shared_session(db)
            if map_session and (not existing or map_session.id != existing.id):
                existing = map_session
                map_fallback_attached = True
        session = existing or DispatchSession(
            public_code=await DispatchSessionService._unique_public_code(db),
            status=DispatchSessionStatus.awaiting_location.value,
            source=payload.source or "api",
        )
        DispatchSessionService._apply_intake(session, payload)
        shared_location = await DispatchSessionService._consume_pre_shared_location(payload.caller_phone)
        if shared_location:
            DispatchSessionService._apply_shared_location(session, shared_location)
        db.add(session)
        await db.flush()

        token_row, signed_token = await DispatchSessionService._issue_location_token(db, session, payload.expires_minutes)
        session.active_location_token_id = token_row.id
        await DispatchSessionService.record_event(db, session.id, "session.created" if not existing else "session.reused", "system", {
            "source": session.source,
            "has_retell_call_id": bool(session.retell_call_id),
            "has_twilio_call_sid": bool(session.twilio_call_sid),
            "has_pre_shared_location": bool(shared_location),
            "map_fallback_attached": map_fallback_attached,
        })
        if shared_location:
            await DispatchSessionService.record_event(db, session.id, "location.updated", "caller", {
                "source": "map_phone_button",
                "city": session.city,
                "state": session.state,
                "accuracy_m": session.location_accuracy_m,
            }, is_public=True)
        else:
            await DispatchSessionService.record_event(db, session.id, "location.requested", "system", {"location_token_id": str(token_row.id)})
        await SessionCacheService.mirror_session(session, ttl_seconds=payload.expires_minutes * 60)
        return DispatchCreateSessionResponse(
            dispatch_session_id=session.id,
            public_code=session.public_code,
            status=session.status,
            location_url=_public_url(signed_token),
            location_token=signed_token,
            expires_at=token_row.expires_at,
            location_captured=bool(session.location_captured_at),
            city=session.city,
            state=session.state,
            address=session.address,
            latitude=session.lat,
            longitude=session.lng,
            location_accuracy_m=session.location_accuracy_m,
            location_source=session.location_source,
            location_captured_at=session.location_captured_at,
            say=DispatchSessionService._say(
                session,
                None,
                ["problemType", "vehicleType"] if session.location_captured_at else ["location"],
            ),
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
            if not missing_fields:
                match_response = await DispatchSessionService._run_match_if_ready(db, session)
                if match_response:
                    session.status = DispatchSessionStatus.matched.value if match_response.status == "matched" else DispatchSessionStatus.manual_review.value
                    latest_match = await DispatchSessionService._latest_match(db, session.id)
                    if latest_match:
                        match_status = latest_match.status
                        candidates = latest_match.candidates or []
                        best_match = DispatchSessionService._ai_safe_best_match(candidates[0]) if candidates else None
                    missing_fields = []

        return DispatchSessionStatusResponse(
            dispatch_session_id=session.id,
            public_code=session.public_code,
            status=session.status,
            location_captured=bool(session.location_captured_at),
            city=session.city,
            state=session.state,
            address=session.address,
            latitude=session.lat,
            longitude=session.lng,
            location_accuracy_m=session.location_accuracy_m,
            location_source=session.location_source,
            location_captured_at=session.location_captured_at,
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
    def _is_retell_session(payload: DispatchCreateSessionRequest) -> bool:
        return (payload.source or "").lower() == "retell" or bool(payload.retell_call_id)

    @staticmethod
    async def _find_recent_map_shared_session(db: AsyncSession) -> DispatchSession | None:
        since = datetime.now(timezone.utc) - timedelta(minutes=10)
        result = await db.execute(
            select(DispatchSession)
            .where(
                DispatchSession.source == "map_phone_button",
                DispatchSession.lat.is_not(None),
                DispatchSession.lng.is_not(None),
                DispatchSession.location_captured_at.is_not(None),
                DispatchSession.retell_call_id.is_(None),
                or_(DispatchSession.location_captured_at >= since, DispatchSession.updated_at >= since),
                DispatchSession.status.notin_([
                    DispatchSessionStatus.completed.value,
                    DispatchSessionStatus.cancelled.value,
                ]),
            )
            .order_by(desc(DispatchSession.location_captured_at), desc(DispatchSession.updated_at))
            .limit(1)
        )
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
        session.address = payload.address or session.address
        session.lat = payload.latitude if payload.latitude is not None else session.lat
        session.lng = payload.longitude if payload.longitude is not None else session.lng
        session.location_accuracy_m = payload.accuracy_m if payload.accuracy_m is not None else session.location_accuracy_m
        session.location_source = payload.location_source or session.location_source
        session.metadata_json = {**(session.metadata_json or {}), **payload.metadata}
        if session.lat is not None and session.lng is not None:
            if payload.latitude is not None and payload.longitude is not None:
                session.location_captured_at = datetime.now(timezone.utc)
            else:
                session.location_captured_at = session.location_captured_at or datetime.now(timezone.utc)
            if session.status in {DispatchSessionStatus.created.value, DispatchSessionStatus.awaiting_location.value}:
                session.status = DispatchSessionStatus.matching.value

    @staticmethod
    async def _consume_pre_shared_location(caller_phone: str | None) -> dict[str, Any] | None:
        if not caller_phone:
            return None
        shared = await SharedCallerLocationService.lookup(caller_phone)
        if not shared or shared.get("latitude") is None or shared.get("longitude") is None:
            return None
        return shared

    @staticmethod
    def _apply_shared_location(session: DispatchSession, shared: dict[str, Any]) -> None:
        session.lat = shared["latitude"]
        session.lng = shared["longitude"]
        session.location_accuracy_m = shared.get("accuracy")
        session.location_source = "map_phone_button"
        session.location_captured_at = datetime.now(timezone.utc)
        session.city = shared.get("city") or session.city
        session.state = shared.get("state") or session.state
        session.address = shared.get("address") or session.address
        session.status = DispatchSessionStatus.matching.value
        metadata = session.metadata_json or {}
        session.metadata_json = {
            **metadata,
            "pre_shared_location": True,
            "pre_shared_location_session_id": shared.get("session_id"),
            "pre_shared_location_phone": shared.get("phone"),
            "pre_shared_location_captured_at": shared.get("captured_at"),
        }

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
        location_label = DispatchSessionService._location_label(session)
        if missing_fields:
            if session.location_captured_at and "problemType" in missing_fields:
                if location_label:
                    return f"I see your shared location near {location_label}. Is that correct?"
                return "I received your shared GPS, but I could not translate it into a city and state. What city and state are you in, and what nearest major road or highway are you by?"
            if "location" in missing_fields or "state" in missing_fields:
                return "I cannot see your shared location yet. Please tell me your city, state, and nearest major road or highway."
            if "problemType" in missing_fields:
                return "What problem are you having — tire, engine, battery, fuel, towing, or something else?"
            if "vehicleType" in missing_fields:
                return "What type of vehicle do you need assistance for?"
        if best_match:
            location = ", ".join(item for item in [best_match.get("city"), best_match.get("state")] if item)
            return f"I found {best_match['company_name']} near {location or 'your area'}. I’m confirming availability now."
        if session.location_captured_at:
            return "I have your location and I’m checking the best nearby provider now."
        return "I still need your location. Please tell me the highway or interstate, nearest exit, city, state, and a nearby truck stop or landmark."

    @staticmethod
    def _location_label(session: DispatchSession) -> str | None:
        if session.address:
            return session.address
        city_state = ", ".join(item for item in [session.city, session.state] if item)
        return city_state or None

    @staticmethod
    def _active_call_context(session: DispatchSession) -> ActiveCallContext:
        shared_location = None
        if session.lat is not None and session.lng is not None:
            shared_location = SharedLocationContext(
                lat=session.lat,
                lng=session.lng,
                accuracy=session.location_accuracy_m,
                address=session.address or None,
                city=session.city or None,
                state=session.state or infer_state_from_coordinates(session.lat, session.lng),
            )
        return ActiveCallContext(
            caller_phone=session.caller_phone_encrypted,
            session_id=session.id,
            location_confirmed=bool((session.metadata_json or {}).get("location_confirmed")),
            shared_location=shared_location,
            instruction="Before doing anything else, confirm this shared location with the caller.",
        )

    @staticmethod
    def _active_call_context_say(context: ActiveCallContext) -> str:
        location = context.shared_location
        if not location:
            return "I cannot see your shared location yet. Please tell me your city, state, and nearest major road or highway."
        if not (location.address or location.city):
            return "I received your shared GPS, but I could not translate it into a city and state. What city and state are you in, and what nearest major road or highway are you by?"
        parts = [location.address, location.city, location.state]
        label = ", ".join(part for part in parts if part)
        return f"I see your shared location near {label}. Is that where you need roadside help?"
