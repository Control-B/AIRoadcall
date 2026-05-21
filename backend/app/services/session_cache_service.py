from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.models.dispatch_session import DispatchSession


class SessionCacheService:
    """Optional Redis mirror for active Roadcall dispatch sessions.

    Postgres remains the durable source of truth. Redis is used when REDIS_URL is
    configured to give active call/session code lookups a short TTL and easy
    cleanup semantics.
    """

    @staticmethod
    def _client():
        redis_url = get_settings().REDIS_URL.strip()
        if not redis_url:
            return None
        try:
            from redis.asyncio import Redis
        except Exception:
            return None
        return Redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def _payload(session: DispatchSession) -> dict[str, Any]:
        expires_minutes = get_settings().ROADCALL_SESSION_CODE_TTL_MINUTES
        expires_at = session.created_at.replace(tzinfo=timezone.utc) if session.created_at.tzinfo is None else session.created_at
        expires_at = expires_at.timestamp() + expires_minutes * 60
        return {
            "callSid": session.retell_call_id or session.twilio_call_sid,
            "sessionCode": session.public_code,
            "phoneNumber": session.caller_phone_encrypted,
            "status": session.status,
            "gps": None if session.lat is None or session.lng is None else {
                "latitude": session.lat,
                "longitude": session.lng,
                "accuracy": session.location_accuracy_m,
            },
            "mechanicMatches": [],
            "createdAt": session.created_at.isoformat() if session.created_at else None,
            "expiresAt": datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
        }

    @classmethod
    async def mirror_session(cls, session: DispatchSession, *, ttl_seconds: int | None = None) -> None:
        client = cls._client()
        if client is None:
            return
        ttl = ttl_seconds or get_settings().ROADCALL_SESSION_CODE_TTL_MINUTES * 60
        key = f"roadcall:session:{session.public_code}"
        try:
            await client.set(key, json.dumps(cls._payload(session), default=str), ex=ttl)
        finally:
            await client.aclose()

    @classmethod
    async def delete_session(cls, public_code: str) -> None:
        client = cls._client()
        if client is None:
            return
        try:
            await client.delete(f"roadcall:session:{public_code}")
        finally:
            await client.aclose()
