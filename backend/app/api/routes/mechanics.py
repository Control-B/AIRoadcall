import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_admin_api_key
from app.api.routes.admin_auth import verify_admin
from app.schemas.mechanic import (
    MechanicCreateRequest,
    MechanicRecommendationRequest,
    MechanicRecommendationResponse,
    MechanicSearchResult,
    ShopLookupRequest,
    ShopLookupResponse,
    MechanicView,
    MechanicLocationUpdate,
    MechanicAdminListResponse,
    MechanicAdminStats,
)
from app.services.mechanic_data_service import MechanicDataService

router = APIRouter(prefix="/mechanics", tags=["mechanics"])


@router.get(
    "/admin/stats",
    response_model=MechanicAdminStats,
    dependencies=[Depends(verify_admin)],
)
async def get_mechanic_admin_stats(
    db: AsyncSession = Depends(get_session),
):
    """Get mechanic database stats for the admin viewer."""
    return await MechanicDataService.get_admin_stats(db)


@router.get(
    "/admin/list",
    response_model=MechanicAdminListResponse,
    dependencies=[Depends(verify_admin)],
)
async def list_mechanics_admin(
    q: str | None = Query(default=None),
    city: str | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    source: str | None = Query(default=None),
    service_type: str | None = Query(default=None),
    has_email: bool | None = Query(default=None),
    has_website: bool | None = Query(default=None),
    roadside_only: bool = Query(default=False),
    emergency_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    """List mechanic records for the admin viewer with pagination and filters."""
    return await MechanicDataService.list_admin_mechanics(
        db,
        q=q,
        city=city,
        state=state,
        source=source,
        service_type=service_type,
        has_email=has_email,
        has_website=has_website,
        roadside_only=roadside_only,
        emergency_only=emergency_only,
        limit=limit,
        offset=offset,
    )


@router.get(
    "",
    response_model=list[MechanicSearchResult],
    dependencies=[Depends(require_admin_api_key)],
)
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
    """Find mechanics by exact GPS or city/state for internal dispatch/admin tools."""
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


@router.post(
    "/recommendations",
    response_model=MechanicRecommendationResponse,
    dependencies=[Depends(require_admin_api_key)],
)
async def recommend_mechanics(
    request: MechanicRecommendationRequest,
    db: AsyncSession = Depends(get_session),
):
    """Rank nearby mechanics for dispatch using fit, reliability, and response speed."""
    if request.lat is None and request.lng is None and not (request.city and request.state):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either lat/lng or city/state",
        )

    return await MechanicDataService.recommend_mechanics(db, request)


@router.post(
    "/shop-lookup",
    response_model=ShopLookupResponse,
    dependencies=[Depends(require_admin_api_key)],
)
async def lookup_nearest_shops(
    request: ShopLookupRequest,
    db: AsyncSession = Depends(get_session),
):
    """Find the nearest matching shop or chain for direct caller requests."""
    if request.lat is None and request.lng is None and not (request.city and request.state):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either lat/lng or city/state",
        )

    return await MechanicDataService.lookup_nearest_shops(
        db,
        query=request.query,
        lat=request.lat,
        lng=request.lng,
        city=request.city,
        state=request.state,
        limit=request.limit,
    )


@router.post(
    "",
    response_model=MechanicView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_api_key)],
)
async def create_or_update_mechanic(
    request: MechanicCreateRequest,
    db: AsyncSession = Depends(get_session),
):
    """Create or update a mechanic record. Upserts by phone number."""
    return await MechanicDataService.upsert_mechanic(db, request)


@router.post(
    "/{mechanic_id}/location",
    dependencies=[Depends(require_admin_api_key)],
)
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
