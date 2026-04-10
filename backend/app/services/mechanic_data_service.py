from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.mechanic import Mechanic
from app.schemas.mechanic import MechanicCreateRequest, MechanicSearchResult, MechanicView
from app.core.logging import get_logger
from app.services.mechanic_scoring_service import MechanicScoringService
from app.utils.geo import haversine_distance_km
from app.utils.location import city_matches, normalize_city, normalize_state, parse_city_state_from_address

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
                mechanic.city, mechanic.state = parse_city_state_from_address(request.address)
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
                city=parse_city_state_from_address(request.address)[0] if request.address else None,
                state=parse_city_state_from_address(request.address)[1] if request.address else None,
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
            city=mechanic.city,
            state=mechanic.state,
            website=mechanic.website,
            last_enriched_at=mechanic.last_enriched_at,
            total_dispatches=mechanic.total_dispatches,
            successful_dispatches=mechanic.successful_dispatches,
            avg_response_time_min=mechanic.avg_response_time_min,
            created_at=mechanic.created_at,
        )

    @staticmethod
    async def search_mechanics(
        db: AsyncSession,
        lat: float | None = None,
        lng: float | None = None,
        city: str | None = None,
        state: str | None = None,
        issue_type: str = "",
        vehicle_type: str | None = None,
        limit: int = 5,
    ) -> list[MechanicSearchResult]:
        normalized_state = normalize_state(state)
        normalized_city = normalize_city(city)

        query = select(Mechanic).where(Mechanic.active == True)  # noqa: E712
        if normalized_state:
            query = query.where(Mechanic.state == normalized_state)

        effective_state = normalized_state
        result = await db.execute(query)
        mechanics = list(result.scalars().all())
        if not mechanics and normalized_state:
            fallback_result = await db.execute(
                select(Mechanic).where(Mechanic.active == True)  # noqa: E712
            )
            mechanics = list(fallback_result.scalars().all())
            effective_state = None
        if not mechanics:
            return []

        if lat is not None and lng is not None:
            ranked = MechanicScoringService.rank_mechanics(
                mechanics=mechanics,
                driver_lat=lat,
                driver_lng=lng,
                issue_type=issue_type,
                vehicle_type=vehicle_type,
            )
        elif normalized_city and normalized_state:
            ranked = MechanicScoringService.rank_mechanics_by_city(
                mechanics=mechanics,
                driver_city=normalized_city,
                driver_state=effective_state or "",
                issue_type=issue_type,
                vehicle_type=vehicle_type,
            )
        else:
            ranked = [
                (
                    mechanic,
                    MechanicScoringService.score_mechanic_by_city(
                        mechanic,
                        driver_city=normalized_city or mechanic.city or "",
                        driver_state=normalized_state or mechanic.state or "",
                        issue_type=issue_type,
                        vehicle_type=vehicle_type,
                    ),
                )
                for mechanic in mechanics
            ]
            ranked = [item for item in ranked if item[1] > 0.0]
            ranked.sort(key=lambda item: item[1], reverse=True)

        if not ranked:
            return []

        city_matches_only = [m for m, _ in ranked if normalized_city and city_matches(m.city, normalized_city)]
        centroid_lat = None
        centroid_lng = None
        if city_matches_only:
            centroid_lat = sum(m.base_lat for m in city_matches_only) / len(city_matches_only)
            centroid_lng = sum(m.base_lng for m in city_matches_only) / len(city_matches_only)

        items: list[MechanicSearchResult] = []
        for mechanic, score in ranked[:limit]:
            distance_miles = None
            if lat is not None and lng is not None:
                distance_miles = round(haversine_distance_km(lat, lng, mechanic.base_lat, mechanic.base_lng) * 0.621371, 1)
            elif centroid_lat is not None and centroid_lng is not None:
                distance_miles = round(haversine_distance_km(centroid_lat, centroid_lng, mechanic.base_lat, mechanic.base_lng) * 0.621371, 1)

            items.append(
                MechanicSearchResult(
                    id=str(mechanic.id),
                    company_name=mechanic.company_name,
                    contact_name=mechanic.contact_name,
                    phone=mechanic.phone,
                    city=mechanic.city,
                    state=mechanic.state,
                    rating=float(mechanic.rating) if mechanic.rating else None,
                    distance_miles=distance_miles,
                    rank_score=score,
                )
            )

        return items

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
