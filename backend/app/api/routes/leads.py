"""Lead capture — website email sign-ups from lead magnet forms."""
from __future__ import annotations

import os
import urllib.request
import urllib.error
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header, Query
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.lead_capture import LeadCapture

router = APIRouter(prefix="/leads", tags=["leads"])
settings = get_settings()


def _require_admin(x_admin_key: str = Header(...)):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


class LeadIn(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    vertical: Optional[str] = None  # "shops" | "fleet" | "general"
    source: Optional[str] = None

    @field_validator("vertical")
    @classmethod
    def check_vertical(cls, v):
        if v and v not in ("shops", "fleet", "general"):
            return "general"
        return v


class LeadOut(BaseModel):
    id: str
    email: str
    already_subscribed: bool = False


@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
async def capture_lead(
    payload: LeadIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Capture an email lead from a website form."""
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)

    # Check for existing email
    result = await db.execute(select(LeadCapture).where(LeadCapture.email == payload.email.lower()))
    existing = result.scalar_one_or_none()
    if existing:
        return LeadOut(id=str(existing.id), email=existing.email, already_subscribed=True)

    lead = LeadCapture(
        email=payload.email.lower(),
        name=payload.name,
        company=payload.company,
        vertical=payload.vertical or "general",
        source=payload.source,
        ip_address=str(ip)[:45] if ip else None,
    )
    db.add(lead)
    try:
        await db.commit()
        await db.refresh(lead)
    except IntegrityError:
        await db.rollback()
        # Race condition — still return 201 gracefully
        result2 = await db.execute(select(LeadCapture).where(LeadCapture.email == payload.email.lower()))
        existing2 = result2.scalar_one_or_none()
        if existing2:
            return LeadOut(id=str(existing2.id), email=existing2.email, already_subscribed=True)
        raise HTTPException(status_code=500, detail="Could not save lead")

    # Fire welcome email via Resend (best-effort, non-blocking)
    _send_welcome_email(lead)

    return LeadOut(id=str(lead.id), email=lead.email)


def _send_welcome_email(lead: LeadCapture) -> None:
    """Send a welcome email via Resend (fire-and-forget, no await)."""
    api_key = os.getenv("RESEND_API_KEY", "")
    from_email = os.getenv("RESEND_FROM_EMAIL", "hello@roadcall.ai")
    if not api_key or api_key.startswith("re_xxx"):
        return

    vertical_line = ""
    if lead.vertical == "shops":
        vertical_line = "We'll send you tips on AI phone agents, call recovery, and booking automation for truck repair shops."
    elif lead.vertical == "fleet":
        vertical_line = "We'll send you insights on reducing driver downtime, faster dispatch, and AI-driven roadside operations."
    else:
        vertical_line = "We'll keep you posted on AI tools for the trucking industry — no noise, just signal."

    name_greeting = f"Hi {lead.name.split()[0]}," if lead.name else "Hey there,"

    html = f"""
<div style="font-family:sans-serif;max-width:560px;margin:0 auto;color:#1e293b">
  <div style="background:#02050c;padding:24px 32px;border-radius:12px 12px 0 0">
    <span style="color:#f97316;font-weight:900;font-size:20px;letter-spacing:-0.5px">Roadcall</span>
  </div>
  <div style="padding:32px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px">
    <p style="font-size:17px;font-weight:600;margin:0 0 12px">{name_greeting}</p>
    <p style="margin:0 0 16px;color:#475569;line-height:1.6">
      You're on the list. {vertical_line}
    </p>
    <p style="margin:0 0 24px;color:#475569;line-height:1.6">
      In the meantime, you can try our AI demo — call <strong style="color:#1e293b">(866) 613-3303</strong> 
      and tell Sandy you have a breakdown. See exactly how it works.
    </p>
    <a href="https://roadcall.ai" 
       style="display:inline-block;background:#f97316;color:#fff;font-weight:700;padding:12px 24px;border-radius:8px;text-decoration:none;font-size:14px">
      Explore Roadcall →
    </a>
    <p style="margin:24px 0 0;font-size:12px;color:#94a3b8">
      You're receiving this because you signed up at roadcall.ai. 
      <a href="https://roadcall.ai/unsubscribe?email={lead.email}" style="color:#94a3b8">Unsubscribe</a>
    </p>
  </div>
</div>
"""

    payload = {
        "from": f"Roadcall <{from_email}>",
        "to": [lead.email],
        "subject": "You're on the list — here's what's next",
        "html": html,
    }
    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass  # Non-fatal


# ── Admin endpoints ────────────────────────────────────────────────────────────

class LeadListItem(BaseModel):
    id: str
    email: str
    name: Optional[str]
    company: Optional[str]
    vertical: Optional[str]
    source: Optional[str]
    unsubscribed: bool
    welcome_sent: bool
    created_at: str

    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    leads: list[LeadListItem]


@router.get("", response_model=LeadListResponse, dependencies=[Depends(_require_admin)])
async def list_leads(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    vertical: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Admin: list all captured leads."""
    q = select(LeadCapture)
    if vertical:
        q = q.where(LeadCapture.vertical == vertical)
    if search:
        q = q.where(LeadCapture.email.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(q.subquery())
    total_result = await db.execute(count_q)
    total = total_result.scalar_one()

    q = q.order_by(LeadCapture.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    rows = result.scalars().all()

    return LeadListResponse(
        total=total,
        page=page,
        page_size=page_size,
        leads=[
            LeadListItem(
                id=str(r.id),
                email=r.email,
                name=r.name,
                company=r.company,
                vertical=r.vertical,
                source=r.source,
                unsubscribed=r.unsubscribed,
                welcome_sent=r.welcome_sent,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ],
    )


@router.delete("/{lead_id}", dependencies=[Depends(_require_admin)], status_code=204)
async def delete_lead(lead_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LeadCapture).where(LeadCapture.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(lead)
    await db.commit()
