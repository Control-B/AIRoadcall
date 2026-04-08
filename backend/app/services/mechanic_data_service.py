from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.mechanic import Mechanic
from app.schemas.mechanic import MechanicCreateRequest, MechanicView
from app.core.logging import get_logger

logger = get_logger(__name__)


class MechanicDataService:
    """Service for creating, updating, and managing mechanic records."""

    @staticmethod
    async def upsert_mechanic(
        db: AsyncSession, request: MechanicCreateRequest
    ) -> MechanicView:
        """Create or update a mechanic by phone number."""
        result = await db.execute(
            select(Mechanic).where(Mechanic.phone == request.phone)
        )
        mechanic = result.scalar_one_or_none()

        if mechanic:
            # Update
            mechanic.company_name = request.company_name
            mechanic.contact_name = request.contact_name
            mechanic.service_types = request.service_types
            mechanic.vehicle_types_supported = request.vehicle_types_supported
            mechanic.base_lat = request.base_lat
            mechanic.base_lng = request.base_lng
            mechanic.active = request.active
            mechanic.accepts_mobile_roadside = request.accepts_mobile_roadside
            if request.rating is not None:
                mechanic.rating = request.rating
            if request.review_count is not None:
                mechanic.review_count = request.review_count
            if request.source:
                mechanic.source = request.source
            if request.source_confidence is not None:
                mechanic.source_confidence = request.source_confidence
            if request.source_url:
                mechanic.source_url = request.source_url
            if request.hours_of_operation:
                mechanic.hours_of_operation = request.hours_of_operation
            if request.address:
                mechanic.address = request.address
            if request.website:
                mechanic.website = request.website
            if request.email:
                mechanic.email = request.email
            logger.info(f"Mechanic updated: {mechanic.company_name}")
        else:
            mechanic = Mechanic(
                company_name=request.company_name,
                contact_name=request.contact_name,
                phone=request.phone,
                service_types=request.service_types,
                vehicle_types_supported=request.vehicle_types_supported,
                base_lat=request.base_lat,
                base_lng=request.base_lng,
                active=request.active,
                accepts_mobile_roadside=request.accepts_mobile_roadside,
                rating=request.rating,
                review_count=request.review_count,
                source=request.source,
                source_confidence=request.source_confidence,
                source_url=request.source_url,
                hours_of_operation=request.hours_of_operation,
                address=request.address,
                website=request.website,
                email=request.email,
            )
            db.add(mechanic)
            logger.info(f"Mechanic created: {request.company_name}")

        await db.flush()

        return MechanicView(
            id=str(mechanic.id),
            company_name=mechanic.company_name,
            contact_name=mechanic.contact_name,
            phone=mechanic.phone,
            service_types=mechanic.service_types,
            vehicle_types_supported=mechanic.vehicle_types_supported,
            base_lat=mechanic.base_lat,
            base_lng=mechanic.base_lng,
            active=mechanic.active,
            accepts_mobile_roadside=mechanic.accepts_mobile_roadside,
            rating=float(mechanic.rating) if mechanic.rating else None,
            review_count=mechanic.review_count,
            source=mechanic.source,
            source_confidence=mechanic.source_confidence,
            address=mechanic.address,
            website=mechanic.website,
            last_enriched_at=mechanic.last_enriched_at,
            total_dispatches=mechanic.total_dispatches,
            successful_dispatches=mechanic.successful_dispatches,
            avg_response_time_min=mechanic.avg_response_time_min,
            created_at=mechanic.created_at,
        )

    @staticmethod
    async def update_mechanic_location(
        db: AsyncSession, mechanic_id: str, lat: float, lng: float
    ) -> None:
        """Update a mechanic's live GPS location."""
        import uuid

        result = await db.execute(
            select(Mechanic).where(Mechanic.id == uuid.UUID(mechanic_id))
        )
        mechanic = result.scalar_one_or_none()
        if not mechanic:
            raise ValueError("Mechanic not found")

        mechanic.last_known_lat = lat
        mechanic.last_known_lng = lng
        mechanic.last_location_updated_at = datetime.now(timezone.utc)
        await db.flush()

    @staticmethod
    async def get_pipeline_stats(db: AsyncSession) -> dict:
        """Get aggregate stats about the mechanic database for the pipeline dashboard."""
        from datetime import timedelta

        total = await db.scalar(select(func.count(Mechanic.id)))
        active = await db.scalar(
            select(func.count(Mechanic.id)).where(Mechanic.active == True)  # noqa: E712
        )

        # Source breakdown
        source_rows = await db.execute(
            select(Mechanic.source, func.count(Mechanic.id))
            .group_by(Mechanic.source)
        )
        sources = {row[0] or "unknown": row[1] for row in source_rows.all()}

        # Enrichment stats
        never_enriched = await db.scalar(
            select(func.count(Mechanic.id)).where(Mechanic.last_enriched_at == None)  # noqa: E711
        )
        stale_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        stale = await db.scalar(
            select(func.count(Mechanic.id)).where(
                (Mechanic.last_enriched_at != None) &  # noqa: E711
                (Mechanic.last_enriched_at < stale_cutoff)
            )
        )

        avg_rating = await db.scalar(
            select(func.avg(Mechanic.rating)).where(Mechanic.rating != None)  # noqa: E711
        )
        avg_confidence = await db.scalar(
            select(func.avg(Mechanic.source_confidence)).where(
                Mechanic.source_confidence != None  # noqa: E711
            )
        )

        total_disp = await db.scalar(select(func.sum(Mechanic.total_dispatches))) or 0
        success_disp = await db.scalar(select(func.sum(Mechanic.successful_dispatches))) or 0

        return {
            "total_mechanics": total or 0,
            "active_mechanics": active or 0,
            "sources": sources,
            "never_enriched": never_enriched or 0,
            "stale_enrichment": stale or 0,
            "avg_rating": round(float(avg_rating), 2) if avg_rating else None,
            "avg_source_confidence": round(float(avg_confidence), 2) if avg_confidence else None,
            "total_dispatches": total_disp,
            "successful_dispatches": success_disp,
        }
