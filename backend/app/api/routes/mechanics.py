import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.mechanic import (
    MechanicCreateRequest,
    MechanicSearchResult,
    MechanicView,
    MechanicLocationUpdate,
)
from app.services.mechanic_data_service import MechanicDataService

router = APIRouter(prefix="/mechanics", tags=["mechanics"])


@router.get("", response_model=list[MechanicSearchResult])
async def search_mechanics(
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    city: str | None = Query(default=None),
    state: str | None = Query(default=None),
    issue_type: str = Query(default=""),
    vehicle_type: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_session),
):
    """Find mechanics by exact GPS or by caller city/state when GPS is unavailable."""
    if lat is None and lng is None and not (city and state):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either lat/lng or city/state",
        )

    return await MechanicDataService.search_mechanics(
        db,
        lat=lat,
        lng=lng,
        city=city,
        state=state,
        issue_type=issue_type,
        vehicle_type=vehicle_type,
        limit=limit,
    )


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
