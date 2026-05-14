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

    def __init__(self, api_key: str, location_id: str, default_from: Optional[str] = None):
        self._api_key = api_key
        self._location_id = location_id
        self._default_from = default_from

    @property
    def provider_type(self) -> SmsProviderType:
        return SmsProviderType.ghl

    def send(self, to: str, body: str, from_number: Optional[str] = None) -> SmsResult:
        try:
            import httpx
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

    if vertical == "shops" and getattr(cfg, "GHL_API_KEY", None) and getattr(cfg, "GHL_LOCATION_ID", None):
        return GhlSmsProvider(
            api_key=cfg.GHL_API_KEY,
            location_id=cfg.GHL_LOCATION_ID,
            default_from=getattr(cfg, "GHL_FROM_NUMBER", None),
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
