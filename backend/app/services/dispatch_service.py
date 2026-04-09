import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import Job
from app.models.mechanic import Mechanic
from app.models.dispatch_attempt import DispatchAttempt
from app.models.tracking_session import TrackingSession
from app.schemas.dispatch import (
    DispatchStartResponse,
    DispatchNextResponse,
    MechanicResponseResponse,
)
from app.enums.job_status import JobStatus
from app.enums.payment_status import PaymentStatus
from app.enums.dispatch_status import DispatchStatus
from app.enums.tracking_status import TrackingStatus
from app.services.mechanic_scoring_service import MechanicScoringService
from app.services.audit_service import AuditService
from app.core.logging import get_logger

logger = get_logger(__name__)


class DispatchService:

    @staticmethod
    async def start_dispatch(
        db: AsyncSession, job_id: uuid.UUID
    ) -> DispatchStartResponse:
        """Begin mechanic matching. Only allowed if payment is authorized."""
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job:
            raise ValueError("Job not found")

        if job.payment_status not in (PaymentStatus.authorized, PaymentStatus.captured):
            raise ValueError("Payment must be authorized before dispatch")

        if job.status not in (
            JobStatus.payment_authorized,
            JobStatus.matching_mechanics,
            JobStatus.calling_mechanics,
        ):
            raise ValueError(f"Cannot start dispatch from status: {job.status}")

        job.status = JobStatus.matching_mechanics

        await AuditService.log(
            db,
            job_id=job.id,
            event_type="dispatch.started",
            actor_type="system",
            payload={"job_status": job.status},
        )
        await db.flush()

        logger.info(f"Dispatch started for job {job.public_job_id}")

        return DispatchStartResponse(
            success=True,
            job_status=job.status,
            message="Mechanic matching started",
        )

    @staticmethod
    async def dispatch_next_mechanic(
        db: AsyncSession, job_id: uuid.UUID
    ) -> DispatchNextResponse | None:
        """Select the next best mechanic and create a dispatch attempt."""
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError("Job not found")

        if not job.driver_lat or not job.driver_lng:
            raise ValueError("Driver location not available")

        # Get already-attempted mechanic IDs
        attempted_result = await db.execute(
            select(DispatchAttempt.mechanic_id).where(
                DispatchAttempt.job_id == job_id,
                DispatchAttempt.dispatch_status.notin_([
                    DispatchStatus.superseded,
                ]),
            )
        )
        attempted_ids = {row[0] for row in attempted_result.all()}

        # Get all active mechanics
        mechanics_result = await db.execute(
            select(Mechanic).where(
                Mechanic.active == True,
                Mechanic.id.notin_(attempted_ids) if attempted_ids else True,
            )
        )
        mechanics = list(mechanics_result.scalars().all())

        if not mechanics:
            logger.warning(f"No more mechanics available for job {job.public_job_id}")
            return None

        # Score and rank
        ranked = MechanicScoringService.rank_mechanics(
            mechanics=mechanics,
            driver_lat=job.driver_lat,
            driver_lng=job.driver_lng,
            issue_type=job.issue_type,
            vehicle_type=job.vehicle_type,
        )

        if not ranked:
            return None

        best_mechanic, best_score = ranked[0]

        # Create dispatch attempt
        attempt = DispatchAttempt(
            job_id=job_id,
            mechanic_id=best_mechanic.id,
            rank_score=best_score,
            dispatch_status=DispatchStatus.queued,
        )
        db.add(attempt)

        job.status = JobStatus.calling_mechanics
        await db.flush()

        await AuditService.log(
            db,
            job_id=job.id,
            event_type="dispatch.attempt_created",
            actor_type="system",
            payload={
                "mechanic_id": str(best_mechanic.id),
                "company": best_mechanic.company_name,
                "rank_score": best_score,
            },
        )

        logger.info(
            f"Dispatch attempt for job {job.public_job_id}: "
            f"{best_mechanic.company_name} (score: {best_score:.2f})"
        )

        return DispatchNextResponse(
            dispatch_attempt_id=str(attempt.id),
            mechanic_company=best_mechanic.company_name,
            mechanic_contact=best_mechanic.contact_name or "",
            mechanic_phone=best_mechanic.phone or "",
            rank_score=best_score,
            dispatch_status=attempt.dispatch_status,
        )

    @staticmethod
    async def record_mechanic_response(
        db: AsyncSession,
        job_id: uuid.UUID,
        attempt_id: uuid.UUID,
        response: str,
        eta_minutes: int | None = None,
        notes: str | None = None,
    ) -> MechanicResponseResponse:
        """Record a mechanic's response and assign if accepted."""
        result = await db.execute(
            select(DispatchAttempt).where(DispatchAttempt.id == attempt_id)
        )
        attempt = result.scalar_one_or_none()
        if not attempt:
            raise ValueError("Dispatch attempt not found")

        job_result = await db.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            raise ValueError("Job not found")

        now = datetime.now(timezone.utc)
        attempt.responded_at = now
        attempt.response_notes = notes

        if response == "accepted":
            attempt.dispatch_status = DispatchStatus.accepted
            attempt.availability_eta_minutes = eta_minutes
            job.assigned_mechanic_id = attempt.mechanic_id
            job.status = JobStatus.mechanic_assigned

            # Create tracking session
            tracking = TrackingSession(
                job_id=job_id,
                mechanic_id=attempt.mechanic_id,
                tracking_status=TrackingStatus.pending,
            )
            db.add(tracking)

            # Supersede other pending attempts
            other_attempts = await db.execute(
                select(DispatchAttempt).where(
                    DispatchAttempt.job_id == job_id,
                    DispatchAttempt.id != attempt_id,
                    DispatchAttempt.dispatch_status.in_([
                        DispatchStatus.queued,
                        DispatchStatus.calling,
                    ]),
                )
            )
            for other in other_attempts.scalars().all():
                other.dispatch_status = DispatchStatus.superseded

            await AuditService.log(
                db,
                job_id=job.id,
                event_type="mechanic.assigned",
                actor_type="mechanic",
                actor_id=str(attempt.mechanic_id),
                payload={
                    "eta_minutes": eta_minutes,
                },
            )

            logger.info(f"Mechanic assigned to job {job.public_job_id}")

        elif response == "declined":
            attempt.dispatch_status = DispatchStatus.declined
        elif response == "unavailable":
            attempt.dispatch_status = DispatchStatus.unavailable
        elif response == "no_answer":
            attempt.dispatch_status = DispatchStatus.no_answer
        elif response == "timed_out":
            attempt.dispatch_status = DispatchStatus.timed_out
        else:
            attempt.dispatch_status = DispatchStatus.declined

        await AuditService.log(
            db,
            job_id=job.id,
            event_type=f"dispatch.mechanic_{response}",
            actor_type="mechanic",
            actor_id=str(attempt.mechanic_id),
            payload={"notes": notes},
        )

        await db.flush()

        return MechanicResponseResponse(
            success=True,
            dispatch_status=attempt.dispatch_status,
            job_status=job.status,
            assigned_mechanic_id=(
                str(job.assigned_mechanic_id) if job.assigned_mechanic_id else None
            ),
        )
