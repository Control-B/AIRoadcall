"""Seed the database with sample data for development and testing."""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.core.security import create_signed_token, generate_public_job_id
from app.core.database import Base
from app.models.job import Job
from app.models.mechanic import Mechanic
from app.models.dispatch_attempt import DispatchAttempt
from app.models.tracking_session import TrackingSession
from app.models.audit_event import AuditEvent
from app.enums.job_status import JobStatus
from app.enums.payment_status import PaymentStatus
from app.enums.dispatch_status import DispatchStatus
from app.enums.tracking_status import TrackingStatus

settings = get_settings()


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # --- Mechanics ---
        mechanic_1 = Mechanic(
            id=uuid.uuid4(),
            company_name="QuickFix Auto Services",
            contact_name="Mike Johnson",
            phone="+15551234001",
            service_types=["flat_tire", "dead_battery", "lockout", "fuel_delivery", "tow_needed"],
            vehicle_types_supported=["sedan", "suv", "truck", "van"],
            base_lat=34.0522,
            base_lng=-118.2437,
            active=True,
            accepts_mobile_roadside=True,
            rating=4.8,
            source="manual",
            source_confidence=1.0,
        )

        mechanic_2 = Mechanic(
            id=uuid.uuid4(),
            company_name="Roadside Rescue Pro",
            contact_name="Sarah Williams",
            phone="+15551234002",
            service_types=["flat_tire", "dead_battery", "engine_trouble", "overheating", "tow_needed"],
            vehicle_types_supported=["sedan", "suv", "truck"],
            base_lat=34.0195,
            base_lng=-118.4912,
            active=True,
            accepts_mobile_roadside=True,
            rating=4.5,
            source="manual",
            source_confidence=1.0,
        )

        mechanic_3 = Mechanic(
            id=uuid.uuid4(),
            company_name="24/7 Mobile Mechanics",
            contact_name="David Chen",
            phone="+15551234003",
            service_types=["dead_battery", "lockout", "fuel_delivery", "engine_trouble"],
            vehicle_types_supported=["sedan", "suv", "van", "motorcycle"],
            base_lat=34.0736,
            base_lng=-118.4004,
            active=True,
            accepts_mobile_roadside=True,
            rating=4.2,
            source="apify",
            source_confidence=0.85,
        )

        db.add_all([mechanic_1, mechanic_2, mechanic_3])
        await db.flush()

        # --- Sample Job (awaiting driver) ---
        public_id_1 = generate_public_job_id()
        job_1_id = uuid.uuid4()
        token_1 = create_signed_token(str(job_1_id), public_id_1)

        job_1 = Job(
            id=job_1_id,
            public_job_id=public_id_1,
            magic_link_token=token_1,
            magic_link_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            driver_name="Alex Rivera",
            driver_phone="+15559876543",
            vehicle_type="sedan",
            issue_type="flat_tire",
            issue_summary="Front passenger tire is completely flat. Driver is on the shoulder of I-405 northbound near exit 52.",
            status=JobStatus.awaiting_driver_location,
            payment_status=PaymentStatus.not_started,
            payment_hold_amount=150.00,
        )
        db.add(job_1)
        await db.flush()

        # --- Sample Job (mechanic assigned, for tracking testing) ---
        public_id_2 = generate_public_job_id()
        job_2_id = uuid.uuid4()
        token_2 = create_signed_token(str(job_2_id), public_id_2)

        # Set mechanic 1 as having a live location for tracking
        mechanic_1.last_known_lat = 34.0480
        mechanic_1.last_known_lng = -118.2500
        mechanic_1.last_location_updated_at = datetime.now(timezone.utc)

        job_2 = Job(
            id=job_2_id,
            public_job_id=public_id_2,
            magic_link_token=token_2,
            magic_link_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            driver_name="Jordan Smith",
            driver_phone="+15559876544",
            vehicle_type="suv",
            issue_type="dead_battery",
            issue_summary="Car won't start. Battery appears dead. Parked at a gas station on Wilshire Blvd.",
            status=JobStatus.mechanic_en_route,
            payment_status=PaymentStatus.authorized,
            payment_hold_amount=175.00,
            driver_lat=34.0622,
            driver_lng=-118.2337,
            driver_location_captured_at=datetime.now(timezone.utc),
            assigned_mechanic_id=mechanic_1.id,
        )
        db.add(job_2)
        await db.flush()

        # Dispatch attempt for job 2
        attempt = DispatchAttempt(
            job_id=job_2_id,
            mechanic_id=mechanic_1.id,
            rank_score=0.92,
            dispatch_status=DispatchStatus.accepted,
            called_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            responded_at=datetime.now(timezone.utc) - timedelta(minutes=8),
            availability_eta_minutes=15,
            response_notes="On my way, about 15 minutes out.",
        )
        db.add(attempt)

        # Tracking session for job 2
        tracking = TrackingSession(
            job_id=job_2_id,
            mechanic_id=mechanic_1.id,
            tracking_status=TrackingStatus.active,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=7),
        )
        db.add(tracking)

        # Audit events
        db.add(AuditEvent(
            job_id=job_1_id,
            event_type="job.created",
            actor_type="system",
            payload_json={"public_job_id": public_id_1},
        ))
        db.add(AuditEvent(
            job_id=job_2_id,
            event_type="job.created",
            actor_type="system",
            payload_json={"public_job_id": public_id_2},
        ))
        db.add(AuditEvent(
            job_id=job_2_id,
            event_type="mechanic.assigned",
            actor_type="system",
            payload_json={"mechanic_id": str(mechanic_1.id)},
        ))

        await db.commit()

        print("\n" + "=" * 60)
        print("SEED DATA CREATED SUCCESSFULLY")
        print("=" * 60)
        print(f"\nJob 1 (awaiting location): {public_id_1}")
        print(f"  Magic Link: {settings.APP_BASE_URL}/support/{token_1}")
        print(f"\nJob 2 (mechanic en route): {public_id_2}")
        print(f"  Magic Link: {settings.APP_BASE_URL}/support/{token_2}")
        print(f"\nMechanics:")
        print(f"  1. {mechanic_1.company_name} ({mechanic_1.phone})")
        print(f"  2. {mechanic_2.company_name} ({mechanic_2.phone})")
        print(f"  3. {mechanic_3.company_name} ({mechanic_3.phone})")
        print("=" * 60 + "\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
