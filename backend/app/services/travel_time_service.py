from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

MAPBOX_MATRIX_URL = "https://api.mapbox.com/directions-matrix/v1/mapbox/driving"
MILES_PER_METER = 0.000621371


@dataclass(slots=True)
class TravelTimeResult:
    provider_id: str
    drive_distance_miles: float | None
    estimated_drive_minutes: int | None
    source: str = "mapbox_matrix"


class TravelTimeService:
    """Mapbox Matrix-backed travel time calculator with safe Haversine fallback."""

    @staticmethod
    async def estimate_drive_times(
        origin_lat: float,
        origin_lng: float,
        candidates: Iterable[object],
        *,
        max_candidates: int = 10,
    ) -> dict[str, TravelTimeResult]:
        candidate_list = list(candidates)[:max_candidates]
        if not candidate_list:
            return {}

        token = settings.MAPBOX_ACCESS_TOKEN
        if not token:
            return TravelTimeService._fallback(candidate_list)

        coordinates = [f"{origin_lng},{origin_lat}"]
        for candidate in candidate_list:
            coordinates.append(f"{candidate.longitude},{candidate.latitude}")

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(
                    f"{MAPBOX_MATRIX_URL}/{';'.join(coordinates)}",
                    params={
                        "access_token": token,
                        "sources": "0",
                        "destinations": ";".join(str(i) for i in range(1, len(coordinates))),
                        "annotations": "duration,distance",
                    },
                )
                response.raise_for_status()
                payload = response.json()

            durations = (payload.get("durations") or [[]])[0] or []
            distances = (payload.get("distances") or [[]])[0] or []
            results: dict[str, TravelTimeResult] = {}
            for index, candidate in enumerate(candidate_list):
                duration_seconds = durations[index] if index < len(durations) else None
                distance_meters = distances[index] if index < len(distances) else None
                provider_id = str(candidate.id)
                results[provider_id] = TravelTimeResult(
                    provider_id=provider_id,
                    drive_distance_miles=round(float(distance_meters) * MILES_PER_METER, 1) if distance_meters is not None else None,
                    estimated_drive_minutes=max(1, round(float(duration_seconds) / 60)) if duration_seconds is not None else None,
                )
            return results
        except Exception as exc:
            logger.warning("Mapbox Matrix failed; falling back to straight-line estimates: %s", exc)
            return TravelTimeService._fallback(candidate_list)

    @staticmethod
    def _fallback(candidates: Iterable[object]) -> dict[str, TravelTimeResult]:
        results: dict[str, TravelTimeResult] = {}
        for candidate in candidates:
            straight = float(getattr(candidate, "straight_line_distance", 0.0) or 0.0)
            drive_distance = round(straight * 1.25, 1)
            estimated_minutes = max(5, round((drive_distance / 45.0) * 60)) if drive_distance else None
            provider_id = str(candidate.id)
            results[provider_id] = TravelTimeResult(
                provider_id=provider_id,
                drive_distance_miles=drive_distance,
                estimated_drive_minutes=estimated_minutes,
                source="haversine_fallback",
            )
        return results
