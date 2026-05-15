import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_session,
    require_admin_api_key,
    get_mechanic_dispatch_offer_context,
)
from app.models.job import Job
from app.models.dispatch_attempt import DispatchAttempt
from app.schemas.dispatch import (
    DispatchStartResponse,
    DispatchNextResponse,
    MechanicResponseRequest,
    MechanicResponseResponse,
    MechanicOfferView,
    MechanicOfferStatusView,
    MechanicOfferRespondRequest,
)
from app.schemas.location_dispatch import (
    DispatchCoordinates,
    DispatchMapRoute,
    DispatchMatchByLocationRequest,
    DispatchMatchByLocationResponse,
    DispatchProviderMatch,
)
from app.services.geocoding_service import GeocodingService
from app.services.location_matching_service import LocationMatchingService, ProviderCandidate
from app.schemas.tracking import MechanicTrackingView
from app.services.dispatch_service import DispatchService
from app.services.tracking_service import TrackingService
from app.core.config import get_settings
from sqlalchemy import select

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


async def require_dispatch_match_access(
    authorization: str | None = Header(default=None),
    x_admin_key: str | None = Header(default=None),
) -> None:
    settings = get_settings()
    admin_key = settings.ADMIN_API_KEY.strip()
    if admin_key and x_admin_key and x_admin_key.strip() == admin_key:
        return

    retell_token = settings.RETELL_BACKEND_WEBHOOK_TOKEN.strip()
    if retell_token and authorization and authorization.strip() == f"Bearer {retell_token}":
        return

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to match providers")


def _provider_to_response(provider: ProviderCandidate) -> DispatchProviderMatch:
    return DispatchProviderMatch(
        id=provider.id,
        business_name=provider.business_name,
        phone=provider.phone,
        email=provider.email,
        address=provider.address,
        city=provider.city,
        state=provider.state,
        zip_code=provider.zip_code,
        latitude=provider.latitude,
        longitude=provider.longitude,
        services=provider.services,
        heavy_duty_support=provider.heavy_duty_support,
        roadside_support=provider.roadside_support,
        mobile_mechanic=provider.mobile_mechanic,
        towing=provider.towing,
        availability_status=provider.availability_status,
        rating=provider.rating,
        response_score=provider.response_score,
        distance_miles=provider.drive_distance_miles or provider.straight_line_distance,
        straight_line_distance=provider.straight_line_distance,
        drive_distance_miles=provider.drive_distance_miles,
        estimated_drive_minutes=provider.estimated_drive_minutes,
        rank_score=provider.rank_score,
        score_reasons=provider.score_reasons,
    )


def _provider_route(latitude: float, longitude: float, provider: ProviderCandidate) -> DispatchMapRoute:
    return DispatchMapRoute(
        provider_id=provider.id,
        from_latitude=latitude,
        from_longitude=longitude,
        to_latitude=provider.latitude,
        to_longitude=provider.longitude,
        drive_distance_miles=provider.drive_distance_miles,
        estimated_drive_minutes=provider.estimated_drive_minutes,
        geometry={
            "type": "LineString",
            "coordinates": [[longitude, latitude], [provider.longitude, provider.latitude]],
        },
    )


def _normalize_mechanic_offer_response(raw: str) -> str:
    lower = raw.lower().strip()
    if lower in ("accepted", "declined"):
        return lower
    if lower in ("yes", "accept", "ok", "sure"):
        return "accepted"
    if lower in ("no", "decline", "pass", "cant", "can't"):
        return "declined"
    raise ValueError("response must be accepted or declined")


@router.post(
    "/match-by-location",
    response_model=DispatchMatchByLocationResponse,
    dependencies=[Depends(require_dispatch_match_access)],
)
async def match_by_location(
    request: DispatchMatchByLocationRequest,
    db: AsyncSession = Depends(get_session),
):
    """Geocode caller location and rank providers by actual proximity.

    The AI agent must call this endpoint before naming any provider. Results are
    backend-verified and sorted by geospatial proximity/travel-time ranking.
    """
    geocoded = await GeocodingService.geocode_location(request.location_text)
    if not geocoded:
        return DispatchMatchByLocationResponse(
            status="geocoding_failed",
            message="I could not confidently locate that place. Ask for city/state, nearest highway, exit, mile marker, truck stop, or landmark.",
            follow_up_question="What city and state, highway exit, mile marker, or nearby truck stop are you closest to?",
        )

    latitude = float(geocoded["latitude"])
    longitude = float(geocoded["longitude"])
    providers, radius = await LocationMatchingService.find_nearby_providers(
        db,
        latitude=latitude,
        longitude=longitude,
        service_needed=request.service_needed,
        vehicle_type=request.vehicle_type,
        urgency=request.urgency,
        limit=request.limit,
    )

    if not providers:
        return DispatchMatchByLocationResponse(
            status="no_provider_found",
            normalized_location=geocoded["normalized_location"],
            coordinates=DispatchCoordinates(latitude=latitude, longitude=longitude),
            confidence=geocoded.get("confidence"),
            search_radius_miles=150,
            providers=[],
            message="No provider found within 150 miles. Offer manual escalation and ask whether to broaden the search.",
            follow_up_question="I’m not finding a verified nearby provider. Do you want me to escalate this for manual dispatch or broaden the search?",
            mapbox_metadata=geocoded.get("mapbox_metadata"),
        )

    return DispatchMatchByLocationResponse(
        status="matched",
        normalized_location=geocoded["normalized_location"],
        coordinates=DispatchCoordinates(latitude=latitude, longitude=longitude),
        confidence=geocoded.get("confidence"),
        search_radius_miles=radius,
        providers=[_provider_to_response(provider) for provider in providers],
        map_routes=[_provider_route(latitude, longitude, provider) for provider in providers[:3]],
        message=f"Found {len(providers)} provider option(s) within {radius} miles of {geocoded['normalized_location']}.",
        mapbox_metadata=geocoded.get("mapbox_metadata"),
    )


