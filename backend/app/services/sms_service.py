"""SMS delivery service for sending magic links to drivers."""
import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SMSService:
    """SMS delivery — Telnyx primary, Twilio fallback."""

    @staticmethod
    def _send_via_telnyx(phone_number: str, body: str) -> bool:
        try:
            import httpx
            resp = httpx.post(
                "https://api.telnyx.com/v2/messages",
                headers={"Authorization": f"Bearer {settings.TELNYX_API_KEY}"},
                json={"from": settings.TELNYX_FROM_NUMBER, "to": phone_number, "text": body},
                timeout=10,
            )
            resp.raise_for_status()
            msg_id = resp.json().get("data", {}).get("id", "?")
            logger.info(f"Telnyx SMS sent to {phone_number}: id={msg_id}")
            return True
        except Exception as e:
            logger.error(f"Telnyx SMS failed to {phone_number}: {e}")
            return False

    @staticmethod
    def _send_via_twilio(phone_number: str, body: str) -> bool:
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            params = dict(body=body, to=phone_number)
            if settings.TWILIO_MESSAGING_SERVICE_SID:
                params["messaging_service_sid"] = settings.TWILIO_MESSAGING_SERVICE_SID
            else:
                params["from_"] = settings.TWILIO_FROM_NUMBER
            message = client.messages.create(**params)
            logger.info(f"Twilio SMS sent to {phone_number}: SID={message.sid}")
            return True
        except Exception as e:
            logger.error(f"Twilio SMS failed to {phone_number}: {e}")
            return False

    @staticmethod
    def _send_sync(phone_number: str, body: str) -> bool:
        """Try Telnyx first, fall back to Twilio."""
        if settings.TELNYX_API_KEY:
            return SMSService._send_via_telnyx(phone_number, body)
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN \
                and not settings.TWILIO_ACCOUNT_SID.startswith("AC_placeholder"):
            return SMSService._send_via_twilio(phone_number, body)
        logger.info(f"[DEV] SMS to {phone_number}: {body}")
        return True

    @staticmethod
    async def send_magic_link(
        phone_number: str, magic_link_url: str, driver_name: str
    ) -> bool:
        """Send the GPS magic link to the driver via SMS."""
        if not phone_number:
            logger.warning("Cannot send SMS — no phone number provided")
            return False
        body = (
            f"Hi {driver_name}, tap this link to share your location and "
            f"we'll dispatch the nearest mechanic:\n{magic_link_url}"
        )
        return await asyncio.to_thread(SMSService._send_sync, phone_number, body)

    @staticmethod
    async def send_sms(phone_number: str, body: str) -> bool:
        """Send a generic SMS (outreach, dispatch notifications, etc.)."""
        if not phone_number:
            return False
        return await asyncio.to_thread(SMSService._send_sync, phone_number, body)
