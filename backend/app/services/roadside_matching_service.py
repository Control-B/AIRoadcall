import re
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Iterable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mechanic import Mechanic
from app.schemas.roadside_match import (
    RoadsideCallerContext,
    RoadsideLocationInput,
    RoadsideMajorVendorMatch,
    RoadsideMatchRequest,
    RoadsideMatchResponse,
    RoadsideMechanicMatch,
)
from app.services.geocoding_service import GeocodingService
from app.services.major_vendor_service import MajorVendorService
from app.utils.geo import haversine_distance_km
from app.utils.location import STATE_NAME_TO_CODE, normalize_city, normalize_state
from app.core.logging import get_logger


logger = get_logger(__name__)


PROBLEM_ALIASES: list[tuple[list[str], str]] = [
    (["tire", "tyre", "flat", "blowout", "blown tire", "wheel"], "flat_tire"),
    (["diesel", "engine", "mechanical", "motor", "overheat", "coolant", "radiator"], "engine_trouble"),
    (["battery", "jump", "jumpstart", "jump start", "alternator"], "dead_battery"),
    (["fuel", "gas", "out of gas", "def", "diesel fuel"], "fuel_delivery"),
    (["tow", "towing", "wrecker", "winch", "stuck"], "tow_needed"),
    (["lock", "lockout", "locked out", "keys"], "lockout"),
    (["trailer", "reefer", "brake", "air leak", "lights", "mudflap"], "trailer_repair"),
    (["accident", "crash", "collision"], "accident"),
]

SERVICE_LABELS = {
    "flat_tire": "tire repair",
    "engine_trouble": "diesel repair",
    "dead_battery": "battery",
    "fuel_delivery": "fuel",
    "tow_needed": "towing",
    "lockout": "lockout",
    "trailer_repair": "trailer repair",
    "accident": "accident support",
    "other": "roadside assistance",
}

VEHICLE_ALIASES = {
    "car": "light_duty",
    "auto": "light_duty",
    "automobile": "light_duty",
    "sedan": "light_duty",
    "suv": "light_duty",
    "pickup": "light_duty",
    "pickup truck": "light_duty",
    "light duty": "light_duty",
    "light-duty": "light_duty",
    "van": "light_duty",
    "semi": "heavy_duty",
    "semi truck": "heavy_duty",
    "tractor": "heavy_duty",
    "tractor trailer": "heavy_duty",
    "18 wheeler": "heavy_duty",
    "eighteen wheeler": "heavy_duty",
    "big rig": "heavy_duty",
    "heavy duty": "heavy_duty",
    "heavy-duty": "heavy_duty",
    "diesel truck": "heavy_duty",
    "box truck": "commercial",
    "straight truck": "commercial",
    "medium duty": "commercial",
    "medium-duty": "commercial",
    "trailer": "trailer",
    "reefer": "trailer",
    "dry van": "trailer",
    "rv": "rv",
    "motorhome": "rv",
    "camper": "rv",
    "travel trailer": "rv",
    "fleet": "fleet",
}

ROAD_RE = re.compile(
    r"\b(?P<road>(?:I|US|U\.S\.|HWY|HIGHWAY|SR|STATE ROAD|ROUTE|RT)\s*[- ]?\d+[A-Z]?|[A-Z][A-Za-z0-9 .'-]+\s(?:Road|Rd|Street|St|Avenue|Ave|Boulevard|Blvd|Lane|Ln|Drive|Dr))\b",
    re.IGNORECASE,
)
EXIT_RE = re.compile(
    r"\b(?:exit|mile marker|mm)\s*(?P<landmark>[A-Za-z0-9 -]+?)(?:\s+(?:with|at|near|on)\b|[,.]|$)",
    re.IGNORECASE,
)
COORD_RE = re.compile(r"(?P<lat>-?\d{1,2}\.\d+)\s*,\s*(?P<lng>-?\d{1,3}\.\d+)")

CITY_PREFIX_ALIASES = {
    "saint": ["saint", "st", "st."],
    "st": ["saint", "st", "st."],
    "st.": ["saint", "st", "st."],
    "fort": ["fort", "ft", "ft."],
    "ft": ["fort", "ft", "ft."],
    "ft.": ["fort", "ft", "ft."],
}

RADIUS_SEARCH_MILES = (25, 50, 100)


@dataclass
class ScoreResult:
    score: float
    distance_miles: float | None
    reasons: list[str]


@dataclass
class MechanicSearchResult:
    mechanics: list[Mechanic]
    search_level: str
    exact_count: int = 0
    radius_count: int = 0
    fallback_created: bool = False


