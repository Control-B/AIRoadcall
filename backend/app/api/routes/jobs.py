from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, validate_magic_token
from app.models.job import Job
from app.schemas.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobDriverView,
    LocationUpdateRequest,
    LocationUpdateResponse,
)
from app.services.job_service import JobService
from app.services.sms_service import SMSService
from app.core.config import get_settings

router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()


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
    await SMSService.send_magic_link(
        phone_number=request.driver_phone,
        magic_link_url=result.magic_link_url,
        driver_name=request.driver_name,
    )

    return result


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
