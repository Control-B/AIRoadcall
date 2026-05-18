from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
import os
import smtplib
from email.message import EmailMessage

router = APIRouter(prefix="/support", tags=["support"])

SUPPORT_EMAIL = os.environ.get("SUPPORT_EMAIL", "support@roadcall.ai")

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

    # Send email (using local SMTP relay or configure as needed)
    try:
        with smtplib.SMTP("localhost") as smtp:
            smtp.send_message(msg)
        return {"ok": True}
    except Exception as e:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"ok": False, "error": str(e)})