def parseCallerLocation(text: str, location: RoadsideLocationInput | None = None) -> dict:
    combined = text or ""
    parsed: dict = {
        "city": None,
        "state": None,
        "road": None,
        "landmark": None,
        "latitude": None,
        "longitude": None,
    }

    coord_match = COORD_RE.search(combined)
    if coord_match:
        parsed["latitude"] = float(coord_match.group("lat"))
        parsed["longitude"] = float(coord_match.group("lng"))

    road_match = ROAD_RE.search(combined)
    if road_match:
        parsed["road"] = re.sub(r"\s+", " ", road_match.group("road")).strip()

    exit_match = EXIT_RE.search(combined)
    if exit_match:
        parsed["landmark"] = exit_match.group("landmark").strip(" .,;")

    parsed["state"] = _extract_state(combined)
    parsed["city"] = _extract_city(combined, parsed["state"])

    if location:
        if location.city:
            parsed["city"] = normalizeCity(location.city)
        if location.state:
            parsed["state"] = normalizeState(location.state)
        if location.road:
            parsed["road"] = location.road.strip()
        if location.landmark:
            parsed["landmark"] = location.landmark.strip()
        if location.latitude is not None:
            parsed["latitude"] = location.latitude
        if location.longitude is not None:
            parsed["longitude"] = location.longitude

    return parsed


def normalizeState(value: str | None) -> str | None:
    return normalize_state(value)


def normalizeCity(value: str | None) -> str | None:
    return normalize_city(value)


def classifyProblem(text: str | None) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    for aliases, problem in PROBLEM_ALIASES:
        if any(alias in lowered for alias in aliases):
            return problem
    return None


def normalizeVehicleType(text: str | None) -> str | None:
    if not text:
        return None
    lowered = text.lower().replace("-", " ")
    for alias, normalized in VEHICLE_ALIASES.items():
        if alias in lowered:
            return normalized
    return None


def parseCallerContext(message: str) -> RoadsideCallerContext:
    request = RoadsideMatchRequest(message=message)
    return RoadsideMatchingService.build_context(request)


def calculateDistanceMiles(lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None) -> float | None:
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    return haversine_distance_km(float(lat1), float(lon1), float(lat2), float(lon2)) * 0.621371


def findExactCityMatches(mechanics: Iterable[object], city: str | None, state: str | None, problemType: str | None = None) -> list[object]:
    context = RoadsideCallerContext(
        city=normalizeCity(city),
        state=normalizeState(state),
        problemType=classifyProblem(problemType) or problemType,
        serviceNeeded=SERVICE_LABELS.get(classifyProblem(problemType) or problemType or "other"),
    )
    return _filter_problem_capable(findMechanicsByStateCity(mechanics, state, city), context)


def findRadiusMatches(
    mechanics: Iterable[object],
    latitude: float,
    longitude: float,
    state: str | None,
    problemType: str | None,
    radiusMiles: int,
) -> list[object]:
    context = RoadsideCallerContext(
        latitude=latitude,
        longitude=longitude,
        state=normalizeState(state),
        problemType=classifyProblem(problemType) or problemType,
        serviceNeeded=SERVICE_LABELS.get(classifyProblem(problemType) or problemType or "other"),
    )
    qualified = []
    for mechanic in mechanics:
        if normalizeState(getattr(mechanic, "state", None)) != context.state:
            continue
        distance_miles = calculateDistanceMiles(latitude, longitude, getattr(mechanic, "base_lat", None), getattr(mechanic, "base_lng", None))
        if distance_miles is None:
            continue
        if distance_miles <= _service_radius(mechanic) or distance_miles <= radiusMiles:
            qualified.append(mechanic)
    return _filter_problem_capable(qualified, context)


def is_24_7(mechanic: object) -> bool:
    if bool(getattr(mechanic, "emergency_service", False)):
        return True
    hours = getattr(mechanic, "hours_of_operation", None)
    if not hours:
        return False
    text = " ".join(str(item) for item in _flatten_hours(hours)).lower()
    return any(token in text for token in ("24/7", "24 hours", "open 24", "24 hour"))


def findMechanicsByStateCity(mechanics: Iterable[object], state: str | None, city: str | None) -> list[object]:
    wanted_state = normalizeState(state)
    wanted_city_terms = _city_search_terms(city)
    return [
        mechanic
        for mechanic in mechanics
        if normalizeState(getattr(mechanic, "state", None)) == wanted_state
        and _normalized_city_key(getattr(mechanic, "city", None)) in wanted_city_terms
    ]


