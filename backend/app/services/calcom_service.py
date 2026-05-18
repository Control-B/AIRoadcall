"""Thin Cal.com (OSS + SaaS) API client used by the Retell Shop Receptionist.

Per-shop credentials live on ``ShopProfile``:
  - ``calcom_api_key``             — required to enable real-time slots + bookings
  - ``calcom_event_type_id``       — the event type the AI books into
  - ``calcom_base_url``            — optional self-hosted base, defaults to https://api.cal.com
  - ``calcom_default_timezone``    — optional IANA tz used when caller's tz is unknown

If credentials are missing the caller-facing flow falls back to the
``calcom_calendar_url`` (booking link the agent can text via SMS).

Cal.com v2 API reference: https://cal.com/docs/api-reference/v2
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger("calcom")

DEFAULT_BASE_URL = "https://api.cal.com"
DEFAULT_TIMEZONE = "America/New_York"
API_VERSION_HEADER = "cal-api-version"
SLOTS_API_VERSION = "2024-09-04"
BOOKINGS_API_VERSION = "2024-08-13"


class CalComError(RuntimeError):
    """Raised when Cal.com returns a non-2xx or the response shape is unexpected."""


class CalComService:
    """Minimal wrapper around Cal.com v2 slots + bookings endpoints."""

    def __init__(
        self,
        *,
        api_key: str,
        event_type_id: str,
        base_url: str | None = None,
        default_timezone: str | None = None,
        timeout: float = 8.0,
    ) -> None:
        if not api_key:
            raise CalComError("calcom_api_key is required")
        if not event_type_id:
            raise CalComError("calcom_event_type_id is required")
        self.api_key = api_key.strip()
        self.event_type_id = str(event_type_id).strip()
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.default_timezone = default_timezone or DEFAULT_TIMEZONE
        self.timeout = timeout

    # ── HTTP helper ─────────────────────────────────────────────────────────

    def _headers(self, api_version: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            API_VERSION_HEADER: api_version,
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        api_version: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=self._headers(api_version),
                )
            except httpx.HTTPError as exc:
                raise CalComError(f"Cal.com request failed: {exc}") from exc
        if resp.status_code >= 400:
            raise CalComError(f"Cal.com {method} {path} -> {resp.status_code}: {resp.text[:300]}")
        try:
            return resp.json()
        except ValueError as exc:
            raise CalComError("Cal.com returned non-JSON response") from exc

    # ── Slots ───────────────────────────────────────────────────────────────

    async def get_available_slots(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        timezone_name: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, str]]:
        """Return up to ``limit`` upcoming open slots as
        ``[{"start": iso, "iso": iso, "human": "Tue May 19, 9:00 AM"}, ...]``.

        The Cal.com v2 slots response groups slots by date::

            {"data": {"slots": {"2026-05-19": [{"start": "2026-05-19T13:00:00.000Z"}, ...]}}}
        """
        tz = timezone_name or self.default_timezone
        now = datetime.now(timezone.utc)
        start_dt = start or now
        end_dt = end or (start_dt + timedelta(days=7))
        params = {
            "eventTypeId": self.event_type_id,
            "startTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "timeZone": tz,
        }
        data = await self._request("GET", "/v2/slots", api_version=SLOTS_API_VERSION, params=params)
        slots_by_day = (data.get("data") or {}).get("slots") or {}
        flat: list[dict[str, str]] = []
        for day in sorted(slots_by_day.keys()):
            for slot in slots_by_day[day] or []:
                start_iso = slot.get("start") if isinstance(slot, dict) else None
                if not start_iso:
                    continue
                flat.append({
                    "start": start_iso,
                    "iso": start_iso,
                    "human": _humanize_slot(start_iso, tz),
                })
                if len(flat) >= limit:
                    return flat
        return flat

    # ── Bookings ────────────────────────────────────────────────────────────

    async def create_booking(
        self,
        *,
        start_iso: str,
        attendee_name: str,
        attendee_phone: str,
        attendee_email: str | None = None,
        timezone_name: str | None = None,
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a Cal.com booking for the given slot.

        Returns the parsed Cal.com booking object (contains booking_uid, status, etc).
        """
        tz = timezone_name or self.default_timezone
        # Cal.com requires an email; synthesize a placeholder from the phone if missing
        # so phone-only callers can still be booked through the AI.
        email = attendee_email or _synth_email_from_phone(attendee_phone)
        body = {
            "eventTypeId": _coerce_int(self.event_type_id),
            "start": start_iso,
            "attendee": {
                "name": attendee_name,
                "email": email,
                "timeZone": tz,
                "phoneNumber": attendee_phone,
                "language": "en",
            },
            "metadata": {
                "source": "retell_shop_receptionist",
                **(metadata or {}),
            },
        }
        if notes:
            body["bookingFieldsResponses"] = {"notes": notes}
        return await self._request(
            "POST",
            "/v2/bookings",
            api_version=BOOKINGS_API_VERSION,
            json_body=body,
        )


# ── helpers ─────────────────────────────────────────────────────────────────

def _humanize_slot(iso: str, tz: str) -> str:
    """Best-effort 'Tue May 19, 9:00 AM ET' style label. Pure best-effort —
    Retell will read whatever we return, so we keep it short and unambiguous."""
    try:
        # Cal.com returns UTC ISO. We display in the shop tz with a short label.
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        try:
            from zoneinfo import ZoneInfo

            local = dt.astimezone(ZoneInfo(tz))
        except Exception:
            local = dt
        return local.strftime("%a %b %d, %-I:%M %p")
    except Exception:
        return iso


def _synth_email_from_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"phone-{digits or 'unknown'}@callers.roadcall.ai"


def _coerce_int(value: str | int) -> int | str:
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


def service_from_profile(profile: Any) -> CalComService | None:
    """Construct a CalComService from a ShopProfile-like object, or None when
    the shop has not connected Cal.com yet."""
    api_key = getattr(profile, "calcom_api_key", None)
    event_type_id = getattr(profile, "calcom_event_type_id", None)
    if not api_key or not event_type_id:
        return None
    try:
        return CalComService(
            api_key=api_key,
            event_type_id=event_type_id,
            base_url=getattr(profile, "calcom_base_url", None) or None,
            default_timezone=getattr(profile, "calcom_default_timezone", None) or None,
        )
    except CalComError as exc:
        logger.warning("calcom service construction failed: %s", exc)
        return None
