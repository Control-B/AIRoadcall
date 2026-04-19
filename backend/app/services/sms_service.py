"""SMS delivery service for sending magic links to drivers."""
import asyncio

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SMSService:
    """Twilio SMS service for magic-link delivery."""

    @staticmethod
    def _send_via_twilio(phone_number: str, body: str) -> bool:
        try:
            from twilio.rest import Client

            client = Client(
                settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
            )
            # Prefer Messaging Service SID (A2P 10DLC) over direct from_ number
            params = dict(body=body, to=phone_number)
            if settings.TWILIO_MESSAGING_SERVICE_SID:
                params["messaging_service_sid"] = settings.TWILIO_MESSAGING_SERVICE_SID
            else:
                params["from_"] = settings.TWILIO_FROM_NUMBER
            message = client.messages.create(**params)
            logger.info(f"SMS sent to {phone_number}: SID={message.sid}")
            return True
        except Exception as e:
            logger.error(f"Twilio SMS failed to {phone_number}: {e}")
            return False

    @staticmethod
    async def send_magic_link(
        phone_number: str, magic_link_url: str, driver_name: str
    ) -> bool:
        """Send an SMS with the magic link to the driver.

        Uses Twilio when configured, otherwise logs (dev/test fallback).
        """
        if not phone_number:
            logger.warning("Cannot send SMS — no phone number provided")
            return False

        body = (
            f"Hi {driver_name}, your Roadside Assist link is ready — "
            f"tap to share your location and we'll send help your way:\n"
            f"{magic_link_url}"
        )

        # ── Twilio (production) ──
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN \
                and not settings.TWILIO_ACCOUNT_SID.startswith("AC_placeholder"):
            return await asyncio.to_thread(
                SMSService._send_via_twilio,
                phone_number,
                body,
            )

        # ── Dev fallback ──
        logger.info(
            f"[DEV] SMS to {phone_number}: {body}"
        )
        return True

    @staticmethod
    async def send_sms(phone_number: str, body: str) -> bool:
        """Send a generic SMS (used by outreach, dispatch notifications, etc.)."""
        if not phone_number:
            return False

        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN \
                and not settings.TWILIO_ACCOUNT_SID.startswith("AC_placeholder"):
            return await asyncio.to_thread(
                SMSService._send_via_twilio,
                phone_number,
                body,
            )

        logger.info(f"[DEV] SMS to {phone_number}: {body}")
        return True