def scoreMechanicMatch(mechanic: object, callerContext: RoadsideCallerContext) -> ScoreResult:
    score = 0.0
    reasons: list[str] = []
    distance_miles: float | None = None

    mech_state = normalizeState(getattr(mechanic, "state", None))
    mech_city = normalizeCity(getattr(mechanic, "city", None))
    if callerContext.state and mech_state == callerContext.state:
        if callerContext.city and _city_matches(mech_city, callerContext.city):
            score += 30
            reasons.append("Exact city/state match")
        else:
            score += 10
            reasons.append("Same state fallback match")

    if callerContext.latitude is not None and callerContext.longitude is not None:
        base_lat = getattr(mechanic, "base_lat", None)
        base_lng = getattr(mechanic, "base_lng", None)
        if base_lat is not None and base_lng is not None:
            distance_miles = haversine_distance_km(
                callerContext.latitude,
                callerContext.longitude,
                base_lat,
                base_lng,
            ) * 0.621371
            radius = _service_radius(mechanic)
            if distance_miles <= radius:
                score += 25
                reasons.append(f"Within {radius} mile service radius")
            score += max(0, 20 - min(distance_miles, 100) * 0.2)
            reasons.append(f"{distance_miles:.1f} miles away")

    service_types = _lower_list(getattr(mechanic, "service_types", []) or [])
    problem = callerContext.problemType
    if problem and _service_matches_problem(service_types, problem, callerContext.serviceNeeded):
        score += 35
        reasons.append(f"Service match for {SERVICE_LABELS.get(problem, problem)}")
    elif problem:
        score += 4
        reasons.append("General roadside capability")

    vehicle_types = _lower_list(getattr(mechanic, "vehicle_types_supported", []) or [])
    vehicle = normalizeVehicleType(callerContext.vehicleType)
    raw_vehicle = (callerContext.vehicleType or "").lower()
    if vehicle and _vehicle_matches(vehicle_types, vehicle, raw_vehicle):
        score += 15
        reasons.append("Vehicle type match")
    elif vehicle in {"heavy_duty", "commercial", "fleet", "trailer"} and any(v in vehicle_types for v in ("heavy_duty", "commercial", "fleet", "trailer")):
        score += 8
        reasons.append("Commercial vehicle capable")
    elif vehicle:
        score -= 6
        reasons.append(f"Vehicle type not confirmed for {vehicle.replace('_', ' ')}")

    if is_24_7(mechanic):
        score += 15
        reasons.append("24/7 emergency availability")

    if bool(getattr(mechanic, "accepts_mobile_roadside", False)):
        score += 20
        reasons.append("Mobile roadside service")

    priority = _priority_score(mechanic)
    if priority:
        bonus = min(priority, 100) * 0.12
        score += bonus
        reasons.append(f"Priority score {priority}")

    if getattr(mechanic, "phone", None):
        score += 5
        reasons.append("Phone available")
    else:
        score -= 1000
        reasons.append("Disqualified: missing phone")

    rating = getattr(mechanic, "rating", None)
    if rating is not None:
        try:
            score += min(float(rating), 5.0)
        except (TypeError, ValueError):
            pass

    return ScoreResult(score=round(score, 2), distance_miles=distance_miles, reasons=reasons)


def rankMechanics(matches: list[tuple[object, ScoreResult]]) -> list[tuple[object, ScoreResult]]:
    return sorted(matches, key=lambda item: item[1].score, reverse=True)


def formatDispatchRecommendation(matches: list[tuple[object, ScoreResult]]) -> list[RoadsideMechanicMatch]:
    formatted = []
    for mechanic, scored in matches:
        problem_reasons = scored.reasons[:4]
        formatted.append(
            RoadsideMechanicMatch(
                mechanicId=str(getattr(mechanic, "id")),
                businessName=getattr(mechanic, "company_name", "Unknown mechanic"),
                phone=getattr(mechanic, "phone", ""),
                city=getattr(mechanic, "city", None),
                state=getattr(mechanic, "state", None),
                address=getattr(mechanic, "address", None),
                services=getattr(mechanic, "service_types", []) or [],
                vehicleTypes=getattr(mechanic, "vehicle_types_supported", []) or [],
                mobileService=bool(getattr(mechanic, "accepts_mobile_roadside", False)),
                emergencyService=is_24_7(mechanic),
                serviceRadiusMiles=_service_radius(mechanic),
                priorityScore=_priority_score(mechanic),
                distanceMiles=round(scored.distance_miles, 1) if scored.distance_miles is not None else None,
                score=scored.score,
                reason=", ".join(problem_reasons) if problem_reasons else "Best available mechanic match",
                internalReasons=scored.reasons,
            )
        )
    return formatted


