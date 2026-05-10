from datetime import datetime, timezone
import math
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc

from app.models.mechanic import Mechanic
from app.schemas.mechanic import (
    MechanicCreateRequest,
    MechanicRecommendationRequest,
    MechanicRecommendationResponse,
    MechanicRecommendationView,
    MechanicSearchResult,
    MechanicView,
    MechanicAdminListItem,
    MechanicAdminListResponse,
    MechanicAdminStats,
)
from app.core.logging import get_logger
from app.services.mechanic_scoring_service import MechanicScoringService
from app.utils.geo import haversine_distance_km
from app.utils.location import city_matches, normalize_city, normalize_state, parse_city_state_from_address

logger = get_logger(__name__)


class MechanicDataService:
    """Service for creating, updating, and managing mechanic records."""

    _DAY_KEYS = {
        0: ("mon", "monday"),
        1: ("tue", "tues", "tuesday"),
        2: ("wed", "wednesday"),
        3: ("thu", "thur", "thurs", "thursday"),
        4: ("fri", "friday"),
        5: ("sat", "saturday"),
        6: ("sun", "sunday"),
    }

    _QUERY_STOP_WORDS = {
        "the", "a", "an", "nearest", "nearby", "shop", "shops", "location",
        "please", "find", "need", "me", "to", "for", "that", "does", "do",
        "with", "and", "or", "service", "services",
    }

    _SERVICE_HINTS = {
        "tire": "flat_tire",
        "tyre": "flat_tire",
        "flat": "flat_tire",
        "engine": "engine_trouble",
        "motor": "engine_trouble",
        "tow": "tow_needed",
        "towing": "tow_needed",
        "battery": "dead_battery",
        "jump": "dead_battery",
        "fuel": "fuel_delivery",
        "gas": "fuel_delivery",
        "lockout": "lockout",
        "keys": "lockout",
        "trailer": "trailer",
        "semi": "semi truck",
        "truck": "truck",
        "mechanic": "engine_trouble",
        "repair": "engine_trouble",
    }

    @staticmethod
    async def get_admin_stats(db: AsyncSession) -> MechanicAdminStats:
        total = await db.scalar(select(func.count(Mechanic.id))) or 0
        active = await db.scalar(
            select(func.count(Mechanic.id)).where(Mechanic.active == True)  # noqa: E712
        ) or 0
        with_phone = await db.scalar(
            select(func.count(Mechanic.id)).where(Mechanic.phone.isnot(None), Mechanic.phone != "")
        ) or 0
        with_email = await db.scalar(
            select(func.count(Mechanic.id)).where(Mechanic.email.isnot(None), Mechanic.email != "")
        ) or 0
        with_website = await db.scalar(
            select(func.count(Mechanic.id)).where(Mechanic.website.isnot(None), Mechanic.website != "")
        ) or 0
        roadside = await db.scalar(
            select(func.count(Mechanic.id)).where(Mechanic.accepts_mobile_roadside == True)  # noqa: E712
        ) or 0

        source_rows = await db.execute(
            select(Mechanic.source, func.count(Mechanic.id))
            .group_by(Mechanic.source)
            .order_by(desc(func.count(Mechanic.id)))
        )
        sources = {row[0] or "unknown": row[1] for row in source_rows.all()}

        state_rows = await db.execute(
            select(Mechanic.state, func.count(Mechanic.id))
            .where(Mechanic.state.isnot(None), Mechanic.state != "")
            .group_by(Mechanic.state)
            .order_by(desc(func.count(Mechanic.id)))
            .limit(10)
        )
        top_states = [
            {"state": row[0], "count": row[1]}
            for row in state_rows.all()
            if row[0]
        ]

        return MechanicAdminStats(
            total_mechanics=total,
            active_mechanics=active,
            total_with_phone=with_phone,
            total_with_email=with_email,
            total_with_website=with_website,
            roadside_mechanics=roadside,
            sources=sources,
            top_states=top_states,
        )

    @staticmethod
    async def list_admin_mechanics(
        db: AsyncSession,
        *,
        q: str | None = None,
        city: str | None = None,
        state: str | None = None,
        source: str | None = None,
        has_email: bool | None = None,
        has_website: bool | None = None,
        roadside_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> MechanicAdminListResponse:
        filters = []
        if q:
            term = f"%{q.strip()}%"
            filters.append(
                or_(
                    Mechanic.company_name.ilike(term),
                    Mechanic.contact_name.ilike(term),
                    Mechanic.phone.ilike(term),
                    Mechanic.email.ilike(term),
                    Mechanic.website.ilike(term),
                    Mechanic.address.ilike(term),
                )
            )
        if city:
            filters.append(Mechanic.city.ilike(f"%{city.strip()}%"))
        if state:
            filters.append(Mechanic.state == normalize_state(state))
        if source:
            filters.append(Mechanic.source == source)
        if has_email is True:
            filters.append(Mechanic.email.isnot(None))
            filters.append(Mechanic.email != "")
        elif has_email is False:
            filters.append(or_(Mechanic.email.is_(None), Mechanic.email == ""))
        if has_website is True:
            filters.append(Mechanic.website.isnot(None))
            filters.append(Mechanic.website != "")
        elif has_website is False:
            filters.append(or_(Mechanic.website.is_(None), Mechanic.website == ""))
        if roadside_only:
            filters.append(Mechanic.accepts_mobile_roadside == True)  # noqa: E712

        count_query = select(func.count(Mechanic.id))
        data_query = select(Mechanic).order_by(Mechanic.company_name.asc()).limit(limit).offset(offset)
        for condition in filters:
            count_query = count_query.where(condition)
            data_query = data_query.where(condition)

        total = await db.scalar(count_query) or 0
        rows = await db.execute(data_query)
        mechanics = rows.scalars().all()

        return MechanicAdminListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[
                MechanicAdminListItem(
                    id=str(mechanic.id),
                    company_name=mechanic.company_name,
                    contact_name=mechanic.contact_name,
                    phone=mechanic.phone,
                    email=mechanic.email,
                    website=mechanic.website,
                    address=mechanic.address,
                    city=mechanic.city,
                    state=mechanic.state,
                    service_types=mechanic.service_types or [],
                    vehicle_types_supported=mechanic.vehicle_types_supported or [],
                    active=mechanic.active,
                    accepts_mobile_roadside=mechanic.accepts_mobile_roadside,
                    rating=float(mechanic.rating) if mechanic.rating is not None else None,
                    review_count=mechanic.review_count,
                    source=mechanic.source,
                    source_confidence=mechanic.source_confidence,
                    lead_status=mechanic.lead_status,
                    last_enriched_at=mechanic.last_enriched_at,
                    created_at=mechanic.created_at,
                )
                for mechanic in mechanics
            ],
        )

    @staticmethod
    def _bounding_box(lat: float, lng: float, radius_km: float = 160.0) -> tuple[float, float, float, float]:
        lat_delta = radius_km / 111.0
        safe_cos = max(math.cos(math.radians(lat)), 0.2)
        lng_delta = radius_km / (111.0 * safe_cos)
        return lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta

    @staticmethod
    def _reliability_score(mechanic: Mechanic) -> float:
        if mechanic.total_dispatches > 0:
            return round(mechanic.successful_dispatches / mechanic.total_dispatches, 4)
        rating_score = (float(mechanic.rating) / 5.0) if mechanic.rating else 0.6
        confidence = mechanic.source_confidence or 0.5
        return round((rating_score * 0.7) + (confidence * 0.3), 4)

    @staticmethod
    def _estimated_response_minutes(
        mechanic: Mechanic,
        distance_miles: float | None,
    ) -> int | None:
        if mechanic.avg_response_time_min is not None and mechanic.avg_response_time_min > 0:
            return int(round(mechanic.avg_response_time_min))
        if distance_miles is None:
            return None
        travel_minutes = (distance_miles / 35.0) * 60.0
        return int(round(max(15.0, min(90.0, travel_minutes + 15.0))))

    @staticmethod
    def _response_speed_score(estimated_response_minutes: int | None) -> float:
        if estimated_response_minutes is None:
            return 0.55
        if estimated_response_minutes <= 15:
            return 1.0
        if estimated_response_minutes >= 90:
            return 0.0
        return round(1.0 - ((estimated_response_minutes - 15) / 75.0), 4)

    @staticmethod
    def _availability_score(mechanic: Mechanic, prefer_immediate: bool) -> float:
        available_now, status = MechanicDataService._available_now(mechanic)
        if available_now is False:
            return 0.0
        score = 1.0 if mechanic.active else 0.0
        if mechanic.accepts_mobile_roadside:
            score *= 1.0
        else:
            score *= 0.55
        if available_now is True:
            score *= 1.0
        elif available_now is None:
            score *= 0.7
        if prefer_immediate and mechanic.avg_response_time_min is not None:
            score *= 1.0 if mechanic.avg_response_time_min <= 30 else 0.75
        return round(score, 4)

    @staticmethod
    def _available_now(mechanic: Mechanic, now: datetime | None = None) -> tuple[bool | None, str]:
        if not mechanic.active:
            return False, "inactive"

        hours = mechanic.hours_of_operation
        if not hours:
            return None, "hours_unknown"

        now = now or datetime.now(timezone.utc)
        haystacks: list[str] = []
        if isinstance(hours, dict):
            note = hours.get("note")
            if note:
                haystacks.append(str(note))
            schedule = hours.get("schedule")
            if isinstance(schedule, list):
                haystacks.extend(str(item) for item in schedule if item)
            for value in hours.values():
                if isinstance(value, str):
                    haystacks.append(value)
        elif isinstance(hours, list):
            haystacks.extend(str(item) for item in hours if item)
        elif isinstance(hours, str):
            haystacks.append(hours)

        combined = " ".join(haystacks).lower()
        if any(token in combined for token in ("24/7", "24 hours", "open 24", "open twenty four")):
            return True, "open_24_7"
        if "closed permanently" in combined or "permanently closed" in combined:
            return False, "permanently_closed"

        day_text = MechanicDataService._current_day_hours_text(hours, now.weekday())
        if day_text is None:
            return None, "hours_unknown"

        normalized = day_text.lower().strip()
        if any(token in normalized for token in ("closed", "not open")):
            return False, "closed_today"
        if any(token in normalized for token in ("24/7", "24 hours", "open 24")):
            return True, "open_24_hours"

        minutes = MechanicDataService._minutes_from_hours_text(normalized)
        if len(minutes) >= 2:
            current_minutes = now.hour * 60 + now.minute
            open_minutes, close_minutes = minutes[0], minutes[1]
            if close_minutes < open_minutes:
                is_open = current_minutes >= open_minutes or current_minutes <= close_minutes
            else:
                is_open = open_minutes <= current_minutes <= close_minutes
            return (True, "open_now") if is_open else (False, "closed_now")

        if "open" in normalized:
            return True, "marked_open"
        return None, "hours_unparsed"

    @staticmethod
    def _current_day_hours_text(hours: object, weekday: int) -> str | None:
        day_keys = MechanicDataService._DAY_KEYS.get(weekday, ())
        if isinstance(hours, dict):
            for key in day_keys:
                if key in hours and isinstance(hours[key], str):
                    return str(hours[key])
                title_key = key.title()
                if title_key in hours and isinstance(hours[title_key], str):
                    return str(hours[title_key])
            schedule = hours.get("schedule")
            if isinstance(schedule, list):
                for item in schedule:
                    text = str(item)
                    if any(text.lower().startswith(key) for key in day_keys):
                        return text
        if isinstance(hours, list):
            for item in hours:
                text = str(item)
                if any(text.lower().startswith(key) for key in day_keys):
                    return text
        return None

    @staticmethod
    def _minutes_from_hours_text(text: str) -> list[int]:
        matches = re.findall(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text.lower())
        minutes: list[int] = []
        for hour_str, minute_str, meridiem in matches:
            hour = int(hour_str) % 12
            minute = int(minute_str or 0)
            if meridiem == "pm":
                hour += 12
            minutes.append(hour * 60 + minute)
        return minutes

    @staticmethod
    def _specialty_score(
        mechanic: Mechanic,
        issue_type: str,
        vehicle_type: str | None,
        trailer_type: str | None,
    ) -> float:
        issue_match = MechanicScoringService._issue_match_score(mechanic, issue_type)
        vehicle_query = vehicle_type or trailer_type
        vehicle_match = MechanicScoringService._vehicle_match_score(mechanic, vehicle_query)
        return round((issue_match * 0.6) + (vehicle_match * 0.4), 4)

    @staticmethod
    def _recommendation_reasons(
        mechanic: Mechanic,
        *,
        issue_type: str,
        vehicle_type: str | None,
        trailer_type: str | None,
        distance_miles: float | None,
        estimated_response_minutes: int | None,
        reliability_score: float,
        available_now: bool | None,
        availability_status: str,
    ) -> list[str]:
        reasons: list[str] = []
        if distance_miles is not None:
            reasons.append(f"about {distance_miles:.1f} miles away")
        if issue_type and issue_type in (mechanic.service_types or []):
            reasons.append(f"handles {issue_type.replace('_', ' ')} work")
        supported_types = [v.lower() for v in (mechanic.vehicle_types_supported or [])]
        for label in filter(None, [vehicle_type, trailer_type]):
            if label and label.lower() in supported_types:
                reasons.append(f"supports {label}")
                break
        if mechanic.accepts_mobile_roadside:
            reasons.append("offers mobile roadside service")
        if available_now is True:
            reasons.append("appears available right now")
        elif availability_status == "hours_unknown":
            reasons.append("availability not confirmed from hours data")
        if estimated_response_minutes is not None:
            reasons.append(f"historical response around {estimated_response_minutes} minutes")
        if reliability_score >= 0.75:
            reasons.append("strong reliability history")
        elif mechanic.rating and float(mechanic.rating) >= 4.5:
            reasons.append("high customer rating")
        return reasons[:4]

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        lowered = re.sub(r"[^a-z0-9' ]+", " ", (query or "").lower())
        terms = [term for term in lowered.split() if term and term not in MechanicDataService._QUERY_STOP_WORDS]
        return terms

    @staticmethod
    def _query_hints(query: str) -> tuple[str, str | None]:
        terms = MechanicDataService._query_terms(query)
        service_hint = ""
        vehicle_hint = None
        for term in terms:
            mapped = MechanicDataService._SERVICE_HINTS.get(term, "")
            if mapped in {"trailer", "semi truck", "truck"} and not vehicle_hint:
                vehicle_hint = mapped
            elif mapped and not service_hint:
                service_hint = mapped
        return service_hint, vehicle_hint

    @staticmethod
    def _shop_query_score(
        mechanic: Mechanic,
        query: str,
        service_hint: str,
        vehicle_hint: str | None,
    ) -> tuple[float, str]:
        terms = MechanicDataService._query_terms(query)
        searchable_text = " ".join(
            part for part in [
                mechanic.company_name,
                mechanic.address,
                mechanic.city,
                mechanic.state,
                mechanic.website,
                " ".join(str(item) for item in (mechanic.service_types or [])),
                " ".join(str(item) for item in (mechanic.vehicle_types_supported or [])),
            ]
            if part
        ).lower()
        company_text = (mechanic.company_name or "").lower()

        score = 0.0
        reasons: list[str] = []

        for term in terms:
            if term in company_text:
                score += 2.5
                reasons.append(f"matches {term} in the shop name")
            elif term in searchable_text:
                score += 1.0
                reasons.append(f"matches {term}")

        if service_hint and service_hint in (mechanic.service_types or []):
            score += 2.0
            reasons.append(f"handles {service_hint.replace('_', ' ')} work")

        if vehicle_hint and any(vehicle_hint.lower() in str(item).lower() for item in (mechanic.vehicle_types_supported or [])):
            score += 1.5
            reasons.append(f"supports {vehicle_hint}")

        if not terms:
            reasons.append("closest active shop in the area")

        if mechanic.accepts_mobile_roadside:
            score += 0.25

        if mechanic.rating and float(mechanic.rating) >= 4.5:
            score += 0.2

        if not reasons:
            reasons.append("best nearby match")

        return score, reasons[0]

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

        query = select(Mechanic).where(Mechanic.active == True).order_by(Mechanic.state, Mechanic.city, Mechanic.company_name)  # noqa: E712
        if normalized_state:
            query = query.where(Mechanic.state == normalized_state)
        if lat is not None and lng is not None:
            min_lat, max_lat, min_lng, max_lng = MechanicDataService._bounding_box(lat, lng)
            query = query.where(
                Mechanic.base_lat >= min_lat,
                Mechanic.base_lat <= max_lat,
                Mechanic.base_lng >= min_lng,
                Mechanic.base_lng <= max_lng,
            )

        effective_state = normalized_state
        result = await db.execute(query)
        mechanics = list(result.scalars().all())
        if not mechanics and normalized_city and normalized_state:
            city_result = await db.execute(
                select(Mechanic)
                .where(
                    Mechanic.active == True,  # noqa: E712
                    Mechanic.state == normalized_state,
                    func.lower(Mechanic.city) == normalized_city,
                )
                .order_by(Mechanic.company_name)
            )
            mechanics = list(city_result.scalars().all())
        if not mechanics and normalized_state:
            fallback_result = await db.execute(
                select(Mechanic).where(Mechanic.active == True).order_by(Mechanic.state, Mechanic.city, Mechanic.company_name)  # noqa: E712
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
    async def recommend_mechanics(
        db: AsyncSession,
        request: MechanicRecommendationRequest,
    ) -> MechanicRecommendationResponse:
        normalized_state = normalize_state(request.state)
        normalized_city = normalize_city(request.city)

        query = select(Mechanic).where(Mechanic.active == True).order_by(Mechanic.state, Mechanic.city, Mechanic.company_name)  # noqa: E712
        if normalized_state:
            query = query.where(Mechanic.state == normalized_state)
        if request.require_mobile_roadside:
            query = query.where(Mechanic.accepts_mobile_roadside == True)  # noqa: E712
        if request.min_rating is not None:
            query = query.where(Mechanic.rating >= request.min_rating)
        if request.lat is not None and request.lng is not None:
            min_lat, max_lat, min_lng, max_lng = MechanicDataService._bounding_box(request.lat, request.lng)
            query = query.where(
                Mechanic.base_lat >= min_lat,
                Mechanic.base_lat <= max_lat,
                Mechanic.base_lng >= min_lng,
                Mechanic.base_lng <= max_lng,
            )
        result = await db.execute(query)
        mechanics = list(result.scalars().all())
        if not mechanics and normalized_city and normalized_state:
            city_query = select(Mechanic).where(Mechanic.active == True)  # noqa: E712
            if request.require_mobile_roadside:
                city_query = city_query.where(Mechanic.accepts_mobile_roadside == True)  # noqa: E712
            if request.min_rating is not None:
                city_query = city_query.where(Mechanic.rating >= request.min_rating)
            city_query = city_query.where(
                Mechanic.state == normalized_state,
                func.lower(Mechanic.city) == normalized_city,
            ).order_by(Mechanic.company_name)
            city_result = await db.execute(city_query)
            mechanics = list(city_result.scalars().all())
        if request.require_available_now:
            mechanics = [m for m in mechanics if MechanicDataService._available_now(m)[0] is True]
        if not mechanics:
            return MechanicRecommendationResponse(
                summary="No matching mechanics found for those criteria.",
                recommendations=[],
            )

        if request.lat is not None and request.lng is not None:
            ranked = MechanicScoringService.rank_mechanics(
                mechanics=mechanics,
                driver_lat=request.lat,
                driver_lng=request.lng,
                issue_type=request.issue_type,
                vehicle_type=request.vehicle_type or request.trailer_type,
            )
            centroid_lat = request.lat
            centroid_lng = request.lng
        else:
            ranked = MechanicScoringService.rank_mechanics_by_city(
                mechanics=mechanics,
                driver_city=normalized_city or "",
                driver_state=normalized_state or "",
                issue_type=request.issue_type,
                vehicle_type=request.vehicle_type or request.trailer_type,
            )
            city_matches_only = [m for m, _ in ranked if normalized_city and city_matches(m.city, normalized_city)]
            centroid_lat = None
            centroid_lng = None
            if city_matches_only:
                centroid_lat = sum(m.base_lat for m in city_matches_only) / len(city_matches_only)
                centroid_lng = sum(m.base_lng for m in city_matches_only) / len(city_matches_only)

        enriched: list[MechanicRecommendationView] = []
        for mechanic, base_score in ranked:
            distance_miles = None
            if request.lat is not None and request.lng is not None:
                distance_miles = round(
                    haversine_distance_km(request.lat, request.lng, mechanic.base_lat, mechanic.base_lng) * 0.621371,
                    1,
                )
            elif centroid_lat is not None and centroid_lng is not None:
                distance_miles = round(
                    haversine_distance_km(centroid_lat, centroid_lng, mechanic.base_lat, mechanic.base_lng) * 0.621371,
                    1,
                )

            reliability_score = MechanicDataService._reliability_score(mechanic)
            available_now, availability_status = MechanicDataService._available_now(mechanic)
            specialty_score = MechanicDataService._specialty_score(
                mechanic,
                issue_type=request.issue_type,
                vehicle_type=request.vehicle_type,
                trailer_type=request.trailer_type,
            )
            estimated_response_minutes = MechanicDataService._estimated_response_minutes(
                mechanic,
                distance_miles,
            )
            response_speed_score = MechanicDataService._response_speed_score(
                estimated_response_minutes,
            )
            availability_score = MechanicDataService._availability_score(
                mechanic,
                request.prefer_immediate,
            )
            recommendation_score = round(
                (base_score * 0.45)
                + (reliability_score * 0.2)
                + (specialty_score * 0.15)
                + (response_speed_score * 0.1)
                + (availability_score * 0.1),
                4,
            )

            enriched.append(
                MechanicRecommendationView(
                    id=str(mechanic.id),
                    company_name=mechanic.company_name,
                    contact_name=mechanic.contact_name,
                    phone=mechanic.phone,
                    city=mechanic.city,
                    state=mechanic.state,
                    distance_miles=distance_miles,
                    rating=float(mechanic.rating) if mechanic.rating else None,
                    accepts_mobile_roadside=mechanic.accepts_mobile_roadside,
                    available_now=available_now,
                    availability_status=availability_status,
                    estimated_response_minutes=estimated_response_minutes,
                    reliability_score=reliability_score,
                    specialty_score=specialty_score,
                    availability_score=availability_score,
                    recommendation_score=recommendation_score,
                    reasons=MechanicDataService._recommendation_reasons(
                        mechanic,
                        issue_type=request.issue_type,
                        vehicle_type=request.vehicle_type,
                        trailer_type=request.trailer_type,
                        distance_miles=distance_miles,
                        estimated_response_minutes=estimated_response_minutes,
                        reliability_score=reliability_score,
                        available_now=available_now,
                        availability_status=availability_status,
                    ),
                )
            )

        enriched.sort(key=lambda item: item.recommendation_score, reverse=True)
        top = enriched[: request.limit]

        if not top:
            return MechanicRecommendationResponse(
                summary="No matching mechanics found for those criteria.",
                recommendations=[],
            )

        summary = (
            f"Found {len(top)} recommended mechanics"
            f" for {request.issue_type.replace('_', ' ') if request.issue_type else 'this job'}"
            f" near {request.city + ', ' if request.city else ''}{request.state or 'the requested area'}."
        )
        return MechanicRecommendationResponse(summary=summary, recommendations=top)

    @staticmethod
    async def lookup_nearest_shops(
        db: AsyncSession,
        *,
        query: str,
        lat: float | None = None,
        lng: float | None = None,
        city: str | None = None,
        state: str | None = None,
        limit: int = 3,
    ) -> dict:
        normalized_state = normalize_state(state)
        normalized_city = normalize_city(city)
        service_hint, vehicle_hint = MechanicDataService._query_hints(query)
        query_terms = MechanicDataService._query_terms(query)

        mechanic_query = select(Mechanic).where(Mechanic.active == True).order_by(Mechanic.company_name)  # noqa: E712
        if normalized_state:
            mechanic_query = mechanic_query.where(Mechanic.state == normalized_state)
        if lat is not None and lng is not None:
            min_lat, max_lat, min_lng, max_lng = MechanicDataService._bounding_box(lat, lng)
            mechanic_query = mechanic_query.where(
                Mechanic.base_lat >= min_lat,
                Mechanic.base_lat <= max_lat,
                Mechanic.base_lng >= min_lng,
                Mechanic.base_lng <= max_lng,
            )

        result = await db.execute(mechanic_query)
        mechanics = list(result.scalars().all())
        if not mechanics and normalized_city and normalized_state:
            city_result = await db.execute(
                select(Mechanic).where(
                    Mechanic.active == True,  # noqa: E712
                    Mechanic.state == normalized_state,
                    func.lower(Mechanic.city) == normalized_city,
                )
            )
            mechanics = list(city_result.scalars().all())
        if not mechanics and normalized_state:
            fallback_result = await db.execute(
                select(Mechanic).where(
                    Mechanic.active == True,  # noqa: E712
                    Mechanic.state == normalized_state,
                ).order_by(Mechanic.company_name)
            )
            mechanics = list(fallback_result.scalars().all())
        if not mechanics:
            return {"summary": "I couldn't find a matching shop in that area.", "matches": []}

        ranked: list[tuple[Mechanic, float, float | None, str]] = []
        for mechanic in mechanics:
            query_score, reason = MechanicDataService._shop_query_score(
                mechanic,
                query=query,
                service_hint=service_hint,
                vehicle_hint=vehicle_hint,
            )
            if query_terms and query_score <= 0:
                continue

            distance_miles = None
            proximity_score = 0.0
            if lat is not None and lng is not None:
                distance_miles = round(
                    haversine_distance_km(lat, lng, mechanic.base_lat, mechanic.base_lng) * 0.621371,
                    1,
                )
                proximity_score = max(0.0, 1.0 - min(distance_miles, 100.0) / 100.0)
            elif normalized_city and normalized_state and city_matches(mechanic.city, normalized_city):
                proximity_score = 1.0
            elif normalized_state and normalize_state(mechanic.state) == normalized_state:
                proximity_score = 0.45

            total_score = (query_score * 2.0) + proximity_score
            if mechanic.rating:
                total_score += float(mechanic.rating) / 10.0

            ranked.append((mechanic, total_score, distance_miles, reason))

        ranked.sort(key=lambda item: item[1], reverse=True)
        top = ranked[:limit]
        if not top:
            return {"summary": "I couldn't find a matching shop in that area.", "matches": []}

        location_text = city or state or "that area"
        summary = f"I found {len(top)} nearby match{'es' if len(top) != 1 else ''} for {query} near {location_text}."
        matches = []
        for mechanic, _, distance_miles, reason in top:
            matches.append(
                {
                    "id": str(mechanic.id),
                    "company_name": mechanic.company_name,
                    "address": mechanic.address,
                    "city": mechanic.city,
                    "state": mechanic.state,
                    "phone": mechanic.phone,
                    "rating": float(mechanic.rating) if mechanic.rating else None,
                    "distance_miles": distance_miles,
                    "reason": reason,
                }
            )

        return {"summary": summary, "matches": matches}

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
