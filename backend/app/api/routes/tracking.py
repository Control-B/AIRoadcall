from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, validate_magic_token
from app.schemas.tracking import TrackingView
from app.services.tracking_service import TrackingService

router = APIRouter(prefix="/jobs", tags=["tracking"])


@router.get("/{token}/tracking", response_model=TrackingView)
async def get_tracking(
    token: str,
    db: AsyncSession = Depends(get_session),
):
    """Return tracking payload for the driver-facing live tracking UI."""
    job = await validate_magic_token(token, db)
    return await TrackingService.get_tracking_view(db, job)
