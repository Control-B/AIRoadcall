import httpx
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

router = APIRouter(prefix="/support", tags=["support"])

SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@roadcall.ai")
SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))
settings = get_settings()

class SupportForm(BaseModel):
    role: str
    data: dict

@router.post("/submit-setup-form")
async def submit_setup_form(payload: SupportForm):
    # Compose email
    subject = f"New {payload.role} setup submission"
    body = "\n".join([f"{k}: {v}" for k, v in payload.data.items()])
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SUPPORT_EMAIL
    msg["To"] = SUPPORT_EMAIL
    msg.set_content(body)

    if settings.RESEND_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                    json={
                        "from": settings.RESEND_FROM_EMAIL,
                        "to": [SUPPORT_EMAIL],
                        "subject": subject,
                        "text": body,
                    },
                )
            if response.status_code < 400:
                return {"ok": True, "channel": "resend"}
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"ok": False, "error": f"Resend rejected support email ({response.status_code})"},
            )
        except Exception as exc:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"ok": False, "error": f"Resend support email failed: {exc}"},
            )

    # SMTP fallback for local relays or production SMTP sidecars.
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
            smtp.send_message(msg)
        return {"ok": True, "channel": "smtp"}
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"ok": False, "error": str(e)})
