"""Pre-call shared caller location cache.

When a website visitor taps "Share my location" before phoning Sandy, we store
their normalized phone -> {lat, lng, address...} in Redis with a short TTL so
the Retell agent can attach the location automatically on the inbound call.

This replaces the legacy roadcall.ai/go short-code dance: the caller no longer
has to enter a code while on the line — the website already linked their phone
number to their GPS.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings

_DIGITS = re.compile(r"\D")
_DEFAULT_TTL_SECONDS = 30 * 60
_KEY_PREFIX = "caller_shared_location:"


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = _DIGITS.sub("", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) >= 10:
        return f"+{digits}"
    return None


class SharedCallerLocationService:
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
    def _key(phone_e164: str) -> str:
        return f"{_KEY_PREFIX}{phone_e164}"

    @classmethod
    async def store(
        cls,
        *,
        phone: str,
        session_id: str | None = None,
        latitude: float,
        longitude: float,
        accuracy: float | None,
        address: str | None,
        city: str | None,
        state: str | None,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> dict[str, Any] | None:
        phone_e164 = normalize_phone(phone)
        if not phone_e164:
            return None
        payload = {
            "phone": phone_e164,
            "session_id": session_id,
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
            "address": address,
            "city": city,
            "state": state,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": ttl_seconds,
        }
        client = cls._client()
        if client is None:
            return payload
        try:
            await client.set(cls._key(phone_e164), json.dumps(payload), ex=ttl_seconds)
        finally:
            await client.aclose()
        return payload

    @classmethod
    async def lookup(cls, phone: str | None) -> dict[str, Any] | None:
        phone_e164 = normalize_phone(phone)
        if not phone_e164:
            return None
        client = cls._client()
        if client is None:
            return None
        try:
            raw = await client.get(cls._key(phone_e164))
        finally:
            await client.aclose()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    @classmethod
    async def consume(cls, phone: str | None) -> dict[str, Any] | None:
        """Lookup and delete in one shot — used once the agent has attached the location."""
        phone_e164 = normalize_phone(phone)
        if not phone_e164:
            return None
        client = cls._client()
        if client is None:
            return None
        try:
            raw = await client.get(cls._key(phone_e164))
            if raw:
                await client.delete(cls._key(phone_e164))
        finally:
            await client.aclose()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None
