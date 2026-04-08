import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.mechanic import (
    MechanicCreateRequest,
    MechanicView,
    MechanicLocationUpdate,
)
from app.services.mechanic_data_service import MechanicDataService

router = APIRouter(prefix="/mechanics", tags=["mechanics"])


@router.post("", response_model=MechanicView, status_code=status.HTTP_201_CREATED)
async def create_or_update_mechanic(
    request: MechanicCreateRequest,
    db: AsyncSession = Depends(get_session),
):
    """Create or update a mechanic record. Upserts by phone number."""
    return await MechanicDataService.upsert_mechanic(db, request)


@router.post("/{mechanic_id}/location")
async def update_mechanic_location(
    mechanic_id: uuid.UUID,
    request: MechanicLocationUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Save mechanic live GPS location for tracking."""
    try:
        await MechanicDataService.update_mechanic_location(
            db, str(mechanic_id), request.lat, request.lng
        )
        return {"success": True}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
