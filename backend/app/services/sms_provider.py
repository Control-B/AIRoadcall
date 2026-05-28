"""
SMS Provider abstraction layer.

Roadcall Shops uses GHL/LC Phone for CRM-integrated messaging.
Roadcall Fleet uses Twilio (or Telnyx fallback) for direct dispatch SMS.
A Console provider is available for local development / testing.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class SmsProviderType(str, Enum):
    twilio = "twilio"
    telnyx = "telnyx"
    ghl = "ghl"          # GoHighLevel / LC Phone (Shops vertical)
    console = "console"  # Dev/test — prints to stdout


@dataclass
class SmsResult:
    success: bool
    provider: SmsProviderType
    message_id: Optional[str] = None
    error: Optional[str] = None


MOBILE_LINE_TYPES = {"mobile"}


def _lookup_sms_capable_number(
    account_sid: str,
    auth_token: str,
    phone_number: str,
) -> tuple[bool, str | None]:
    if not account_sid or not auth_token:
        return True, None

    try:
        import httpx

        url = f"https://lookups.twilio.com/v2/PhoneNumbers/{quote(phone_number, safe='')}"
        resp = httpx.get(
            url,
            params={"Fields": "line_type_intelligence"},
            auth=(account_sid, auth_token),
            timeout=10,
        )
        if resp.status_code == 404:
            return False, "Twilio Lookup rejected phone number"
        resp.raise_for_status()
        data = resp.json()
        line_type = (data.get("line_type_intelligence") or {}).get("type")
        if not line_type:
            return False, "Twilio Lookup did not return a line type"
        if str(line_type).lower() not in MOBILE_LINE_TYPES:
            return False, f"Phone number is not SMS-safe mobile line type: {line_type}"
        return True, None
    except Exception as exc:
        logger.error("Twilio Lookup preflight failed for %s: %s", phone_number, exc)
        return False, f"Twilio Lookup preflight failed: {exc}"


def _contact_has_sms_dnd(contact: dict) -> bool:
    if contact.get("dnd") is True:
        return True

    settings = contact.get("dndSettings") or contact.get("dnd_settings") or {}
    sms_settings = settings.get("SMS") or settings.get("sms") or {}
    if isinstance(sms_settings, dict):
        status = str(sms_settings.get("status") or "").lower()
        if status in {"active", "opted_out", "opt_out", "dnd", "blocked"}:
            return True

    for key in ("optOut", "opt_out", "smsOptOut", "sms_opt_out"):
        if contact.get(key) is True:
            return True
    return False


class SMSProvider(abc.ABC):
    """Abstract base class for SMS providers."""

    @abc.abstractmethod
    def send(self, to: str, body: str, from_number: Optional[str] = None) -> SmsResult:
        ...

    @property
    @abc.abstractmethod
    def provider_type(self) -> SmsProviderType:
        ...


# ---------------------------------------------------------------------------
# Console provider (no-op for local dev)
# ---------------------------------------------------------------------------

class ConsoleSmsProvider(SMSProvider):
    @property
    def provider_type(self) -> SmsProviderType:
        return SmsProviderType.console

    def send(self, to: str, body: str, from_number: Optional[str] = None) -> SmsResult:
        logger.info("[ConsoleSMS] TO=%s | FROM=%s | BODY=%s", to, from_number or "N/A", body)
        print(f"[SMS] → {to}: {body}")
        return SmsResult(success=True, provider=SmsProviderType.console, message_id="console-noop")


# ---------------------------------------------------------------------------
# Twilio provider
# ---------------------------------------------------------------------------

class TwilioSmsProvider(SMSProvider):
    def __init__(self, account_sid: str, auth_token: str, default_from: str):
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._default_from = default_from

    @property
    def provider_type(self) -> SmsProviderType:
        return SmsProviderType.twilio

    def send(self, to: str, body: str, from_number: Optional[str] = None) -> SmsResult:
        try:
            sms_capable, lookup_error = _lookup_sms_capable_number(
                self._account_sid,
                self._auth_token,
                to,
            )
            if not sms_capable:
                return SmsResult(success=False, provider=SmsProviderType.twilio, error=lookup_error)

            from twilio.rest import Client  # type: ignore
            client = Client(self._account_sid, self._auth_token)
            msg = client.messages.create(
                to=to,
                from_=from_number or self._default_from,
                body=body,
            )
            logger.info("TwilioSMS sent: sid=%s status=%s", msg.sid, msg.status)
            return SmsResult(success=True, provider=SmsProviderType.twilio, message_id=msg.sid)
        except Exception as exc:
            logger.error("TwilioSMS error: %s", exc)
            return SmsResult(success=False, provider=SmsProviderType.twilio, error=str(exc))


# ---------------------------------------------------------------------------
# Telnyx provider
# ---------------------------------------------------------------------------

class TelnyxSmsProvider(SMSProvider):
    def __init__(self, api_key: str, default_from: str):
        self._api_key = api_key
        self._default_from = default_from

    @property
    def provider_type(self) -> SmsProviderType:
        return SmsProviderType.telnyx

    def send(self, to: str, body: str, from_number: Optional[str] = None) -> SmsResult:
        try:
            import telnyx  # type: ignore
            telnyx.api_key = self._api_key
            msg = telnyx.Message.create(
                from_=from_number or self._default_from,
                to=to,
                text=body,
            )
            msg_id = getattr(msg, "id", None) or getattr(getattr(msg, "data", None), "id", None)
            logger.info("TelnyxSMS sent: id=%s", msg_id)
            return SmsResult(success=True, provider=SmsProviderType.telnyx, message_id=str(msg_id))
        except Exception as exc:
            logger.error("TelnyxSMS error: %s", exc)
            return SmsResult(success=False, provider=SmsProviderType.telnyx, error=str(exc))


# ---------------------------------------------------------------------------
# GHL / LC Phone provider (Shops vertical)
# ---------------------------------------------------------------------------

class GhlSmsProvider(SMSProvider):
    """
    Sends SMS via GoHighLevel (LC Phone) API.
    Used by Roadcall Shops — messages appear inside the GHL CRM conversation thread.
    Docs: https://highlevel.stoplight.io/docs/integrations/b3A6MjY1MDI5Mg-create-sms-message
    """

    def __init__(
        self,
        api_key: str,
        location_id: str,
        default_from: Optional[str] = None,
        twilio_account_sid: Optional[str] = None,
        twilio_auth_token: Optional[str] = None,
    ):
        self._api_key = api_key
        self._location_id = location_id
        self._default_from = default_from
        self._twilio_account_sid = twilio_account_sid or ""
        self._twilio_auth_token = twilio_auth_token or ""

    @property
    def provider_type(self) -> SmsProviderType:
        return SmsProviderType.ghl

    def _find_ghl_contact_by_phone(self, phone_number: str) -> dict | None:
        import httpx

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Version": "2021-04-15",
        }
        resp = httpx.get(
            "https://services.leadconnectorhq.com/contacts/",
            params={"locationId": self._location_id, "query": phone_number},
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        contacts = data.get("contacts") or data.get("contact") or []
        if isinstance(contacts, dict):
            contacts = [contacts]
        normalized_phone = "".join(ch for ch in phone_number if ch.isdigit())
        for contact in contacts:
            contact_phone = str(contact.get("phone") or contact.get("contactPhone") or "")
            normalized_contact_phone = "".join(ch for ch in contact_phone if ch.isdigit())
            if normalized_contact_phone and normalized_contact_phone == normalized_phone:
                return contact
        return contacts[0] if contacts else None

    def send(self, to: str, body: str, from_number: Optional[str] = None) -> SmsResult:
        try:
            import httpx
            sms_capable, lookup_error = _lookup_sms_capable_number(
                self._twilio_account_sid,
                self._twilio_auth_token,
                to,
            )
            if not sms_capable:
                return SmsResult(success=False, provider=SmsProviderType.ghl, error=lookup_error)

            contact = self._find_ghl_contact_by_phone(to)
            if contact and _contact_has_sms_dnd(contact):
                contact_id = contact.get("id") or contact.get("contactId") or "unknown"
                return SmsResult(
                    success=False,
                    provider=SmsProviderType.ghl,
                    error=f"GHL contact has SMS DND enabled: {contact_id}",
                )

            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Version": "2021-04-15",
            }
            payload = {
                "type": "SMS",
                "message": body,
                "contactPhone": to,
                "locationId": self._location_id,
            }
            if from_number or self._default_from:
                payload["fromNumber"] = from_number or self._default_from

            resp = httpx.post(
                "https://services.leadconnectorhq.com/conversations/messages",
                json=payload,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("messageId") or data.get("id")
            logger.info("GhlSMS sent: id=%s", msg_id)
            return SmsResult(success=True, provider=SmsProviderType.ghl, message_id=str(msg_id))
        except Exception as exc:
            logger.error("GhlSMS error: %s", exc)
            return SmsResult(success=False, provider=SmsProviderType.ghl, error=str(exc))


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_sms_provider(vertical: str = "fleet") -> SMSProvider:
    """
    Return the appropriate SMS provider for the given vertical.
    - 'shops'  → GHL/LC Phone (falls back to Twilio if GHL not configured)
    - 'fleet'  → Twilio (falls back to Telnyx, then Console)
    """
    from app.core.config import get_settings
    cfg = get_settings()

    if (
        vertical == "shops"
        and getattr(cfg, "GHL_API_KEY", None)
        and getattr(cfg, "GHL_LOCATION_ID", None)
    ):
        return GhlSmsProvider(
            api_key=cfg.GHL_API_KEY,
            location_id=cfg.GHL_LOCATION_ID,
            default_from=getattr(cfg, "GHL_FROM_NUMBER", None),
            twilio_account_sid=getattr(cfg, "TWILIO_ACCOUNT_SID", None),
            twilio_auth_token=getattr(cfg, "TWILIO_AUTH_TOKEN", None),
        )

    # Fleet (or Shops fallback) — Twilio primary
    if getattr(cfg, "TWILIO_ACCOUNT_SID", None) and getattr(cfg, "TWILIO_AUTH_TOKEN", None):
        return TwilioSmsProvider(
            account_sid=cfg.TWILIO_ACCOUNT_SID,
            auth_token=cfg.TWILIO_AUTH_TOKEN,
            default_from=cfg.TWILIO_FROM_NUMBER,
        )

    # Telnyx fallback
    if getattr(cfg, "TELNYX_API_KEY", None) and getattr(cfg, "TELNYX_FROM_NUMBER", None):
        return TelnyxSmsProvider(
            api_key=cfg.TELNYX_API_KEY,
            default_from=cfg.TELNYX_FROM_NUMBER,
        )

    # Last resort: Console (dev / missing config)
    logger.warning("No SMS provider configured — falling back to ConsoleSmsProvider")
    return ConsoleSmsProvider()
