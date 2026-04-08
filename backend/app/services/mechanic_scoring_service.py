from app.models.mechanic import Mechanic
from app.utils.geo import haversine_distance_km
from app.core.logging import get_logger

logger = get_logger(__name__)

# Scoring weights (easily tunable)
WEIGHT_DISTANCE = 0.35
WEIGHT_ISSUE_MATCH = 0.25
WEIGHT_VEHICLE_MATCH = 0.15
WEIGHT_RATING = 0.10
WEIGHT_MOBILE_ROADSIDE = 0.10
WEIGHT_SOURCE_CONFIDENCE = 0.05

MAX_DISTANCE_KM = 80.0  # Beyond this, mechanic scores 0 for distance


class MechanicScoringService:

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

        # Issue type match
        service_types = mechanic.service_types or []
        issue_match = 1.0 if issue_type in service_types else 0.3
        score += WEIGHT_ISSUE_MATCH * issue_match

        # Vehicle type match
        vehicle_types = mechanic.vehicle_types_supported or []
        if vehicle_type and vehicle_types:
            vehicle_match = 1.0 if vehicle_type.lower() in [
                v.lower() for v in vehicle_types
            ] else 0.5
        else:
            vehicle_match = 0.6  # Neutral if unknown
        score += WEIGHT_VEHICLE_MATCH * vehicle_match

        # Rating score
        rating = float(mechanic.rating) if mechanic.rating else 3.0
        rating_score = rating / 5.0
        score += WEIGHT_RATING * rating_score

        # Mobile roadside capability
        mobile_score = 1.0 if mechanic.accepts_mobile_roadside else 0.0
        score += WEIGHT_MOBILE_ROADSIDE * mobile_score

        # Source confidence
        confidence = mechanic.source_confidence or 0.5
        score += WEIGHT_SOURCE_CONFIDENCE * confidence

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
