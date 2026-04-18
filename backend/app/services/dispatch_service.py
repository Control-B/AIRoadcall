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
from app.services.sms_service import SMSService
from app.core.config import get_settings
from app.core.security import create_mechanic_tracking_token
from app.core.logging import get_logger
from app.utils.location import normalize_state

logger = get_logger(__name__)
settings = get_settings()


class DispatchService:

    @staticmethod
    async def launch_outbound_call(
        db: AsyncSession,
        job: Job,
        next_attempt: DispatchNextResponse,
    ) -> None:
        attempt_id = uuid.UUID(next_attempt.dispatch_attempt_id)
        attempt_result = await db.execute(
            select(DispatchAttempt).where(DispatchAttempt.id == attempt_id)
        )
        attempt = attempt_result.scalar_one_or_none()
        if not attempt:
            raise ValueError("Dispatch attempt not found")

        if attempt.dispatch_status == DispatchStatus.queued:
            attempt.dispatch_status = DispatchStatus.calling
            if not attempt.called_at:
                attempt.called_at = datetime.now(timezone.utc)
            await db.flush()
        elif attempt.dispatch_status != DispatchStatus.calling:
            logger.info(
                "Dispatch attempt %s not launchable (%s)",
                attempt_id,
                attempt.dispatch_status,
            )
            return

        from app.services.livekit_service import LiveKitService

        job_summary = (
            f"{job.issue_type}: {job.issue_summary or ''} — {job.vehicle_type or 'vehicle'}"
        )
        call_result = await LiveKitService.initiate_mechanic_call(
            mechanic_phone=next_attempt.mechanic_phone,
            mechanic_name=next_attempt.mechanic_company,
            job_summary=job_summary,
            job_id=str(job.id),
            dispatch_attempt_id=next_attempt.dispatch_attempt_id,
        )

        if call_result.get("status") == "error":
            logger.error(
                "LiveKit call launch failed for attempt %s: %s",
                attempt_id,
                call_result.get("error", "unknown error"),
            )
            await DispatchService.record_mechanic_response(
                db=db,
                job_id=job.id,
                attempt_id=attempt_id,
                response="timed_out",
                notes=f"LiveKit call launch failed: {call_result.get('error', 'unknown error')}",
            )

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

        has_precise_location = job.driver_lat is not None and job.driver_lng is not None
        has_city_location = bool(job.driver_city and job.driver_state)
        if not has_precise_location and not has_city_location:
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

        mechanic_query = select(Mechanic).where(Mechanic.active == True)
        if attempted_ids:
            mechanic_query = mechanic_query.where(Mechanic.id.notin_(attempted_ids))

        fallback_query = mechanic_query
        if job.driver_state and normalize_state(job.driver_state):
            mechanic_query = mechanic_query.where(Mechanic.state == normalize_state(job.driver_state))

        ranking_state = normalize_state(job.driver_state) if job.driver_state else None
        mechanics_result = await db.execute(mechanic_query)
        mechanics = list(mechanics_result.scalars().all())

        if not mechanics and job.driver_state:
            mechanics_result = await db.execute(fallback_query)
            mechanics = list(mechanics_result.scalars().all())
            ranking_state = None

        if not mechanics:
            logger.warning(f"No more mechanics available for job {job.public_job_id}")
            return None

        if has_precise_location:
            ranked = MechanicScoringService.rank_mechanics(
                mechanics=mechanics,
                driver_lat=job.driver_lat,
                driver_lng=job.driver_lng,
                issue_type=job.issue_type,
                vehicle_type=job.vehicle_type,
            )
        else:
            ranked = MechanicScoringService.rank_mechanics_by_city(
                mechanics=mechanics,
                driver_city=job.driver_city or "",
                driver_state=ranking_state or "",
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

        if attempt.dispatch_status not in (DispatchStatus.queued, DispatchStatus.calling):
            logger.info(
                f"Dispatch attempt {attempt_id} already finalized ({attempt.dispatch_status}), "
                "skipping duplicate record"
            )
            return MechanicResponseResponse(
                success=True,
                dispatch_status=attempt.dispatch_status,
                job_status=job.status,
                assigned_mechanic_id=(
                    str(job.assigned_mechanic_id) if job.assigned_mechanic_id else None
                ),
            )

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

            mechanic_result = await db.execute(
                select(Mechanic).where(Mechanic.id == attempt.mechanic_id)
            )
            mechanic = mechanic_result.scalar_one_or_none()
            if mechanic and mechanic.phone:
                tracking_token = create_mechanic_tracking_token(
                    str(job.id),
                    job.public_job_id,
                    str(attempt.mechanic_id),
                )
                tracking_url = f"{settings.APP_BASE_URL}/mechanic-track/{tracking_token}"
                driver_location_hint = ", ".join(
                    part for part in [job.driver_city, job.driver_state] if part
                )
                issue_summary = job.issue_summary or job.issue_type
                sms_body = (
                    f"Roadcall dispatch {job.public_job_id} is confirmed. "
                    f"Driver: {job.driver_name}. "
                    f"Issue: {issue_summary}. "
                    f"Open the live map for driver location, route, and ETA:\n"
                    f"{tracking_url}"
                )
                if driver_location_hint:
                    sms_body = (
                        f"Roadcall dispatch {job.public_job_id} is confirmed. "
                        f"Driver area: {driver_location_hint}. "
                        f"Issue: {issue_summary}. "
                        f"Open the live map for driver location, route, and ETA:\n"
                        f"{tracking_url}"
                    )
                sent = await SMSService.send_sms(mechanic.phone, sms_body)
                if not sent:
                    logger.warning(
                        "Failed to send mechanic tracking SMS for job %s",
                        job.public_job_id,
                    )

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

        # Offer the next mechanic (outbound SIP + AI) when this one could not take the job
        if response in ("declined", "unavailable", "no_answer", "timed_out"):
            next_attempt = await DispatchService.dispatch_next_mechanic(db, job_id)
            if next_attempt:
                await DispatchService.launch_outbound_call(db, job, next_attempt)

        return MechanicResponseResponse(
            success=True,
            dispatch_status=attempt.dispatch_status,
            job_status=job.status,
            assigned_mechanic_id=(
                str(job.assigned_mechanic_id) if job.assigned_mechanic_id else None
            ),
        )
