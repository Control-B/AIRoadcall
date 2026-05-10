import re
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Iterable

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mechanic import Mechanic
from app.schemas.roadside_match import (
    RoadsideCallerContext,
    RoadsideLocationInput,
    RoadsideMatchRequest,
    RoadsideMatchResponse,
    RoadsideMechanicMatch,
)
from app.utils.geo import haversine_distance_km
from app.utils.location import STATE_NAME_TO_CODE, normalize_city, normalize_state


PROBLEM_ALIASES: list[tuple[list[str], str]] = [
    (["tire", "tyre", "flat", "blowout", "blown tire", "wheel"], "flat_tire"),
    (["diesel", "engine", "mechanical", "motor", "overheat", "coolant", "radiator"], "engine_trouble"),
    (["battery", "jump", "jumpstart", "jump start", "alternator"], "dead_battery"),
    (["fuel", "gas", "out of gas", "def", "diesel fuel"], "fuel_delivery"),
    (["tow", "towing", "wrecker", "winch", "stuck"], "tow_needed"),
    (["lock", "lockout", "locked out", "keys"], "lockout"),
    (["accident", "crash", "collision"], "accident"),
]

SERVICE_LABELS = {
    "flat_tire": "tire repair",
    "engine_trouble": "diesel repair",
    "dead_battery": "battery",
    "fuel_delivery": "fuel",
    "tow_needed": "towing",
    "lockout": "lockout",
    "accident": "accident support",
    "other": "roadside assistance",
}

VEHICLE_ALIASES = {
    "semi": "heavy_duty",
    "semi truck": "heavy_duty",
    "tractor trailer": "heavy_duty",
    "18 wheeler": "heavy_duty",
    "big rig": "heavy_duty",
    "box truck": "commercial",
    "trailer": "trailer",
    "rv": "rv",
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


@dataclass
class ScoreResult:
    score: float
    distance_miles: float | None
    reasons: list[str]


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
    return lowered.strip() or None


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
            score += 15
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
                score += 20
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
    if vehicle and (vehicle in vehicle_types or raw_vehicle in " ".join(vehicle_types)):
        score += 15
        reasons.append("Vehicle type match")
    elif vehicle and any(v in vehicle_types for v in ("heavy_duty", "commercial", "fleet")):
        score += 8
        reasons.append("Commercial vehicle capable")

    if is_24_7(mechanic):
        score += 10
        reasons.append("24/7 emergency availability")

    if bool(getattr(mechanic, "accepts_mobile_roadside", False)):
        score += 15
        reasons.append("Mobile roadside service")

    priority = _priority_score(mechanic)
    if priority:
        bonus = min(priority, 100) * 0.12
        score += bonus
        reasons.append(f"Priority score {priority}")

    if getattr(mechanic, "phone", None):
        score += 5
        reasons.append("Phone available")

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
        if missing_fields:
            return RoadsideMatchResponse(
                matches=[],
                needsMoreInfo=True,
                missingFields=missing_fields,
                callerContext=context,
                fallbackEscalation=False,
                message=RoadsideMatchingService.next_question(missing_fields),
            )

        mechanics = await RoadsideMatchingService.findNearbyMechanics(db, context, limit=max(request.limit, 3))
        scored = rankMechanics([
            (mechanic, scoreMechanicMatch(mechanic, context))
            for mechanic in mechanics
        ])
        top = scored[: request.limit]
        formatted = formatDispatchRecommendation(top)
        return RoadsideMatchResponse(
            matches=formatted,
            needsMoreInfo=False,
            missingFields=[],
            callerContext=context,
            fallbackEscalation=not bool(formatted),
            message=(
                "Got it. I found nearby mechanics."
                if formatted
                else "I could not find a confident match. Escalate to manual dispatch."
            ),
        )

    @staticmethod
    def build_context(request: RoadsideMatchRequest) -> RoadsideCallerContext:
        text = " ".join(part for part in [request.message, request.transcript] if part)
        parsed_location = parseCallerLocation(text, request.location)
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
        if context.latitude is None and context.longitude is None:
            if not context.city and not context.road and not context.landmark:
                missing.append("location")
            if not context.state:
                missing.append("state")
        if not context.problemType:
            missing.append("problemType")
        return missing

    @staticmethod
    def next_question(missing_fields: list[str]) -> str:
        if "location" in missing_fields:
            return "What city or nearest exit?"
        if "state" in missing_fields:
            return "What state are you in?"
        if "problemType" in missing_fields:
            return "Is it tire, engine, battery, fuel, towing, or something else?"
        return "Got it. I’m checking nearby mechanics."

    @staticmethod
    async def findNearbyMechanics(db: AsyncSession, context: RoadsideCallerContext, limit: int = 10) -> list[Mechanic]:
        query = select(Mechanic).where(Mechanic.active == True)  # noqa: E712
        if context.state:
            query = query.where(func.upper(Mechanic.state) == context.state.upper())

        if context.city:
            city_terms = _city_search_terms(context.city)
            city_query = query.where(
                or_(*[func.lower(Mechanic.city) == city_term for city_term in city_terms])
            ).limit(500)
            result = await db.execute(city_query)
            city_matches = list(result.scalars().all())
            if city_matches:
                if context.state and len(city_matches) < max(limit * 5, 25):
                    fallback_result = await db.execute(query.limit(500))
                    state_matches = list(fallback_result.scalars().all())
                    return _dedupe_mechanics([*city_matches, *state_matches])
                return city_matches

        if context.latitude is not None and context.longitude is not None:
            lat_delta = 2.0
            lng_delta = 2.0
            query = query.where(
                Mechanic.base_lat >= context.latitude - lat_delta,
                Mechanic.base_lat <= context.latitude + lat_delta,
                Mechanic.base_lng >= context.longitude - lng_delta,
                Mechanic.base_lng <= context.longitude + lng_delta,
            )

        result = await db.execute(query.limit(500))
        mechanics = list(result.scalars().all())
        if mechanics:
            return mechanics

        if context.state:
            fallback = await db.execute(select(Mechanic).where(Mechanic.active == True).limit(500))  # noqa: E712
            return list(fallback.scalars().all())
        return []


# Backward-compatible aliases requested in the prompt.
findNearbyMechanics = RoadsideMatchingService.findNearbyMechanics


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
