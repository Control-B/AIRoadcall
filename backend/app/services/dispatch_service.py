import uuid
import math
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
    MechanicOfferView,
    MechanicOfferStatusView,
    RematchCandidateView,
)
from app.enums.job_status import JobStatus
from app.enums.payment_status import PaymentStatus
from app.enums.dispatch_status import DispatchStatus
from app.enums.tracking_status import TrackingStatus
from app.enums.driver_eta import DriverEtaDecision
from app.services.mechanic_scoring_service import MechanicScoringService
from app.services.audit_service import AuditService
from app.services.sms_service import SMSService
from app.core.config import get_settings
from app.core.security import create_mechanic_tracking_token, create_mechanic_dispatch_offer_token
from app.core.logging import get_logger
from app.utils.location import normalize_state
from app.utils.geo import haversine_distance_meters

logger = get_logger(__name__)
settings = get_settings()


class DispatchService:

    @staticmethod
    def _bounding_box(lat: float, lng: float, radius_km: float = 160.0) -> tuple[float, float, float, float]:
        lat_delta = radius_km / 111.0
        safe_cos = max(math.cos(math.radians(lat)), 0.2)
        lng_delta = radius_km / (111.0 * safe_cos)
        return lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta

    @staticmethod
    def _estimate_eta_minutes_for_mechanic(job: Job, mechanic: Mechanic) -> int | None:
        if job.driver_lat is None or job.driver_lng is None:
            return None
        mechanic_lat = mechanic.last_known_lat or mechanic.base_lat
        mechanic_lng = mechanic.last_known_lng or mechanic.base_lng
        if mechanic_lat is None or mechanic_lng is None:
            return None
        distance_miles = haversine_distance_meters(
            job.driver_lat,
            job.driver_lng,
            mechanic_lat,
            mechanic_lng,
        ) / 1609.344
        return max(5, round((distance_miles / 35.0) * 60))

    @staticmethod
    async def _get_ranked_mechanics_for_job(
        db: AsyncSession, job: Job
    ) -> list[tuple[Mechanic, float]]:
        """Return scored mechanics not yet attempted for this job (any prior attempt counts)."""
        has_precise_location = job.driver_lat is not None and job.driver_lng is not None
        has_city_location = bool(job.driver_city and job.driver_state)
        if not has_precise_location and not has_city_location:
            return []

        attempted_result = await db.execute(
            select(DispatchAttempt.mechanic_id).where(
                DispatchAttempt.job_id == job.id,
            )
        )
        attempted_ids = {row[0] for row in attempted_result.all()}

        mechanic_query = select(Mechanic).where(Mechanic.active == True)
        if attempted_ids:
            mechanic_query = mechanic_query.where(Mechanic.id.notin_(attempted_ids))

        if has_precise_location:
            min_lat, max_lat, min_lng, max_lng = DispatchService._bounding_box(
                job.driver_lat, job.driver_lng
            )
            mechanic_query = mechanic_query.where(
                Mechanic.base_lat >= min_lat,
                Mechanic.base_lat <= max_lat,
                Mechanic.base_lng >= min_lng,
                Mechanic.base_lng <= max_lng,
            )

        fallback_query = mechanic_query
        if job.driver_state and normalize_state(job.driver_state):
            mechanic_query = mechanic_query.where(
                Mechanic.state == normalize_state(job.driver_state)
            )

        ranking_state = normalize_state(job.driver_state) if job.driver_state else None
        mechanics_result = await db.execute(mechanic_query)
        mechanics = list(mechanics_result.scalars().all())

        if not mechanics and job.driver_state:
            mechanics_result = await db.execute(fallback_query)
            mechanics = list(mechanics_result.scalars().all())
            ranking_state = None

        if not mechanics:
            return []

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

        return ranked

    @staticmethod
    async def _send_dispatch_offer_sms(
        db: AsyncSession,
        job: Job,
        mechanic: Mechanic,
        attempt: DispatchAttempt,
    ) -> None:
        """Mark attempt as calling and SMS a signed web dispatch link."""
        if attempt.dispatch_status == DispatchStatus.queued:
            attempt.dispatch_status = DispatchStatus.calling
        if not attempt.called_at:
            attempt.called_at = datetime.now(timezone.utc)
        await db.flush()

        token = create_mechanic_dispatch_offer_token(
            str(job.id),
            job.public_job_id,
            str(attempt.id),
            str(mechanic.id),
        )
        url = f"{settings.public_app_base_url}/mechanic-offer/{token}"
        issue_bit = job.issue_summary or str(job.issue_type)
        body = (
            f"Roadcall {job.public_job_id} — {issue_bit}. "
            f"View work location on the map and tap Accept or Decline:\n{url}"
        )
        if mechanic.phone:
            await SMSService.send_sms(mechanic.phone, body)

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
    async def dispatch_mechanics_batch(
        db: AsyncSession,
        job_id: uuid.UUID,
        count: int,
    ) -> list[DispatchNextResponse]:
        """Create up to `count` parallel dispatch attempts and SMS each mechanic a web offer link."""
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError("Job not found")

        ranked = await DispatchService._get_ranked_mechanics_for_job(db, job)
        if not ranked:
            logger.warning("No mechanics available for batch job %s", job.public_job_id)
            return []

        n = min(count, len(ranked))
        out: list[DispatchNextResponse] = []

        for i in range(n):
            mechanic, best_score = ranked[i]
            attempt = DispatchAttempt(
                job_id=job_id,
                mechanic_id=mechanic.id,
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
                    "mechanic_id": str(mechanic.id),
                    "company": mechanic.company_name,
                    "rank_score": best_score,
                    "batch": True,
                },
            )

            await DispatchService._send_dispatch_offer_sms(db, job, mechanic, attempt)

            out.append(
                DispatchNextResponse(
                    dispatch_attempt_id=str(attempt.id),
                    mechanic_company=mechanic.company_name,
                    mechanic_contact=mechanic.contact_name or "",
                    mechanic_phone=mechanic.phone or "",
                    rank_score=best_score,
                    dispatch_status=attempt.dispatch_status,
                )
            )

            logger.info(
                "Batch dispatch attempt for job %s: %s (score: %.2f)",
                job.public_job_id,
                mechanic.company_name,
                best_score,
            )

        return out

    @staticmethod
    async def dispatch_next_mechanic(
        db: AsyncSession, job_id: uuid.UUID
    ) -> DispatchNextResponse | None:
        """Select the next best mechanic and create a single dispatch attempt (API / legacy)."""
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError("Job not found")

        ranked = await DispatchService._get_ranked_mechanics_for_job(db, job)
        if not ranked:
            logger.warning(f"No more mechanics available for job {job.public_job_id}")
            return None

        best_mechanic, best_score = ranked[0]

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

        await DispatchService._send_dispatch_offer_sms(db, job, best_mechanic, attempt)

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
    async def maybe_dispatch_next_wave(db: AsyncSession, job_id: uuid.UUID) -> None:
        """If no mechanic is assigned and no open parallel offers remain, queue the next batch."""
        job_result = await db.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job or job.assigned_mechanic_id:
            return

        pending = await db.execute(
            select(DispatchAttempt).where(
                DispatchAttempt.job_id == job_id,
                DispatchAttempt.dispatch_status.in_(
                    [DispatchStatus.queued, DispatchStatus.calling]
                ),
            )
        )
        if pending.scalars().first():
            return

        batch = await DispatchService.dispatch_mechanics_batch(
            db, job_id, settings.DISPATCH_BATCH_SIZE
        )
        if not batch:
            return

        job_ref = await db.execute(select(Job).where(Job.id == job_id))
        job = job_ref.scalar_one_or_none()
        if not job:
            return

        if settings.DISPATCH_VOICE_ON_BATCH:
            for item in batch:
                await DispatchService.launch_outbound_call(db, job, item)

    @staticmethod
    async def build_mechanic_offer_view(
        db: AsyncSession, job: Job, attempt: DispatchAttempt
    ) -> MechanicOfferView:
        """Public offer details for mechanic web UI."""
        driver_area = ", ".join(p for p in [job.driver_city, job.driver_state] if p) or None
        job_filled = job.assigned_mechanic_id is not None
        mechanic_result = await db.execute(
            select(Mechanic).where(Mechanic.id == attempt.mechanic_id)
        )
        mechanic = mechanic_result.scalar_one_or_none()
        suggested_eta_minutes = (
            DispatchService._estimate_eta_minutes_for_mechanic(job, mechanic)
            if mechanic
            else None
        )

        offer_state = "active"
        if attempt.dispatch_status == DispatchStatus.superseded:
            offer_state = "superseded"
        elif job_filled and job.assigned_mechanic_id != attempt.mechanic_id:
            offer_state = "filled"
        elif attempt.dispatch_status in (
            DispatchStatus.accepted,
            DispatchStatus.declined,
            DispatchStatus.unavailable,
            DispatchStatus.no_answer,
            DispatchStatus.timed_out,
        ):
            offer_state = "closed"

        return MechanicOfferView(
            public_job_id=job.public_job_id,
            issue_type=str(getattr(job.issue_type, "value", job.issue_type)),
            issue_summary=job.issue_summary,
            vehicle_type=job.vehicle_type,
            driver_area=driver_area,
            driver_lat=job.driver_lat,
            driver_lng=job.driver_lng,
            dispatch_attempt_id=str(attempt.id),
            dispatch_status=attempt.dispatch_status,
            suggested_eta_minutes=suggested_eta_minutes,
            offer_state=offer_state,
            job_filled=job_filled,
        )

    @staticmethod
    async def mechanic_offer_status(
        db: AsyncSession, job: Job, attempt: DispatchAttempt
    ) -> MechanicOfferStatusView:
        view = await DispatchService.build_mechanic_offer_view(db, job, attempt)
        return MechanicOfferStatusView(
            offer_state=view.offer_state,
            job_filled=view.job_filled,
            dispatch_status=view.dispatch_status,
            public_job_id=job.public_job_id,
        )

    @staticmethod
    async def list_rematch_candidates(
        db: AsyncSession, job: Job, limit: int = 15
    ) -> list[RematchCandidateView]:
        ranked = await DispatchService._get_ranked_mechanics_for_job(db, job)
        out: list[RematchCandidateView] = []
        for mechanic, score in ranked[:limit]:
            dist_miles = None
            if job.driver_lat is not None and job.driver_lng is not None:
                dist_miles = haversine_distance_meters(
                    job.driver_lat,
                    job.driver_lng,
                    mechanic.base_lat,
                    mechanic.base_lng,
                ) / 1609.344
            rating_val = float(mechanic.rating) if mechanic.rating is not None else None
            estimated_eta_minutes = DispatchService._estimate_eta_minutes_for_mechanic(
                job, mechanic
            )
            out.append(
                RematchCandidateView(
                    mechanic_id=str(mechanic.id),
                    company_name=mechanic.company_name,
                    contact_name=mechanic.contact_name,
                    city=mechanic.city,
                    state=mechanic.state,
                    rating=rating_val,
                    distance_miles=dist_miles,
                    estimated_eta_minutes=estimated_eta_minutes,
                    rank_score=score,
                    base_lat=mechanic.base_lat,
                    base_lng=mechanic.base_lng,
                )
            )
        return out

    @staticmethod
    async def rematch_select_mechanic(
        db: AsyncSession, job: Job, mechanic_id: uuid.UUID
    ) -> DispatchNextResponse:
        """Driver chose a specific mechanic after rejecting ETA — single outbound offer."""
        if job.driver_eta_decision != DriverEtaDecision.rejected.value:
            raise ValueError(
                "Rematch is only available after the driver rejects the proposed ETA"
            )
        if job.status not in (JobStatus.matching_mechanics, JobStatus.calling_mechanics):
            raise ValueError(f"Cannot rematch in status {job.status}")
        if job.assigned_mechanic_id:
            raise ValueError("Job already has an assigned mechanic")

        attempted_result = await db.execute(
            select(DispatchAttempt.mechanic_id).where(DispatchAttempt.job_id == job.id)
        )
        attempted_ids = {row[0] for row in attempted_result.all()}
        if mechanic_id in attempted_ids:
            raise ValueError("This provider was already contacted for this job")

        mech_result = await db.execute(
            select(Mechanic).where(Mechanic.id == mechanic_id, Mechanic.active == True)
        )
        mechanic = mech_result.scalar_one_or_none()
        if not mechanic:
            raise ValueError("Mechanic not found or inactive")

        if job.driver_lat is not None and job.driver_lng is not None:
            score = MechanicScoringService.score_mechanic(
                mechanic,
                job.driver_lat,
                job.driver_lng,
                str(job.issue_type),
                job.vehicle_type,
            )
        elif job.driver_city and job.driver_state:
            score = MechanicScoringService.score_mechanic_by_city(
                mechanic,
                job.driver_city,
                normalize_state(job.driver_state) or "",
                str(job.issue_type),
                job.vehicle_type,
            )
        else:
            raise ValueError("Driver location is required for rematch")

        attempt = DispatchAttempt(
            job_id=job.id,
            mechanic_id=mechanic.id,
            rank_score=score,
            dispatch_status=DispatchStatus.queued,
        )
        db.add(attempt)
        job.status = JobStatus.calling_mechanics
        job.driver_eta_decision = None
        await db.flush()

        await AuditService.log(
            db,
            job_id=job.id,
            event_type="dispatch.rematch_selected",
            actor_type="driver",
            payload={"mechanic_id": str(mechanic.id)},
        )

        await DispatchService._send_dispatch_offer_sms(db, job, mechanic, attempt)

        return DispatchNextResponse(
            dispatch_attempt_id=str(attempt.id),
            mechanic_company=mechanic.company_name,
            mechanic_contact=mechanic.contact_name or "",
            mechanic_phone=mechanic.phone or "",
            rank_score=score,
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
        notify_mechanic_tracking_sms: bool = True,
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
            job.driver_eta_decision = DriverEtaDecision.pending.value

            tracking = TrackingSession(
                job_id=job_id,
                mechanic_id=attempt.mechanic_id,
                tracking_status=TrackingStatus.pending,
            )
            db.add(tracking)

            other_attempts = await db.execute(
                select(DispatchAttempt).where(
                    DispatchAttempt.job_id == job_id,
                    DispatchAttempt.id != attempt_id,
                    DispatchAttempt.dispatch_status.in_(
                        [DispatchStatus.queued, DispatchStatus.calling]
                    ),
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
            if notify_mechanic_tracking_sms and mechanic and mechanic.phone:
                tracking_token = create_mechanic_tracking_token(
                    str(job.id),
                    job.public_job_id,
                    str(attempt.mechanic_id),
                )
                tracking_url = f"{settings.public_app_base_url}/mechanic-track/{tracking_token}"
                driver_location_hint = ", ".join(
                    part for part in [job.driver_city, job.driver_state] if part
                )
                issue_summary = job.issue_summary or str(job.issue_type)
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

        if response in ("declined", "unavailable", "no_answer", "timed_out"):
            await DispatchService.maybe_dispatch_next_wave(db, job_id)

        return MechanicResponseResponse(
            success=True,
            dispatch_status=attempt.dispatch_status,
            job_status=job.status,
            assigned_mechanic_id=(
                str(job.assigned_mechanic_id) if job.assigned_mechanic_id else None
            ),
        )

    @staticmethod
    async def auto_assign_demo_mechanic(
        db: AsyncSession,
        job: Job,
    ) -> DispatchNextResponse | None:
        if job.assigned_mechanic_id:
            return None

        next_attempt = await DispatchService.dispatch_next_mechanic(db, job.id)
        if not next_attempt:
            return None

        attempt_id = uuid.UUID(next_attempt.dispatch_attempt_id)
        attempt_result = await db.execute(
            select(DispatchAttempt).where(DispatchAttempt.id == attempt_id)
        )
        attempt = attempt_result.scalar_one_or_none()
        if not attempt:
            raise ValueError("Dispatch attempt not found")

        mechanic_result = await db.execute(
            select(Mechanic).where(Mechanic.id == attempt.mechanic_id)
        )
        mechanic = mechanic_result.scalar_one_or_none()
        if not mechanic:
            raise ValueError("Mechanic not found")

        mechanic_lat = mechanic.last_known_lat or mechanic.base_lat
        mechanic_lng = mechanic.last_known_lng or mechanic.base_lng
        distance_miles = haversine_distance_meters(
            job.driver_lat,
            job.driver_lng,
            mechanic_lat,
            mechanic_lng,
        ) / 1609.344
        eta_minutes = max(5, round((distance_miles / 35.0) * 60))

        await DispatchService.record_mechanic_response(
            db=db,
            job_id=job.id,
            attempt_id=attempt_id,
            response="accepted",
            eta_minutes=eta_minutes,
            notes="Auto-assigned nearest mechanic in demo mode",
            notify_mechanic_tracking_sms=False,
        )

        from app.services.tracking_service import TrackingService

        refreshed_job_result = await db.execute(select(Job).where(Job.id == job.id))
        refreshed_job = refreshed_job_result.scalar_one_or_none()
        if refreshed_job and refreshed_job.assigned_mechanic_id:
            await TrackingService.activate_tracking(db, refreshed_job)

        return next_attempt
