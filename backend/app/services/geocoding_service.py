"""Mapbox Geocoding service — converts addresses and caller locations to coordinates."""
from __future__ import annotations

import asyncio
import time

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

MAPBOX_GEOCODE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"
FLORIDA_BBOX = "-87.6349,24.3963,-79.9743,31.0009"
_CACHE_TTL_SECONDS = 60 * 60 * 24
_GEOCODE_CACHE: dict[str, tuple[float, dict]] = {}


class GeocodingService:
    """Forward-geocode an address string via Mapbox and return (lat, lng, display)."""

    @staticmethod
    async def geocode_location(location_text: str) -> dict | None:
        """Geocode caller-provided location text for dispatch matching.

        Returns normalized location metadata, coordinates, confidence, and the
        original Mapbox feature. Search is restricted to the United States and
        biased toward Florida when the text mentions FL/Florida.
        """
        query = (location_text or "").strip()
        if not query:
            return None

        cache_key = query.lower()
        cached = _GEOCODE_CACHE.get(cache_key)
        now = time.monotonic()
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

        token = settings.MAPBOX_ACCESS_TOKEN
        if not token:
            logger.warning("MAPBOX_ACCESS_TOKEN not set — cannot geocode location")
            return None

        mentions_florida = _mentions_florida(query)
        params = {
            "access_token": token,
            "country": "us",
            "limit": 5,
            "types": "address,poi,place,locality,neighborhood,district,postcode",
        }
        if mentions_florida:
            params["bbox"] = FLORIDA_BBOX

        data = None
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=8) as client:
                    response = await client.get(
                        f"{MAPBOX_GEOCODE_URL}/{query}.json",
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()
                    break
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(0.25 * (attempt + 1))

        if data is None:
            logger.error("Mapbox geocode_location failed for '%s': %s", query, last_error)
            return None

        features = data.get("features", [])
        if not features:
            logger.info("Mapbox returned no location results for: %s", query)
            return None

        feature = _choose_feature(features, prefer_state="FL" if mentions_florida else None)
        lng, lat = feature["center"]
        city, state = _extract_city_state(feature)
        normalized = feature.get("place_name") or ", ".join(part for part in (city, state) if part) or query
        relevance = float(feature.get("relevance") or 0.0)
        confidence = min(0.99, max(0.1, relevance + (0.08 if mentions_florida and state == "FL" else 0.0)))

        result = {
            "normalized_location": normalized,
            "city": city,
            "state": state,
            "latitude": float(lat),
            "longitude": float(lng),
            "confidence": round(confidence, 3),
            "mapbox_metadata": feature,
        }
        _GEOCODE_CACHE[cache_key] = (now, result)
        return result

    @staticmethod
    async def geocode_address(
        address: str,
        city: str = "",
        state: str = "",
    ) -> dict | None:
        """Geocode a free-form address string.

        Returns ``{"lat": float, "lng": float, "display": str}`` or ``None``.
        """
        token = settings.MAPBOX_ACCESS_TOKEN
        if not token:
            logger.warning("MAPBOX_ACCESS_TOKEN not set — cannot geocode")
            return None

        parts = [p.strip() for p in (address, city, state) if p and p.strip()]
        query = ", ".join(parts)
        if not query:
            return None

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{MAPBOX_GEOCODE_URL}/{query}.json",
                    params={
                        "access_token": token,
                        "country": "us",
                        "limit": 1,
                        "types": "address,poi,place,locality,neighborhood",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            features = data.get("features", [])
            if not features:
                logger.info("Mapbox returned no results for: %s", query)
                return None

            feature = features[0]
            lng, lat = feature["center"]  # Mapbox returns [lng, lat]
            display = feature.get("place_name", query)

            logger.info("Geocoded '%s' → (%.5f, %.5f) %s", query, lat, lng, display)
            return {"lat": lat, "lng": lng, "display": display}

        except Exception as e:
            logger.error("Mapbox geocoding failed for '%s': %s", query, e)
            return None

    @staticmethod
    async def reverse_geocode(latitude: float, longitude: float) -> dict | None:
        """Reverse-geocode a (lat, lng) into city, state, address.

        Returns a dict like:
            {
                "city": "Lakeland",
                "state": "FL",
                "address": "1234 Main St",
                "place_name": "1234 Main St, Lakeland, Florida 33801, United States",
                "latitude": 28.0395,
                "longitude": -81.9498,
                "mapbox_metadata": {...}
            }
        Returns None on failure.
        """
        token = settings.MAPBOX_ACCESS_TOKEN
        if not token:
            logger.warning("MAPBOX_ACCESS_TOKEN not set — cannot reverse geocode")
            return None

        cache_key = f"rev:{round(latitude, 5)},{round(longitude, 5)}"
        cached = _GEOCODE_CACHE.get(cache_key)
        now = time.monotonic()
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return cached[1]

        params = {
            "access_token": token,
            "country": "us",
            "limit": 1,
            "types": "address,poi,place,locality,neighborhood,postcode",
        }

        data = None
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=8) as client:
                    response = await client.get(
                        f"{MAPBOX_GEOCODE_URL}/{longitude},{latitude}.json",
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()
                    break
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(0.25 * (attempt + 1))

        if data is None:
            logger.error("Mapbox reverse_geocode failed for (%s,%s): %s", latitude, longitude, last_error)
            return None

        features = data.get("features", [])
        if not features:
            logger.info("Mapbox returned no reverse results for (%s,%s)", latitude, longitude)
            return None

        feature = features[0]
        city, state = _extract_city_state(feature)
        # Try to find a sibling address feature even if first feature is a POI/place
        address = feature.get("address") or feature.get("text")
        place_name = feature.get("place_name")

        result = {
            "city": city,
            "state": state,
            "address": address,
            "place_name": place_name,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "mapbox_metadata": feature,
        }
        _GEOCODE_CACHE[cache_key] = (now, result)
        return result


def _mentions_florida(value: str) -> bool:
    lowered = value.lower()
    return " florida" in f" {lowered}" or lowered.endswith(", fl") or " fl " in f" {lowered} " or lowered.endswith(" fl")


def _choose_feature(features: list[dict], prefer_state: str | None = None) -> dict:
    if not prefer_state:
        return features[0]
    for feature in features:
        _city, state = _extract_city_state(feature)
        if state == prefer_state:
            return feature
    return features[0]


def _extract_city_state(feature: dict) -> tuple[str | None, str | None]:
    city = None
    state = None
    place_type = feature.get("place_type") or []
    if "place" in place_type or "locality" in place_type:
        city = feature.get("text")
    for item in feature.get("context") or []:
        item_id = str(item.get("id", ""))
        if city is None and (item_id.startswith("place") or item_id.startswith("locality")):
            city = item.get("text")
        if item_id.startswith("region"):
            short_code = (item.get("short_code") or "").upper()
            state = short_code.split("-")[-1] if short_code else item.get("text")
    if state is None and "region" in place_type:
        short_code = (feature.get("properties") or {}).get("short_code", "").upper()
        state = short_code.split("-")[-1] if short_code else feature.get("text")
    return city, state
