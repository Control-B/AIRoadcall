from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import Job
from app.models.mechanic import Mechanic
from app.schemas.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobDriverView,
    AssignedMechanicSummary,
    LocationUpdateRequest,
    LocationUpdateResponse,
)
from app.enums.job_status import JobStatus
from app.enums.payment_status import PaymentStatus
from app.core.security import create_signed_token, generate_public_job_id
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.audit_service import AuditService

logger = get_logger(__name__)
settings = get_settings()


class JobService:

    @staticmethod
    async def create_job(
        db: AsyncSession, request: JobCreateRequest
    ) -> JobCreateResponse:
        """Create a new roadside job after AI call intake."""
        public_id = generate_public_job_id()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.MAGIC_LINK_EXPIRY_HOURS
        )

        # Create the job first to get the ID
        job = Job(
            public_job_id=public_id,
            magic_link_token="",  # placeholder
            magic_link_expires_at=expires_at,
            driver_name=request.driver_name,
            driver_phone=request.driver_phone,
            vehicle_type=request.vehicle_type,
            driver_city=request.driver_city,
            driver_state=request.driver_state,
            issue_type=request.issue_type,
            issue_summary=request.issue_summary,
            status=JobStatus.awaiting_driver_location,
            payment_status=PaymentStatus.not_started,
            payment_hold_amount=request.payment_hold_amount or 150.00,
        )
        db.add(job)
        await db.flush()

        # Generate signed token with job ID
        token = create_signed_token(str(job.id), public_id)
        job.magic_link_token = token
        await db.flush()

        magic_link_url = f"{settings.APP_BASE_URL}/support/{token}"

        await AuditService.log(
            db,
            job_id=job.id,
            event_type="job.created",
            actor_type="system",
            payload={"public_job_id": public_id, "issue_type": request.issue_type},
        )

        logger.info(f"Job created: {public_id}")

        return JobCreateResponse(
            public_job_id=public_id,
            magic_link_token=token,
            magic_link_url=magic_link_url,
            status=job.status,
            created_at=job.created_at,
        )

    @staticmethod
    async def get_job_driver_view(job: Job, db: AsyncSession) -> JobDriverView:
        """Build a safe driver-facing view of the job."""
        mechanic_summary = None
        if job.assigned_mechanic_id:
            result = await db.execute(
                select(Mechanic).where(Mechanic.id == job.assigned_mechanic_id)
            )
            mechanic = result.scalar_one_or_none()
            if mechanic:
                mechanic_summary = AssignedMechanicSummary(
                    company_name=mechanic.company_name,
                    contact_name=mechanic.contact_name,
                )

        return JobDriverView(
            public_job_id=job.public_job_id,
            driver_name=job.driver_name,
            vehicle_type=job.vehicle_type,
            issue_type=job.issue_type,
            issue_summary=job.issue_summary,
            driver_city=job.driver_city,
            driver_state=job.driver_state,
            status=job.status,
            payment_status=job.payment_status,
            payment_hold_amount=float(job.payment_hold_amount) if job.payment_hold_amount else None,
            driver_lat=job.driver_lat,
            driver_lng=job.driver_lng,
            driver_location_captured_at=job.driver_location_captured_at,
            assigned_mechanic=mechanic_summary,
            created_at=job.created_at,
        )

    @staticmethod
    async def update_driver_location(
        db: AsyncSession, job: Job, request: LocationUpdateRequest
    ) -> LocationUpdateResponse:
        """Save driver GPS coordinates and advance job status."""
        job.driver_lat = request.lat
        job.driver_lng = request.lng
        job.driver_location_captured_at = datetime.now(timezone.utc)

        # Advance to payment step if currently awaiting location
        if job.status == JobStatus.awaiting_driver_location:
            job.status = JobStatus.awaiting_payment_authorization
            await AuditService.log(
                db,
                job_id=job.id,
                event_type="job.status_changed",
                actor_type="driver",
                payload={
                    "from": JobStatus.awaiting_driver_location,
                    "to": JobStatus.awaiting_payment_authorization,
                },
            )

        await AuditService.log(
            db,
            job_id=job.id,
            event_type="driver.location_updated",
            actor_type="driver",
            payload={"lat": request.lat, "lng": request.lng},
        )

        await db.flush()
        logger.info(f"Location updated for job {job.public_job_id}")

        return LocationUpdateResponse(
            success=True,
            status=job.status,
            driver_lat=job.driver_lat,
            driver_lng=job.driver_lng,
        )
