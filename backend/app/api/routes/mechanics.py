import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
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
    MarketplaceSearchResponse,
)
from app.services.mechanic_data_service import MechanicDataService

router = APIRouter(prefix="/mechanics", tags=["mechanics"])


async def ensure_mechanic_admin_columns(db: AsyncSession) -> None:
    """Self-heal admin columns that older production DBs may not have yet."""
    statements = [
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS website TEXT",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS address TEXT",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS city VARCHAR(120)",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS state VARCHAR(10)",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS rating NUMERIC(3, 2)",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS review_count INTEGER",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS source VARCHAR(50)",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS source_confidence DOUBLE PRECISION",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS last_enriched_at TIMESTAMPTZ",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS enrichment_data JSONB",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS lead_status VARCHAR(50) DEFAULT 'new'",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS emergency_service BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS service_radius_miles INTEGER NOT NULL DEFAULT 50",
        "ALTER TABLE mechanics ADD COLUMN IF NOT EXISTS priority_score INTEGER NOT NULL DEFAULT 50",
    ]
    for statement in statements:
        await db.execute(text(statement))


@router.get(
    "/admin/stats",
    response_model=MechanicAdminStats,
    dependencies=[Depends(verify_admin)],
)
async def get_mechanic_admin_stats(
    db: AsyncSession = Depends(get_session),
):
    """Get mechanic database stats for the admin viewer."""
    await ensure_mechanic_admin_columns(db)
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
    sort_by: str | None = Query(default=None, description="company_name, city, state, rating, created_at, last_enriched_at"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    """List mechanic records for the admin viewer with pagination and filters."""
    await ensure_mechanic_admin_columns(db)
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
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/search",
)
async def public_search_mechanics(
    q: str | None = Query(default=None, description="Company name, city, or keyword"),
    city: str | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    service_type: str | None = Query(default=None),
    is_24_7: bool | None = Query(default=None),
    mobile_only: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    """Public directory search — returns basic provider info safe for public display."""
    await ensure_mechanic_admin_columns(db)
    result = await MechanicDataService.list_admin_mechanics(
        db,
        q=q,
        city=city,
        state=state,
        service_type=service_type,
        has_email=None,
        has_website=None,
        roadside_only=mobile_only or False,
        emergency_only=is_24_7 or False,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    # Strip sensitive fields — only return public-safe data
    safe_mechanics = []
    for m in result.items:
        safe_mechanics.append({
            "id": m.id,
            "company_name": m.company_name,
            "city": m.city,
            "state": m.state,
            "rating": m.rating,
            "review_count": m.review_count,
            "accepts_mobile_roadside": m.accepts_mobile_roadside,
            "emergency_service": m.emergency_service,
            "is_emergency_24_7": getattr(m, "is_emergency_24_7", False),
            "service_types": m.service_types,
            "priority_score": m.priority_score,
        })
    return {
        "mechanics": safe_mechanics,
        "total": result.total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/marketplace",
    response_model=MarketplaceSearchResponse,
)
async def search_marketplace_providers(
    q: str | None = Query(default=None, description="Business/service keyword search"),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    city: str | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    issue_type: str = Query(default="", description="flat_tire, tow_needed, dead_battery, engine_trouble, etc."),
    vehicle_type: str | None = Query(default=None, description="car, truck, heavy_duty, rv, trailer, fleet"),
    radius_miles: int | None = Query(default=75, ge=5, le=250),
    roadside_only: bool = Query(default=True),
    emergency_only: bool = Query(default=False),
    limit: int = Query(default=12, ge=1, le=25),
    db: AsyncSession = Depends(get_session),
):
    """Public operational marketplace search.

    Returns ranked, non-sensitive provider cards with deterministic dispatch fit,
    trust, roadside relevance, response confidence, and score breakdowns.
    """
    if lat is None and lng is None and not (city and state):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either lat/lng or city/state",
        )
    return await MechanicDataService.marketplace_search(
        db,
        q=q,
        lat=lat,
        lng=lng,
        city=city,
        state=state,
        issue_type=issue_type,
        vehicle_type=vehicle_type,
        radius_miles=radius_miles,
        roadside_only=roadside_only,
        emergency_only=emergency_only,
        limit=limit,
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
