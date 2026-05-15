from __future__ import annotations

from dataclasses import dataclass, field
from math import cos, radians
from typing import Iterable

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mechanic import Mechanic
from app.services.travel_time_service import TravelTimeService
from app.utils.geo import haversine_distance_km

SEARCH_RADII_MILES = (25, 50, 75, 100, 150)
MILES_PER_KM = 0.621371


@dataclass(slots=True)
class ProviderCandidate:
    id: str
    business_name: str
    phone: str | None
    email: str | None
    address: str | None
    city: str | None
    state: str | None
    zip_code: str | None
    latitude: float
    longitude: float
    services: list[str]
    heavy_duty_support: bool
    roadside_support: bool
    mobile_mechanic: bool
    towing: bool
    availability_status: str
    rating: float | None
    response_score: float
    straight_line_distance: float
    drive_distance_miles: float | None = None
    estimated_drive_minutes: int | None = None
    rank_score: float = 0.0
    score_reasons: list[str] = field(default_factory=list)


class LocationMatchingService:
    """Geospatial provider ranking for Roadcall dispatch.

    This service treats the mechanic table as the provider source of truth and
    maps it to provider-shaped results for the new dispatch matching API.
    """

    @staticmethod
    async def find_nearby_providers(
        db: AsyncSession,
        *,
        latitude: float,
        longitude: float,
        service_needed: str,
        vehicle_type: str | None = None,
        urgency: str = "roadside",
        limit: int = 10,
    ) -> tuple[list[ProviderCandidate], int | None]:
        for radius in SEARCH_RADII_MILES:
            candidates = await LocationMatchingService._load_candidates(
                db,
                latitude=latitude,
                longitude=longitude,
                radius_miles=radius,
            )
            if candidates:
                ranked = await LocationMatchingService._rank_candidates(
                    latitude=latitude,
                    longitude=longitude,
                    candidates=candidates,
                    service_needed=service_needed,
                    vehicle_type=vehicle_type,
                    urgency=urgency,
                    limit=limit,
                )
                if ranked:
                    return ranked, radius
        return [], None

    @staticmethod
    async def _load_candidates(
        db: AsyncSession,
        *,
        latitude: float,
        longitude: float,
        radius_miles: int,
    ) -> list[ProviderCandidate]:
        lat_delta = radius_miles / 69.0
        lng_delta = radius_miles / max(1.0, 69.0 * abs(cos(radians(latitude))))

        result = await db.execute(
            select(Mechanic).where(
                and_(
                    Mechanic.active == True,
                    Mechanic.base_lat.is_not(None),
                    Mechanic.base_lng.is_not(None),
                    Mechanic.base_lat.between(latitude - lat_delta, latitude + lat_delta),
                    Mechanic.base_lng.between(longitude - lng_delta, longitude + lng_delta),
                )
            )
        )
        mechanics = result.scalars().all()
        candidates: list[ProviderCandidate] = []
        for mechanic in mechanics:
            distance = haversine_distance_km(latitude, longitude, mechanic.base_lat, mechanic.base_lng) * MILES_PER_KM
            if distance > radius_miles:
                continue
            if mechanic.service_radius_miles and distance > float(mechanic.service_radius_miles):
                continue
            services = [str(item) for item in (mechanic.service_types or []) if item]
            vehicles = [str(item).lower() for item in (mechanic.vehicle_types_supported or []) if item]
            service_text = " ".join(services).lower()
            heavy_duty = any(token in " ".join(vehicles + [service_text]) for token in ("heavy", "diesel", "semi", "truck", "fleet", "trailer"))
            towing = "tow" in service_text or "wrecker" in service_text
            response_score = float(getattr(mechanic, "response_score", None) or mechanic.priority_score or 0)
            candidates.append(
                ProviderCandidate(
                    id=str(mechanic.id),
                    business_name=mechanic.company_name,
                    phone=mechanic.phone,
                    email=mechanic.email,
                    address=mechanic.address,
                    city=mechanic.city,
                    state=mechanic.state,
                    zip_code=getattr(mechanic, "zip_code", None),
                    latitude=float(mechanic.base_lat),
                    longitude=float(mechanic.base_lng),
                    services=services,
                    heavy_duty_support=heavy_duty,
                    roadside_support=bool(mechanic.accepts_mobile_roadside or mechanic.emergency_service),
                    mobile_mechanic=bool(mechanic.accepts_mobile_roadside),
                    towing=towing,
                    availability_status=getattr(mechanic, "availability_status", None) or "unknown",
                    rating=float(mechanic.rating) if mechanic.rating is not None else None,
                    response_score=response_score,
                    straight_line_distance=round(distance, 1),
                )
            )
        return candidates

    @staticmethod
    async def _rank_candidates(
        *,
        latitude: float,
        longitude: float,
        candidates: Iterable[ProviderCandidate],
        service_needed: str,
        vehicle_type: str | None,
        urgency: str,
        limit: int,
    ) -> list[ProviderCandidate]:
        initial = sorted(candidates, key=lambda candidate: candidate.straight_line_distance)[: min(25, max(limit * 3, 10))]
        travel_times = await TravelTimeService.estimate_drive_times(latitude, longitude, initial, max_candidates=min(10, len(initial)))
        for candidate in initial:
            travel = travel_times.get(candidate.id)
            if travel:
                candidate.drive_distance_miles = travel.drive_distance_miles
                candidate.estimated_drive_minutes = travel.estimated_drive_minutes
            candidate.rank_score, candidate.score_reasons = LocationMatchingService._score_candidate(
                candidate,
                service_needed=service_needed,
                vehicle_type=vehicle_type,
                urgency=urgency,
            )
        return sorted(
            initial,
            key=lambda c: (
                c.estimated_drive_minutes if c.estimated_drive_minutes is not None else 9999,
                c.drive_distance_miles if c.drive_distance_miles is not None else c.straight_line_distance,
                -c.rank_score,
            ),
        )[:limit]

    @staticmethod
    def _score_candidate(
        candidate: ProviderCandidate,
        *,
        service_needed: str,
        vehicle_type: str | None,
        urgency: str,
    ) -> tuple[float, list[str]]:
        score = 100.0
        reasons: list[str] = []
        service_text = " ".join(candidate.services).lower()
        needed = (service_needed or "").lower()
        vehicle = (vehicle_type or "").lower()

        distance_basis = candidate.drive_distance_miles or candidate.straight_line_distance
        score -= min(distance_basis * 2.0, 80.0)
        reasons.append(f"{candidate.straight_line_distance:.1f} mi straight-line")

        if candidate.estimated_drive_minutes is not None:
            score -= min(candidate.estimated_drive_minutes * 0.45, 45.0)
            reasons.append(f"{candidate.estimated_drive_minutes} min estimated drive")

        service_tokens = [token for token in ("tire", "diesel", "engine", "battery", "fuel", "tow", "trailer", "brake", "mobile", "roadside") if token in needed]
        if any(token in service_text for token in service_tokens):
            score += 30
            reasons.append("service match")
        elif service_tokens:
            score -= 25
            reasons.append("weaker service match")

        if any(token in vehicle for token in ("semi", "heavy", "diesel", "truck", "trailer", "fleet")):
            if candidate.heavy_duty_support:
                score += 25
                reasons.append("heavy-duty capable")
            else:
                score -= 35
                reasons.append("not marked heavy-duty")

        if urgency == "roadside":
            if candidate.roadside_support:
                score += 20
                reasons.append("roadside capable")
            if candidate.mobile_mechanic:
                score += 15
                reasons.append("mobile mechanic")

        if "tow" in needed and candidate.towing:
            score += 20
            reasons.append("towing capable")

        score += min(candidate.response_score, 100) * 0.25
        if candidate.rating is not None:
            score += min(candidate.rating, 5.0) * 4
            reasons.append(f"{candidate.rating:.1f} rating")

        if candidate.availability_status in {"available", "open", "24_7"}:
            score += 15
            reasons.append("availability favorable")

        return round(score, 2), reasons
