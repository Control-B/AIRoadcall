"""Outreach & Campaign API routes."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.outreach_service import OutreachService
from app.schemas.outreach import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    SegmentFilters,
    SegmentPreview,
    MechanicLeadUpdate,
    OutreachDashboardStats,
)

from app.api.routes.admin_auth import verify_admin

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/outreach", tags=["outreach"])


# ── Dashboard ────────────────────────────────────────────

@router.get("/dashboard", response_model=OutreachDashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Get overall outreach dashboard statistics."""
    stats = await OutreachService.get_dashboard_stats(db)
    return stats


# ── Campaigns ────────────────────────────────────────────

@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """List all campaigns."""
    return await OutreachService.list_campaigns(db, limit=limit, offset=offset)


@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Create a new outreach campaign."""
    return await OutreachService.create_campaign(db, data)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Get a campaign by ID."""
    campaign = await OutreachService.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Update a campaign."""
    campaign = await OutreachService.update_campaign(db, campaign_id, data)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Delete a campaign."""
    deleted = await OutreachService.delete_campaign(db, campaign_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"success": True}


# ── Segmentation ─────────────────────────────────────────

@router.post("/segment/preview", response_model=SegmentPreview)
async def preview_segment(
    filters: SegmentFilters,
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Preview how many mechanics match the given filters."""
    result = await OutreachService.preview_segment(
        db, filters.model_dump(exclude_none=True)
    )
    return result


# ── Send / Process ───────────────────────────────────────

@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Start sending a campaign — queues messages for all targeted mechanics."""
    result = await OutreachService.send_campaign(db, campaign_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/campaigns/{campaign_id}/process")
async def process_campaign_messages(
    campaign_id: uuid.UUID,
    batch_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Process a batch of pending messages — actually send SMS/email."""
    result = await OutreachService.process_pending_messages(
        db, campaign_id, batch_size=batch_size
    )
    return result


# ── Campaign Stats ───────────────────────────────────────

@router.get("/campaigns/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Get detailed stats for a campaign."""
    stats = await OutreachService.get_campaign_stats(db, campaign_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return stats


# ── Lead Management ──────────────────────────────────────

@router.put("/mechanics/{mechanic_id}/lead-status")
async def update_lead_status(
    mechanic_id: uuid.UUID,
    data: MechanicLeadUpdate,
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(verify_admin),
):
    """Update a mechanic's lead status."""
    from app.models.mechanic import Mechanic
    from sqlalchemy import select

    result = await db.execute(select(Mechanic).where(Mechanic.id == mechanic_id))
    mechanic = result.scalar_one_or_none()
    if not mechanic:
        raise HTTPException(status_code=404, detail="Mechanic not found")

    mechanic.lead_status = data.lead_status
    if data.lead_notes:
        mechanic.lead_notes = data.lead_notes
    await db.commit()
    return {"success": True, "lead_status": data.lead_status}