@router.get("/mechanic-offer/{token}", response_model=MechanicOfferView)
async def get_mechanic_offer(
    token: str,
    db: AsyncSession = Depends(get_session),
    ctx: tuple[Job, DispatchAttempt] = Depends(get_mechanic_dispatch_offer_context),
):
    job, attempt = ctx
    return await DispatchService.build_mechanic_offer_view(db, job, attempt)


@router.get("/mechanic-offer/{token}/status", response_model=MechanicOfferStatusView)
async def poll_mechanic_offer_status(
    token: str,
    db: AsyncSession = Depends(get_session),
    ctx: tuple[Job, DispatchAttempt] = Depends(get_mechanic_dispatch_offer_context),
):
    job, attempt = ctx
    await db.refresh(job)
    await db.refresh(attempt)
    return await DispatchService.mechanic_offer_status(db, job, attempt)


@router.post("/mechanic-offer/{token}/respond", response_model=MechanicResponseResponse)
async def respond_mechanic_offer(
    token: str,
    request: MechanicOfferRespondRequest,
    db: AsyncSession = Depends(get_session),
    ctx: tuple[Job, DispatchAttempt] = Depends(get_mechanic_dispatch_offer_context),
):
    job, attempt = ctx
    await db.refresh(job)
    await db.refresh(attempt)
    try:
        normalized = _normalize_mechanic_offer_response(request.response)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    try:
        return await DispatchService.record_mechanic_response(
            db=db,
            job_id=job.id,
            attempt_id=attempt.id,
            response=normalized,
            eta_minutes=request.eta_minutes,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/{job_id}/start", response_model=DispatchStartResponse)
async def start_dispatch(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Begin mechanic matching and dispatch workflow.

    Only allowed if payment is authorized. Called by backend orchestration
    after payment confirmation.
    """
    try:
        return await DispatchService.start_dispatch(db, job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{job_id}/start-sms")
async def start_sms_dispatch(
    job_id: uuid.UUID,
    body: dict | None = None,
    db: AsyncSession = Depends(get_session),
):
    """SMS-dispatch top-ranked mechanics for a job without requiring payment.

    Called by the AI agent after the driver's GPS location is confirmed.
    Skips payment gate — finds nearby mechanics and texts each one an
    accept/decline link immediately.
    """
    from app.enums.job_status import JobStatus

    count = (body or {}).get("count", 3)

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update status to matching
    if job.status not in (
        JobStatus.matching_mechanics,
        JobStatus.calling_mechanics,
    ):
        job.status = JobStatus.matching_mechanics
        await db.flush()

    # Dispatch batch (ranks mechanics, creates attempts, sends SMS)
    batch = await DispatchService.dispatch_mechanics_batch(db, job_id, count)

    mechanics_info = []
    for item in batch:
        mechanics_info.append({
            "company_name": item.mechanic_company,
            "phone": item.mechanic_phone,
            "dispatch_attempt_id": item.dispatch_attempt_id,
        })

    return {
        "dispatched_count": len(batch),
        "mechanics": mechanics_info,
        "job_status": job.status,
    }


@router.post("/{job_id}/next", response_model=DispatchNextResponse)
async def dispatch_next_mechanic(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Select and queue the next best-ranked mechanic for dispatch."""
    try:
        result = await DispatchService.dispatch_next_mechanic(db, job_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No more available mechanics for this job",
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{job_id}/mechanic-response", response_model=MechanicResponseResponse)
async def record_mechanic_response(
    job_id: uuid.UUID,
    request: MechanicResponseRequest,
    db: AsyncSession = Depends(get_session),
):
    """Record a mechanic's response to a dispatch attempt."""
    try:
        return await DispatchService.record_mechanic_response(
            db=db,
            job_id=job_id,
            attempt_id=uuid.UUID(request.dispatch_attempt_id),
            response=request.response,
            eta_minutes=request.eta_minutes,
            notes=request.notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{job_id}/mechanic-tracking", response_model=MechanicTrackingView, dependencies=[Depends(require_admin_api_key)])
async def get_mechanic_tracking(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await TrackingService.get_mechanic_tracking_view(db, job)
