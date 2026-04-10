from app.models.mechanic import Mechanic
from app.utils.geo import haversine_distance_km
from app.utils.location import city_matches, normalize_state
from app.core.logging import get_logger

logger = get_logger(__name__)

# Scoring weights (easily tunable)
WEIGHT_DISTANCE = 0.35
WEIGHT_ISSUE_MATCH = 0.25
WEIGHT_VEHICLE_MATCH = 0.15
WEIGHT_RATING = 0.10
WEIGHT_MOBILE_ROADSIDE = 0.10
WEIGHT_SOURCE_CONFIDENCE = 0.05
WEIGHT_CITY_MATCH = 0.45

MAX_DISTANCE_KM = 80.0  # Beyond this, mechanic scores 0 for distance


class MechanicScoringService:

    @staticmethod
    def _issue_match_score(mechanic: Mechanic, issue_type: str) -> float:
        service_types = mechanic.service_types or []
        return 1.0 if issue_type in service_types else 0.3

    @staticmethod
    def _vehicle_match_score(mechanic: Mechanic, vehicle_type: str | None) -> float:
        vehicle_types = mechanic.vehicle_types_supported or []
        if vehicle_type and vehicle_types:
            return 1.0 if vehicle_type.lower() in [v.lower() for v in vehicle_types] else 0.5
        return 0.6

    @staticmethod
    def _quality_score(mechanic: Mechanic) -> float:
        rating = float(mechanic.rating) if mechanic.rating else 3.0
        rating_score = rating / 5.0
        mobile_score = 1.0 if mechanic.accepts_mobile_roadside else 0.0
        confidence = mechanic.source_confidence or 0.5
        return (
            (WEIGHT_RATING * rating_score)
            + (WEIGHT_MOBILE_ROADSIDE * mobile_score)
            + (WEIGHT_SOURCE_CONFIDENCE * confidence)
        )

    @staticmethod
    def score_mechanic(
        mechanic: Mechanic,
        driver_lat: float,
        driver_lng: float,
        issue_type: str,
        vehicle_type: str | None,
    ) -> float:
        """Score a single mechanic for a job. Higher is better (0.0 to 1.0)."""
        score = 0.0

        # Distance score (closer = higher)
        distance = haversine_distance_km(
            driver_lat, driver_lng, mechanic.base_lat, mechanic.base_lng
        )
        if distance > MAX_DISTANCE_KM:
            distance_score = 0.0
        else:
            distance_score = 1.0 - (distance / MAX_DISTANCE_KM)
        score += WEIGHT_DISTANCE * distance_score

        issue_match = MechanicScoringService._issue_match_score(mechanic, issue_type)
        score += WEIGHT_ISSUE_MATCH * issue_match

        vehicle_match = MechanicScoringService._vehicle_match_score(mechanic, vehicle_type)
        score += WEIGHT_VEHICLE_MATCH * vehicle_match
        score += MechanicScoringService._quality_score(mechanic)

        return round(score, 4)

    @staticmethod
    def score_mechanic_by_city(
        mechanic: Mechanic,
        driver_city: str,
        driver_state: str,
        issue_type: str,
        vehicle_type: str | None,
    ) -> float:
        mechanic_state = normalize_state(mechanic.state)
        wanted_state = normalize_state(driver_state)
        if wanted_state and mechanic_state != wanted_state:
            return 0.0

        city_score = 1.0 if city_matches(mechanic.city, driver_city) else 0.25
        score = WEIGHT_CITY_MATCH * city_score
        score += WEIGHT_ISSUE_MATCH * MechanicScoringService._issue_match_score(mechanic, issue_type)
        score += WEIGHT_VEHICLE_MATCH * MechanicScoringService._vehicle_match_score(mechanic, vehicle_type)
        score += MechanicScoringService._quality_score(mechanic)
        return round(score, 4)

    @staticmethod
    def rank_mechanics(
        mechanics: list[Mechanic],
        driver_lat: float,
        driver_lng: float,
        issue_type: str,
        vehicle_type: str | None,
    ) -> list[tuple[Mechanic, float]]:
        """Score and rank all candidate mechanics. Returns sorted (mechanic, score) pairs."""
        scored = []
        for m in mechanics:
            s = MechanicScoringService.score_mechanic(
                m, driver_lat, driver_lng, issue_type, vehicle_type
            )
            if s > 0.0:
                scored.append((m, s))

        scored.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"Ranked {len(scored)} mechanics from {len(mechanics)} candidates")
        return scored

    @staticmethod
    def rank_mechanics_by_city(
        mechanics: list[Mechanic],
        driver_city: str,
        driver_state: str,
        issue_type: str,
        vehicle_type: str | None,
    ) -> list[tuple[Mechanic, float]]:
        scored = []
        for mechanic in mechanics:
            score = MechanicScoringService.score_mechanic_by_city(
                mechanic,
                driver_city=driver_city,
                driver_state=driver_state,
                issue_type=issue_type,
                vehicle_type=vehicle_type,
            )
            if score > 0.0:
                scored.append((mechanic, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        logger.info(
            f"Ranked {len(scored)} mechanics from {len(mechanics)} candidates using city/state"
        )
        return scored
