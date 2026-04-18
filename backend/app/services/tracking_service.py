from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.job import Job
from app.models.mechanic import Mechanic
from app.models.dispatch_attempt import DispatchAttempt
from app.models.tracking_session import TrackingSession
from app.schemas.tracking import TrackingView, MechanicTrackingView
from app.enums.job_status import JobStatus
from app.enums.tracking_status import TrackingStatus
from app.enums.dispatch_status import DispatchStatus
from app.utils.geo import haversine_distance_meters
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.audit_service import AuditService

logger = get_logger(__name__)
settings = get_settings()


class TrackingService:

    @staticmethod
    def _estimate_eta_minutes(distance_miles: float | None, fallback_eta: int | None = None) -> int | None:
        if distance_miles is None:
            return fallback_eta
        estimated = max(1, round((distance_miles / 35.0) * 60))
        if fallback_eta is None:
            return estimated
        return min(fallback_eta, estimated) if fallback_eta > 0 else estimated

    @staticmethod
    async def get_tracking_view(
        db: AsyncSession, job: Job
    ) -> TrackingView:
        """Build tracking payload for the driver-facing UI."""
        mechanic_lat = None
        mechanic_lng = None
        mechanic_company = None
        mechanic_contact = None
        mechanic_last_updated = None
        tracking_status = TrackingStatus.not_started
        started_at = None
        eta_minutes = None
        distance_miles = None
        mechanic_address = None
        mechanic_city = None
        mechanic_state = None
        accepted_eta = None

        if job.assigned_mechanic_id:
            accepted_attempt_result = await db.execute(
                select(DispatchAttempt).where(
                    DispatchAttempt.job_id == job.id,
                    DispatchAttempt.mechanic_id == job.assigned_mechanic_id,
                    DispatchAttempt.dispatch_status == DispatchStatus.accepted,
                )
            )
            accepted_attempt = accepted_attempt_result.scalar_one_or_none()
            accepted_eta = accepted_attempt.availability_eta_minutes if accepted_attempt else None

            # Get tracking session
            ts_result = await db.execute(
                select(TrackingSession).where(
                    TrackingSession.job_id == job.id,
                    TrackingSession.mechanic_id == job.assigned_mechanic_id,
                )
            )
            session = ts_result.scalar_one_or_none()
            if session:
                tracking_status = session.tracking_status
                started_at = session.started_at

                # Update last driver view
                session.last_driver_view_at = datetime.now(timezone.utc)
                await db.flush()

            # Get mechanic info and location
            mech_result = await db.execute(
                select(Mechanic).where(Mechanic.id == job.assigned_mechanic_id)
            )
            mechanic = mech_result.scalar_one_or_none()
            if mechanic:
                mechanic_lat = mechanic.last_known_lat or mechanic.base_lat
                mechanic_lng = mechanic.last_known_lng or mechanic.base_lng
                mechanic_company = mechanic.company_name
                mechanic_contact = mechanic.contact_name
                mechanic_last_updated = mechanic.last_location_updated_at
                mechanic_address = mechanic.address
                mechanic_city = mechanic.city
                mechanic_state = mechanic.state

                # Check arrival proximity
                if (
                    mechanic_lat
                    and mechanic_lng
                    and job.driver_lat
                    and job.driver_lng
                ):
                    dist = haversine_distance_meters(
                        job.driver_lat, job.driver_lng,
                        mechanic_lat, mechanic_lng,
                    )
                    if dist <= settings.MECHANIC_ARRIVAL_THRESHOLD_METERS:
                        if job.status == JobStatus.mechanic_en_route:
                            job.status = JobStatus.mechanic_arrived
                            if session:
                                session.tracking_status = TrackingStatus.arrived
                            await AuditService.log(
                                db,
                                job_id=job.id,
                                event_type="mechanic.arrived",
                                actor_type="system",
                                payload={"distance_meters": dist},
                            )
                            await db.flush()

                if mechanic_lat and mechanic_lng and job.driver_lat and job.driver_lng:
                    distance_miles = haversine_distance_meters(
                        job.driver_lat,
                        job.driver_lng,
                        mechanic_lat,
                        mechanic_lng,
                    ) / 1609.344
                    eta_minutes = TrackingService._estimate_eta_minutes(distance_miles, accepted_eta)
                else:
                    eta_minutes = accepted_eta

        return TrackingView(
            tracking_status=tracking_status,
            driver_lat=job.driver_lat,
            driver_lng=job.driver_lng,
            driver_location_captured_at=job.driver_location_captured_at,
            mechanic_lat=mechanic_lat,
            mechanic_lng=mechanic_lng,
            mechanic_company=mechanic_company,
            mechanic_contact=mechanic_contact,
            mechanic_address=mechanic_address,
            mechanic_city=mechanic_city,
            mechanic_state=mechanic_state,
            mechanic_last_updated=mechanic_last_updated,
            eta_minutes=eta_minutes,
            distance_miles=distance_miles,
            started_at=started_at,
            job_status=job.status,
            driver_eta_decision=job.driver_eta_decision,
        )

    @staticmethod
    async def get_mechanic_tracking_view(db: AsyncSession, job: Job) -> MechanicTrackingView:
        tracking = await TrackingService.get_tracking_view(db, job)
        return MechanicTrackingView(
            public_job_id=job.public_job_id,
            job_status=job.status,
            driver_name=job.driver_name,
            vehicle_type=job.vehicle_type,
            issue_type=job.issue_type,
            issue_summary=job.issue_summary,
            driver_lat=tracking.driver_lat,
            driver_lng=tracking.driver_lng,
            driver_location_captured_at=tracking.driver_location_captured_at,
            mechanic_lat=tracking.mechanic_lat,
            mechanic_lng=tracking.mechanic_lng,
            mechanic_company=tracking.mechanic_company,
            mechanic_contact=tracking.mechanic_contact,
            eta_minutes=tracking.eta_minutes,
            distance_miles=tracking.distance_miles,
        )

    @staticmethod
    async def activate_tracking(
        db: AsyncSession, job: Job
    ) -> None:
        """Activate tracking session when mechanic starts heading to driver."""
        if not job.assigned_mechanic_id:
            raise ValueError("No mechanic assigned")

        result = await db.execute(
            select(TrackingSession).where(
                TrackingSession.job_id == job.id,
                TrackingSession.mechanic_id == job.assigned_mechanic_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise ValueError("No tracking session found")

        session.tracking_status = TrackingStatus.active
        session.started_at = datetime.now(timezone.utc)
        job.status = JobStatus.mechanic_en_route

        await AuditService.log(
            db,
            job_id=job.id,
            event_type="tracking.activated",
            actor_type="system",
        )
        await db.flush()
        logger.info(f"Tracking activated for job {job.public_job_id}")
