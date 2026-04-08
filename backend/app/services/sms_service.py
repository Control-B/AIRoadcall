"""SMS delivery service for sending magic links to drivers."""
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SMSService:
    """Stub for Twilio/SMS provider integration."""

    @staticmethod
    async def send_magic_link(
        phone_number: str, magic_link_url: str, driver_name: str
    ) -> bool:
        """Send an SMS with the magic link to the driver.

        TODO: Implement with Twilio SDK when credentials are configured.
        """
        logger.info(
            f"[STUB] Would send SMS to {phone_number}: "
            f"Hi {driver_name}, here is your roadside support link: {magic_link_url}"
        )

        # Production implementation:
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     body=(
        #         f"Hi {driver_name}, your AI Roadside Support link is ready: "
        #         f"{magic_link_url}"
        #     ),
        #     from_=settings.TWILIO_FROM_NUMBER,
        #     to=phone_number,
        # )
        # return message.sid is not None

        return True
