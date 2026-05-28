"""SMS delivery service for sending magic links to drivers."""
import asyncio
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class SMSService:
    """SMS delivery — Telnyx primary, Twilio fallback."""

    BRAND_NAME = "Roadcall.ai"
    COMPLIANCE_FOOTER = "Reply STOP to opt out, HELP for help."

    @staticmethod
    def _with_compliance_footer(body: str) -> str:
        text = (body or "").strip()
        if not text:
            return text

        lower = text.lower()
        has_stop = "stop" in lower
        has_help = "help" in lower
        if has_stop and has_help:
            return text

        if text.endswith("."):
            return f"{text} {SMSService.COMPLIANCE_FOOTER}"
        return f"{text}. {SMSService.COMPLIANCE_FOOTER}"

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
        """Try Twilio toll-free first, fall back to Telnyx."""
        # Re-read settings at call time (avoids stale cached values at module import)
        cfg = get_settings()
        twilio_sid = cfg.TWILIO_ACCOUNT_SID or ""
        twilio_tok = cfg.TWILIO_AUTH_TOKEN or ""
        telnyx_key = cfg.TELNYX_API_KEY or ""
        telnyx_from = cfg.TELNYX_FROM_NUMBER or ""
        logger.info(
            f"[SMS] provider check — twilio_sid={twilio_sid[:6] if twilio_sid else 'EMPTY'}"
            f" telnyx_key={'SET' if telnyx_key else 'EMPTY'} telnyx_from={telnyx_from!r}"
        )
        if twilio_sid and twilio_tok and not twilio_sid.startswith("AC_placeholder"):
            from app.services.sms_provider import _lookup_sms_capable_number

            sms_capable, lookup_error = _lookup_sms_capable_number(
                twilio_sid,
                twilio_tok,
                phone_number,
            )
            if not sms_capable:
                logger.warning("[SMS] Twilio Lookup blocked %s: %s", phone_number, lookup_error)
                return False

            ok = SMSService._send_via_twilio(phone_number, body)
            if ok:
                return True
        if telnyx_key and telnyx_from:
            ok = SMSService._send_via_telnyx(phone_number, body)
            if ok:
                return True
        logger.warning(f"[SMS] All providers failed for {phone_number} — no fallback available")
        return False

    @staticmethod
    async def send_magic_link(
        phone_number: str, magic_link_url: str, driver_name: str
    ) -> bool:
        """Send the GPS magic link to the driver via SMS."""
        if not phone_number:
            logger.warning("Cannot send SMS — no phone number provided")
            return False
        body = SMSService._with_compliance_footer(
            (
                f"{SMSService.BRAND_NAME}: Hi {driver_name}, tap this secure link to "
                "share your location "
                f"so we can dispatch the nearest mechanic: {magic_link_url}"
            )
        )
        return await asyncio.to_thread(SMSService._send_sync, phone_number, body)

    @staticmethod
    async def send_sms(phone_number: str, body: str) -> bool:
        """Send a generic SMS (outreach, dispatch notifications, etc.)."""
        if not phone_number:
            return False
        safe_body = SMSService._with_compliance_footer(body)
        return await asyncio.to_thread(SMSService._send_sync, phone_number, safe_body)

    @staticmethod
    def _start_twilio_studio_execution_sync(
        to_number: str,
        flow_sid: str,
        parameters: dict[str, Any],
        status_callback: str | None = None,
    ) -> str | None:
        try:
            from twilio.rest import Client

            cfg = get_settings()
            client = Client(cfg.TWILIO_ACCOUNT_SID, cfg.TWILIO_AUTH_TOKEN)
            payload: dict[str, Any] = {
                "to": to_number,
                "from_": cfg.TWILIO_FROM_NUMBER,
                "parameters": parameters,
            }
            if cfg.TWILIO_MESSAGING_SERVICE_SID:
                payload.pop("from_", None)
                payload["messaging_service_sid"] = cfg.TWILIO_MESSAGING_SERVICE_SID
            if status_callback:
                payload["status_callback"] = status_callback

            execution = client.studio.v2.flows(flow_sid).executions.create(**payload)
            logger.info(
                "Twilio Studio execution started to %s: flow=%s execution=%s",
                to_number,
                flow_sid,
                execution.sid,
            )
            return execution.sid
        except Exception as e:
            logger.error(f"Twilio Studio execution failed to {to_number}: {e}")
            return None

    @staticmethod
    async def start_twilio_studio_execution(
        to_number: str,
        parameters: dict[str, Any],
        flow_sid: str | None = None,
        status_callback: str | None = None,
    ) -> str | None:
        if not to_number:
            return None

        cfg = get_settings()
        selected_flow_sid = (flow_sid or cfg.TWILIO_STUDIO_FLOW_SID or "").strip()
        if not selected_flow_sid:
            logger.warning("Twilio Studio flow SID missing; skipping Studio execution")
            return None

        return await asyncio.to_thread(
            SMSService._start_twilio_studio_execution_sync,
            to_number,
            selected_flow_sid,
            parameters,
            status_callback or cfg.TWILIO_STUDIO_STATUS_CALLBACK or None,
        )
