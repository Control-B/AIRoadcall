import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import (
    get_session,
    validate_magic_token,
    validate_mechanic_tracking_token,
    require_admin_api_key,
)
from app.models.job import Job
from app.schemas.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobDriverView,
    LocationUpdateRequest,
    LocationUpdateResponse,
)
from app.schemas.dispatch import (
    DriverEtaDecisionRequest,
    RematchCandidateView,
    RematchSelectRequest,
)
from app.services.job_service import JobService
from app.services.dispatch_service import DispatchService
from app.services.sms_service import SMSService
from app.services.tracking_service import TrackingService
from app.schemas.tracking import MechanicTrackingView
from app.core.config import get_settings

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()


def _send_magic_link_background(phone_number: str, magic_link_url: str, driver_name: str) -> None:
    import logging
    _logger = logging.getLogger(__name__)

    async def _runner() -> None:
        try:
            ok = await SMSService.send_magic_link(
                phone_number=phone_number,
                magic_link_url=magic_link_url,
                driver_name=driver_name,
            )
            if not ok:
                _logger.warning("Background SMS to %s returned False", phone_number)
        except Exception as exc:
            _logger.error("Background SMS to %s failed: %s", phone_number, exc)

    asyncio.create_task(_runner())


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: JobCreateRequest,
    db: AsyncSession = Depends(get_session),
):
    """Create a new roadside job after AI call intake.

    Called by the LiveKit webhook handler or internal service after the AI
    phone call with the driver is complete.
    """
    result = await JobService.create_job(db, request)

    # Send magic link SMS to driver
    _send_magic_link_background(
        phone_number=request.driver_phone,
        magic_link_url=result.magic_link_url,
        driver_name=request.driver_name,
    )

    return result


@router.get("/by-code/{public_job_id}")
async def get_job_by_code(
    public_job_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Look up a job by its public ID (e.g. RC-A1B2C3D4) and return the magic link token.

    Used by the /go/{code} frontend page so the driver can access their case
    without needing an SMS."""
    from sqlalchemy import select
    from app.models.job import Job

    code = public_job_id.upper().strip()
    result = await db.execute(select(Job).where(Job.public_job_id == code))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"magic_link_token": job.magic_link_token, "public_job_id": job.public_job_id}


@router.post("/geocode")
async def geocode_address(
    body: dict,
):
    """Forward-geocode an address via Mapbox. Used by the agent to resolve verbal addresses."""
    from app.services.geocoding_service import GeocodingService

    address = body.get("address", "")
    city = body.get("city", "")
    state = body.get("state", "")
    result = await GeocodingService.geocode_address(address, city, state)
    if not result:
        raise HTTPException(status_code=404, detail="Could not geocode address")
    return result


@router.get("/mechanic-tracking/{token}", response_model=MechanicTrackingView)
async def get_mechanic_tracking_by_token(
    token: str,
    db: AsyncSession = Depends(get_session),
):
    """Retrieve safe mechanic-facing live tracking by signed token."""
    job = await validate_mechanic_tracking_token(token, db)
    return await TrackingService.get_mechanic_tracking_view(db, job)


@router.get(
    "/admin/by-public-id/{public_job_id}",
    response_model=JobDriverView,
    dependencies=[Depends(require_admin_api_key)],
)
async def admin_get_job_by_public_id(
    public_job_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Agent/automation: load driver-safe job view by public job id (e.g. RC-XXXX)."""
    code = public_job_id.upper().strip()
    result = await db.execute(select(Job).where(Job.public_job_id == code))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return await JobService.get_job_driver_view(job, db)


@router.patch("/{token}/driver-eta", response_model=JobDriverView)
async def patch_driver_eta_decision(
    token: str,
    body: DriverEtaDecisionRequest,
    db: AsyncSession = Depends(get_session),
):
    """Driver accepts or rejects the proposed mechanic ETA."""
    job = await validate_magic_token(token, db)
    try:
        return await JobService.apply_driver_eta_decision(db, job, body.decision)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/{token}/rematch-candidates", response_model=list[RematchCandidateView])
async def list_rematch_candidates_route(
    token: str,
    db: AsyncSession = Depends(get_session),
    limit: int = 15,
):
    """Nearby mechanics excluding those already attempted for this job (after ETA rejection)."""
    job = await validate_magic_token(token, db)
    if job.driver_eta_decision != "rejected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rematch is only available after rejecting the ETA",
        )
    return await DispatchService.list_rematch_candidates(db, job, limit=limit)


@router.post("/{token}/rematch-select", response_model=JobDriverView)
async def rematch_select_route(
    token: str,
    body: RematchSelectRequest,
    db: AsyncSession = Depends(get_session),
):
    """Driver selects a specific mechanic from the rematch list."""
    job = await validate_magic_token(token, db)
    try:
        mid = uuid.UUID(body.mechanic_id)
        await DispatchService.rematch_select_mechanic(db, job, mid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    job = await validate_magic_token(token, db)
    return await JobService.get_job_driver_view(job, db)


@router.get("/{token}", response_model=JobDriverView)
async def get_job_by_token(
    token: str,
    db: AsyncSession = Depends(get_session),
):
    """Retrieve safe driver-facing job data by magic link token."""
    job = await validate_magic_token(token, db)
    return await JobService.get_job_driver_view(job, db)


@router.post("/{token}/location", response_model=LocationUpdateResponse)
async def update_driver_location(
    token: str,
    request: LocationUpdateRequest,
    db: AsyncSession = Depends(get_session),
):
    """Save driver GPS coordinates from browser geolocation."""
    job = await validate_magic_token(token, db)
    return await JobService.update_driver_location(db, job, request)


@router.get("/{token}/status", response_model=JobDriverView)
async def get_job_status(
    token: str,
    db: AsyncSession = Depends(get_session),
):
    """Return current driver-safe job status for polling."""
    job = await validate_magic_token(token, db)
    return await JobService.get_job_driver_view(job, db)