class RoadsideMatchingService:
    @staticmethod
    async def match_mechanic(db: AsyncSession, request: RoadsideMatchRequest) -> RoadsideMatchResponse:
        context = RoadsideMatchingService.build_context(request)
        missing_fields = RoadsideMatchingService.missing_fields(context)
        city_level_request = RoadsideMatchingService._is_city_level_request(context)
        if missing_fields:
            logger.info(
                "roadside_match_needs_more_info city=%s state=%s problem=%s missing=%s",
                context.city,
                context.state,
                context.problemType,
                missing_fields,
            )
            return RoadsideMatchResponse(
                status="needs_more_info",
                searchLevel="not_started",
                matches=[],
                majorVendor=None,
                dispatchConfidence=None,
                needsMoreInfo=True,
                missingFields=missing_fields,
                callerContext=context,
                callerLocation=context,
                fallbackEscalation=False,
                message=RoadsideMatchingService.next_question(missing_fields),
            )

        option_limit = min(request.limit, 3)
        search_result = await RoadsideMatchingService.searchMechanics(db, context, limit=max(option_limit, 3))
        scored = rankMechanics([
            (mechanic, scoreMechanicMatch(mechanic, context))
            for mechanic in search_result.mechanics
            if _has_usable_phone(mechanic)
        ])
        top = scored[:option_limit]
        formatted = formatDispatchRecommendation(top)
        fallback_created = search_result.fallback_created or not bool(formatted)
        selected = formatted[0].businessName if formatted else None

        # Major vendor layer — always try to surface one big-chain option.
        major_vendor = await RoadsideMatchingService.findMajorVendor(db, context)

        # Dispatch confidence — normalized top score + presence of options.
        dispatch_confidence = RoadsideMatchingService._dispatch_confidence(top, major_vendor)

        logger.info(
            "roadside_match_result city=%s state=%s problem=%s exact=%s radius=%s selected=%s search_level=%s fallback_created=%s major_vendor=%s confidence=%.2f",
            context.city,
            context.state,
            context.problemType,
            search_result.exact_count,
            search_result.radius_count,
            selected,
            search_result.search_level,
            fallback_created,
            major_vendor.brandName if major_vendor else None,
            dispatch_confidence or 0.0,
        )
        return RoadsideMatchResponse(
            status="matched" if (formatted or major_vendor) else "manual_dispatch_required",
            searchLevel=search_result.search_level,
            matches=formatted,
            majorVendor=major_vendor,
            dispatchConfidence=dispatch_confidence,
            needsMoreInfo=False,
            missingFields=[],
            callerContext=context,
            callerLocation=context,
            fallbackEscalation=fallback_created and not major_vendor,
            fallbackCreated=fallback_created and not major_vendor,
            message=RoadsideMatchingService.match_message(
                context=context,
                matches=formatted,
                majorVendor=major_vendor,
                search_level=search_result.search_level,
                city_level_request=city_level_request,
            ),
        )

    @staticmethod
    def build_context(request: RoadsideMatchRequest) -> RoadsideCallerContext:
        text = " ".join(part for part in [request.message, request.transcript] if part)
        parsed_location = parseCallerLocation(text, request.location)
        if request.city:
            parsed_location["city"] = normalizeCity(request.city)
        if request.state:
            parsed_location["state"] = normalizeState(request.state)
        if request.latitude is not None:
            parsed_location["latitude"] = request.latitude
        if request.longitude is not None:
            parsed_location["longitude"] = request.longitude
        problem = classifyProblem(request.problemType or "") or classifyProblem(text)
        vehicle = normalizeVehicleType(request.vehicleType) or normalizeVehicleType(text)
        return RoadsideCallerContext(
            callerPhone=_clean_phone(request.callerPhone),
            callbackNumber=_clean_phone(request.callbackNumber or request.callerPhone),
            city=parsed_location.get("city"),
            state=parsed_location.get("state"),
            road=parsed_location.get("road"),
            landmark=parsed_location.get("landmark"),
            latitude=parsed_location.get("latitude"),
            longitude=parsed_location.get("longitude"),
            problemType=problem,
            serviceNeeded=SERVICE_LABELS.get(problem or "other"),
            vehicleType=vehicle,
            isEmergencyRoadside=True,
        )

    @staticmethod
    def missing_fields(context: RoadsideCallerContext) -> list[str]:
        missing = []
        has_usable_location = bool(
            (context.latitude is not None and context.longitude is not None)
            or context.city
            or context.road
            or context.landmark
        )
        if context.latitude is None and context.longitude is None:
            if not context.city and not context.road and not context.landmark:
                missing.append("location")
            if not context.state:
                missing.append("state")
        if not context.problemType:
            missing.append("problemType")
        if has_usable_location and context.state and context.problemType and not context.vehicleType:
            missing.append("vehicleType")
        return missing

    @staticmethod
    def next_question(missing_fields: list[str]) -> str:
        if "location" in missing_fields:
            return "What city or nearest exit?"
        if "state" in missing_fields:
            return "What state are you in?"
        if "problemType" in missing_fields:
            return "Is it tire, engine, battery, fuel, towing, or something else?"
        if "vehicleType" in missing_fields:
            return "What type of vehicle is it — car, pickup, box truck, semi, trailer, RV, or fleet vehicle?"
        return "Got it. I’m checking nearby mechanics."

    @staticmethod
    def _is_city_level_request(context: RoadsideCallerContext) -> bool:
        """True when caller gave city/state but no precise road/GPS/landmark.

        For these calls, the safest voice UX is not "here is the one closest
        mechanic" because we do not know the caller's exact position. Return a
        short list of local options and ask whether to send a GPS text, collect
        exact location, or proceed with one of the listed matches.
        """
        return bool(
            context.city
            and context.state
            and context.latitude is None
            and context.longitude is None
            and not context.road
            and not context.landmark
        )

    @staticmethod
    def match_message(
        *,
        context: RoadsideCallerContext,
        matches: list[RoadsideMechanicMatch],
        majorVendor: RoadsideMajorVendorMatch | None = None,
        search_level: str | None,
        city_level_request: bool,
    ) -> str:
        # Build the major-vendor sentence used in every variant.
        major_phrase = ""
        if majorVendor:
            corridor = ""
            if majorVendor.interstate and majorVendor.exitNumber:
                corridor = f" off {majorVendor.interstate} exit {majorVendor.exitNumber}"
            elif majorVendor.interstate:
                corridor = f" off {majorVendor.interstate}"
            elif majorVendor.city:
                corridor = f" in {majorVendor.city}"
            major_phrase = f" There is also a major option, {majorVendor.brandName}{corridor}."

        if not matches and majorVendor:
            return (
                f"I don't see a local mobile mechanic open right now, but"
                f"{major_phrase} Would you like me to dispatch them?"
            ).replace("but There", "but there")

        if not matches:
            return "No mechanic match found within search radius. Manual dispatch case created."

        local_count = len(matches[:3])

        if city_level_request:
            names = "; ".join(
                f"{idx + 1}) {match.businessName}"
                + (f" in {match.city}" if match.city else "")
                for idx, match in enumerate(matches[:3])
            )
            base = (
                f"I found {local_count} local mechanic{'s' if local_count != 1 else ''} near "
                f"{context.city}, {context.state}: {names}.{major_phrase} "
                "Would you prefer the closest mobile mechanic, the larger truck service center, "
                "or should I text you a secure GPS link to confirm your exact location?"
            )
            return base

        if search_level and search_level.startswith("radius_"):
            names = "; ".join(
                f"{idx + 1}) {match.businessName}"
                + (f" about {match.distanceMiles:.1f} miles away" if match.distanceMiles is not None else "")
                for idx, match in enumerate(matches[:3])
            )
            return (
                f"I found {local_count} nearby roadside match{'es' if local_count != 1 else ''}: "
                f"{names}.{major_phrase} "
                "Which would you like — the closest mobile mechanic or the larger truck service center?"
            )

        return f"Got it. I found nearby mechanics.{major_phrase}"

    @staticmethod
    def _dispatch_confidence(
        scored: list[tuple[object, ScoreResult]],
        major_vendor: RoadsideMajorVendorMatch | None,
    ) -> float | None:
        """Normalize top score to 0–1 with a small bonus when a major vendor exists."""
        if not scored and not major_vendor:
            return None
        top_score = scored[0][1].score if scored else 0.0
        # Empirically the matching pipeline tops out around ~120 for a perfect
        # local mechanic; treat 100 as the practical ceiling so we don't
        # under-report confidence on great matches.
        normalized = max(0.0, min(top_score, 100.0)) / 100.0
        if major_vendor:
            normalized = min(1.0, normalized + 0.10)
        return round(normalized, 2)

    @staticmethod
    async def findMajorVendor(
        db: AsyncSession,
        context: RoadsideCallerContext,
    ) -> RoadsideMajorVendorMatch | None:
        """Look up one major chain vendor near the caller, if any."""
        if not context.state:
            return None
        # Try to enrich coords if we only have city/state — geocoding-first.
        if context.latitude is None or context.longitude is None:
            try:
                await RoadsideMatchingService.getCoordinatesForCityState(db, context)
            except Exception:  # noqa: BLE001 — geocoding is best-effort
                pass
        try:
            found = await MajorVendorService.find_nearest(
                db,
                state=context.state,
                latitude=context.latitude,
                longitude=context.longitude,
                vehicle=context.vehicleType,
                problem=context.problemType,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("major_vendor_lookup_failed err=%s", exc)
            return None
        if not found:
            return None
        row, distance_miles = found
        corridor = ""
        if row.interstate and row.exit_number:
            corridor = f"{row.interstate} exit {row.exit_number}"
        elif row.interstate:
            corridor = row.interstate
        if distance_miles is not None:
            reason = f"{row.brand_name} {corridor} — about {distance_miles:.1f} miles away"
        elif corridor:
            reason = f"{row.brand_name} {corridor}"
        else:
            reason = f"{row.brand_name} in {row.city or row.state}"
        return RoadsideMajorVendorMatch(
            vendorId=str(row.id),
            brandName=row.brand_name,
            locationName=row.location_name,
            phone=row.phone,
            address=row.address,
            city=row.city,
            state=row.state,
            interstate=row.interstate,
            exitNumber=row.exit_number,
            services=list(row.services or []),
            heavyDuty=bool(row.heavy_duty),
            rvService=bool(row.rv_service),
            towing=bool(row.towing),
            tireService=bool(row.tire_service),
            is247=bool(row.is_24_7),
            distanceMiles=round(distance_miles, 1) if distance_miles is not None else None,
            priorityScore=row.priority_score,
            reason=reason.strip(),
        )

    @staticmethod
    async def findNearbyMechanics(db: AsyncSession, context: RoadsideCallerContext, limit: int = 10) -> list[Mechanic]:
        result = await RoadsideMatchingService.searchMechanics(db, context, limit=limit)
        return result.mechanics

    @staticmethod
    async def searchMechanics(db: AsyncSession, context: RoadsideCallerContext, limit: int = 10) -> MechanicSearchResult:
        exact_matches = await RoadsideMatchingService.findExactCityMatches(db, context)
        if exact_matches:
            return MechanicSearchResult(
                mechanics=exact_matches,
                search_level="exact_city",
                exact_count=len(exact_matches),
                radius_count=0,
            )

        await RoadsideMatchingService.getCoordinatesForCityState(db, context)
        for radius_miles in RADIUS_SEARCH_MILES:
            radius_matches = await RoadsideMatchingService.findRadiusMatches(db, context, radius_miles)
            if radius_matches:
                return MechanicSearchResult(
                    mechanics=radius_matches,
                    search_level=f"radius_{radius_miles}_miles",
                    exact_count=0,
                    radius_count=len(radius_matches),
                )

        if context.state and (context.latitude is None or context.longitude is None):
            state_matches = await RoadsideMatchingService.findSameStateFallbackMatches(db, context)
            if state_matches:
                return MechanicSearchResult(
                    mechanics=state_matches,
                    search_level="same_state_database_fallback",
                    exact_count=0,
                    radius_count=len(state_matches),
                )

        return RoadsideMatchingService.createManualDispatchFallback(context, search_level="radius_100_miles")

    @staticmethod
    async def getCoordinatesForCityState(db: AsyncSession, context: RoadsideCallerContext) -> tuple[float | None, float | None]:
        if context.latitude is not None and context.longitude is not None:
            return context.latitude, context.longitude
        if not context.city or not context.state:
            return None, None

        geocoded = await GeocodingService.geocode_address("", city=context.city, state=context.state)
        if geocoded:
            context.latitude = geocoded["lat"]
            context.longitude = geocoded["lng"]
            return context.latitude, context.longitude

        city_terms = _city_search_terms(context.city)
        centroid_query = select(Mechanic).where(
            Mechanic.active == True,  # noqa: E712
            func.upper(Mechanic.state) == context.state.upper(),
            Mechanic.base_lat.is_not(None),
            Mechanic.base_lng.is_not(None),
            or_(*[func.lower(Mechanic.city) == city_term for city_term in city_terms]),
        ).limit(50)
        result = await db.execute(centroid_query)
        city_mechanics = list(result.scalars().all())
        if city_mechanics:
            context.latitude = sum(float(mechanic.base_lat) for mechanic in city_mechanics) / len(city_mechanics)
            context.longitude = sum(float(mechanic.base_lng) for mechanic in city_mechanics) / len(city_mechanics)
            return context.latitude, context.longitude
        return None, None

    @staticmethod
    async def findExactCityMatches(db: AsyncSession, context: RoadsideCallerContext) -> list[Mechanic]:
        if not context.city or not context.state:
            return []
        query = select(Mechanic).where(Mechanic.active == True)  # noqa: E712
        city_terms = _city_search_terms(context.city)
        query = query.where(
            func.upper(Mechanic.state) == context.state.upper(),
            or_(*[func.lower(Mechanic.city) == city_term for city_term in city_terms]),
            Mechanic.phone.is_not(None),
            Mechanic.phone != "",
        ).limit(500)
        result = await db.execute(query)
        mechanics = list(result.scalars().all())
        return _filter_problem_capable(mechanics, context)

    @staticmethod
    async def findSameStateFallbackMatches(db: AsyncSession, context: RoadsideCallerContext) -> list[Mechanic]:
        if not context.state:
            return []
        query = select(Mechanic).where(
            Mechanic.active == True,  # noqa: E712
            func.upper(Mechanic.state) == context.state.upper(),
            Mechanic.phone.is_not(None),
            Mechanic.phone != "",
        ).limit(1000)
        result = await db.execute(query)
        return _filter_problem_capable(list(result.scalars().all()), context)

    @staticmethod
    async def findRadiusMatches(db: AsyncSession, context: RoadsideCallerContext, radiusMiles: int) -> list[Mechanic]:
        if context.latitude is None or context.longitude is None or not context.state:
            return []
        lat_delta = max(radiusMiles / 69.0, 0.5)
        lng_delta = max(radiusMiles / 55.0, 0.5)
        query = select(Mechanic).where(
            Mechanic.active == True,  # noqa: E712
            func.upper(Mechanic.state) == context.state.upper(),
            Mechanic.phone.is_not(None),
            Mechanic.phone != "",
            Mechanic.base_lat >= context.latitude - lat_delta,
            Mechanic.base_lat <= context.latitude + lat_delta,
            Mechanic.base_lng >= context.longitude - lng_delta,
            Mechanic.base_lng <= context.longitude + lng_delta,
        ).limit(1000)
        result = await db.execute(query)
        mechanics = []
        for mechanic in result.scalars().all():
            distance_miles = calculateDistanceMiles(
                context.latitude,
                context.longitude,
                getattr(mechanic, "base_lat", None),
                getattr(mechanic, "base_lng", None),
            )
            if distance_miles is None:
                continue
            qualifies_by_radius = distance_miles <= _service_radius(mechanic) or distance_miles <= radiusMiles
            if qualifies_by_radius:
                mechanics.append(mechanic)
        return _filter_problem_capable(mechanics, context)

    @staticmethod
    def createManualDispatchFallback(context: RoadsideCallerContext, search_level: str = "radius_100_miles") -> MechanicSearchResult:
        logger.warning(
            "roadside_manual_dispatch_fallback city=%s state=%s problem=%s callback=%s search_level=%s",
            context.city,
            context.state,
            context.problemType,
            context.callbackNumber,
            search_level,
        )
        return MechanicSearchResult(
            mechanics=[],
            search_level=search_level,
            fallback_created=True,
        )


# Backward-compatible aliases requested in the prompt.
findNearbyMechanics = RoadsideMatchingService.findNearbyMechanics


async def getCoordinatesForCityState(
    city: str | None,
    state: str | None,
    db: AsyncSession | None = None,
) -> tuple[float | None, float | None]:
    context = RoadsideCallerContext(city=normalizeCity(city), state=normalizeState(state))
    if db is None:
        geocoded = await GeocodingService.geocode_address("", city=context.city or "", state=context.state or "")
        return (geocoded["lat"], geocoded["lng"]) if geocoded else (None, None)
    return await RoadsideMatchingService.getCoordinatesForCityState(db, context)


def createManualDispatchFallback(callerContext: RoadsideCallerContext) -> MechanicSearchResult:
    return RoadsideMatchingService.createManualDispatchFallback(callerContext)


def _city_search_terms(city: str | None) -> set[str]:
    normalized = normalizeCity(city)
    if not normalized:
        return set()

    base = _normalized_city_key(normalized)
    terms = {base}
    parts = base.split(" ", 1)
    if len(parts) == 2:
        aliases = CITY_PREFIX_ALIASES.get(parts[0], [])
        terms.update(f"{alias.rstrip('.')} {parts[1]}" for alias in aliases)
        terms.update(f"{alias} {parts[1]}" for alias in aliases if alias.endswith("."))
    return {term for term in terms if term}


def _city_matches(left: str | None, right: str | None) -> bool:
    left_key = _normalized_city_key(left)
    return bool(left_key and left_key in _city_search_terms(right))


def _normalized_city_key(city: str | None) -> str | None:
    normalized = normalizeCity(city)
    if not normalized:
        return None
    return re.sub(r"\s+", " ", normalized.replace(".", "").lower()).strip()


def _service_matches_problem(service_types: list[str], problem: str, service_needed: str | None) -> bool:
    normalized_services = {_service_key(service_type) for service_type in service_types}
    service_text = " ".join(normalized_services)
    problem_key = _service_key(problem)
    needed_key = _service_key(service_needed)

    problem_terms = {
        problem_key,
        needed_key,
        *_problem_service_terms(problem),
    }
    return any(term and (term in normalized_services or term in service_text) for term in problem_terms)


def _filter_problem_capable(mechanics: Iterable[object], context: RoadsideCallerContext) -> list:
    phone_ready = [mechanic for mechanic in mechanics if _has_usable_phone(mechanic)]
    if not context.problemType:
        return phone_ready

    strong_matches = []
    vehicle_matches = []
    vehicle = normalizeVehicleType(context.vehicleType)
    raw_vehicle = (context.vehicleType or "").lower()
    for mechanic in mechanics:
        if not _has_usable_phone(mechanic):
            continue
        service_types = _lower_list(getattr(mechanic, "service_types", []) or [])
        vehicle_types = _lower_list(getattr(mechanic, "vehicle_types_supported", []) or [])
        if _service_matches_problem(service_types, context.problemType, context.serviceNeeded):
            strong_matches.append(mechanic)
            if vehicle and _vehicle_matches(vehicle_types, vehicle, raw_vehicle):
                vehicle_matches.append(mechanic)
    return _dedupe_mechanics([*vehicle_matches, *strong_matches, *phone_ready])


def _has_usable_phone(mechanic: object) -> bool:
    return bool(str(getattr(mechanic, "phone", "") or "").strip())


def _vehicle_matches(vehicle_types: list[str], vehicle: str, raw_vehicle: str = "") -> bool:
    vehicle_text = " ".join(vehicle_types)
    equivalent = {
        "light_duty": {"light_duty", "car", "auto", "automotive", "pickup", "suv", "van"},
        "heavy_duty": {"heavy_duty", "semi", "tractor", "diesel", "truck", "commercial", "fleet"},
        "commercial": {"commercial", "box_truck", "straight_truck", "medium_duty", "fleet", "truck"},
        "trailer": {"trailer", "reefer", "dry_van", "flatbed", "semi", "heavy_duty"},
        "rv": {"rv", "motorhome", "camper", "travel_trailer"},
        "fleet": {"fleet", "commercial", "heavy_duty", "truck"},
    }
    allowed = equivalent.get(vehicle, {vehicle})
    raw_key = _service_key(raw_vehicle)
    return any(
        candidate in vehicle_types
        or candidate in vehicle_text
        or (raw_key and raw_key in vehicle_text)
        for candidate in allowed
    )


def _problem_service_terms(problem: str) -> set[str]:
    terms = {_service_key(SERVICE_LABELS.get(problem, problem))}
    for aliases, mapped_problem in PROBLEM_ALIASES:
        if mapped_problem == problem:
            terms.update(_service_key(alias) for alias in aliases)
    return {term for term in terms if term}


def _service_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")


def _dedupe_mechanics(mechanics: list[Mechanic]) -> list[Mechanic]:
    seen: set[str] = set()
    deduped: list[Mechanic] = []
    for mechanic in mechanics:
        mechanic_id = str(getattr(mechanic, "id", ""))
        if mechanic_id in seen:
            continue
        seen.add(mechanic_id)
        deduped.append(mechanic)
    return deduped


def _clean_phone(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[^+0-9]", "", value)
    return cleaned or None


def _extract_state(text: str) -> str | None:
    for name, code in STATE_NAME_TO_CODE.items():
        if re.search(rf"\b{re.escape(name)}\b", text, flags=re.IGNORECASE):
            return code
    state_matches = list(re.finditer(r"\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|IA|ID|IL|IN|KS|KY|LA|MA|MD|ME|MI|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA|VT|WA|WI|WV|WY|DC)\b", text.upper()))
    return state_matches[-1].group(1) if state_matches else None


def _extract_city(text: str, state: str | None) -> str | None:
    state_pattern = _state_pattern(state)
    near_city_state = re.search(
        rf"\b(?:near|in|around|outside of)\s+([A-Za-z][A-Za-z .'-]{{1,40}}?)\s*,?\s*(?:{state_pattern})\b",
        text,
        flags=re.IGNORECASE,
    )
    if near_city_state:
        city = _clean_city_candidate(near_city_state.group(1))
        if city:
            return normalizeCity(city)

    if state:
        city_before_state = re.search(rf"\b(?:near|in|at|around|outside of)?\s*([A-Za-z][A-Za-z .'-]{{1,40}}?)\s*,?\s*(?:{state_pattern})\b", text, flags=re.IGNORECASE)
        if city_before_state:
            city = _clean_city_candidate(city_before_state.group(1))
            if city:
                return normalizeCity(city)
    near_match = re.search(r"\b(?:near|in|around|outside of)\s+([A-Za-z][A-Za-z .'-]{1,40})(?:\s+on\b|\s+with\b|\s+at\b|[,.]|$)", text, flags=re.IGNORECASE)
    if near_match:
        city = _clean_city_candidate(near_match.group(1))
        if city:
            return normalizeCity(city)
    return None


def _state_pattern(state: str | None) -> str:
    all_codes = "AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|IA|ID|IL|IN|KS|KY|LA|MA|MD|ME|MI|MN|MO|MS|MT|NC|ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VA|VT|WA|WI|WV|WY|DC"
    if not state:
        return all_codes
    names = [name for name, code in STATE_NAME_TO_CODE.items() if code == state]
    tokens = [re.escape(state), *[re.escape(name) for name in names]]
    return "|".join(tokens)


def _clean_city_candidate(value: str) -> str | None:
    cleaned = re.sub(r"\b(?:i|us|hwy|highway|route|rt|sr)\s*[- ]?\d+\b", "", value, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:near|in|at|around|outside|of|on|the|with|and|my|truck|semi|road|highway)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
    if not cleaned or len(cleaned) < 2:
        return None
    return cleaned


def _flatten_hours(hours: object) -> list[str]:
    if isinstance(hours, dict):
        values = []
        for value in hours.values():
            values.extend(_flatten_hours(value))
        return values
    if isinstance(hours, list):
        values = []
        for value in hours:
            values.extend(_flatten_hours(value))
        return values
    return [str(hours)] if hours else []


def _lower_list(values: list) -> list[str]:
    return [str(value).lower().replace(" ", "_") for value in values]


def _service_radius(mechanic: object) -> int:
    value = getattr(mechanic, "service_radius_miles", None)
    try:
        return int(value) if value is not None else 50
    except (TypeError, ValueError):
        return 50


def _priority_score(mechanic: object) -> int:
    value = getattr(mechanic, "priority_score", None)
    try:
        return int(value) if value is not None else 50
    except (TypeError, ValueError):
        return 50


def make_test_mechanic(**kwargs) -> SimpleNamespace:
    defaults = {
        "id": "mechanic_001",
        "company_name": "ABC Truck Repair",
        "contact_name": "ABC Truck Repair",
        "phone": "+18135551212",
        "service_types": ["flat_tire", "engine_trouble"],
        "vehicle_types_supported": ["heavy_duty", "trailer"],
        "base_lat": 27.9506,
        "base_lng": -82.4572,
        "city": "Tampa",
        "state": "FL",
        "address": "123 Main St, Tampa, FL",
        "accepts_mobile_roadside": True,
        "emergency_service": True,
        "service_radius_miles": 50,
        "priority_score": 90,
        "hours_of_operation": {"note": "Open 24 hours"},
        "rating": 4.8,
        "review_count": 120,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
