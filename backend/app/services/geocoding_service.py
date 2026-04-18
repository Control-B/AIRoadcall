"""Mapbox Geocoding service — converts addresses to lat/lng coordinates."""
import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

MAPBOX_GEOCODE_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"


class GeocodingService:
    """Forward-geocode an address string via Mapbox and return (lat, lng, display)."""

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
