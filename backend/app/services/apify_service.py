"""Apify Service — Bulk mechanic data scraping.

Uses Apify's Google Maps Scraper actor to find mobile mechanics, towing
services, and roadside assistance providers in a given area. Results are
parsed, normalized, and upserted into our DB via MechanicDataService.

Flow:
  1. POST /api/pipeline/scrape  → triggers an Apify actor run
  2. The actor scrapes Google Maps for the search query + area
  3. We poll for completion (or use a webhook)
  4. On completion, fetch the dataset, parse each result, upsert

The Apify actor used: "compass/crawler-google-places" (Google Maps Scraper)
which returns structured JSON with name, address, phone, rating,
reviewsCount, location, website, openingHours, etc.
"""
import re
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.mechanic import MechanicCreateRequest

logger = get_logger(__name__)

APIFY_BASE_URL = "https://api.apify.com/v2"
# Google Maps Scraper actor — widely used, reliable
ACTOR_ID = "nwua9Gu5YrADL7ZDj"  # compass/crawler-google-places (Google Maps Scraper)

# Search queries to find roadside mechanics
DEFAULT_SEARCH_QUERIES = [
    "mobile mechanic",
    "roadside assistance",
    "tow truck service",
    "tire repair near me",
    "emergency car repair",
    "24 hour auto repair",
]

# Service type inference from business categories and descriptions
SERVICE_TYPE_KEYWORDS = {
    "flat_tire": ["tire", "flat", "puncture", "wheel"],
    "dead_battery": ["battery", "jump start", "charging"],
    "tow_needed": ["tow", "towing", "wrecker", "haul"],
    "lockout": ["locksmith", "lock", "key", "lockout"],
    "fuel_delivery": ["fuel", "gas delivery"],
    "engine_trouble": ["mechanic", "repair", "engine", "auto repair", "car repair"],
    "overheating": ["radiator", "coolant", "overheat"],
}


class ApifyService:
    """Manages Apify actor runs for bulk mechanic data ingestion."""

    def __init__(self):
        settings = get_settings()
        self.api_token = settings.APIFY_API_TOKEN
        self.headers = {"Authorization": f"Bearer {self.api_token}"}

    async def start_scrape(
        self,
        location: str,
        radius_miles: int = 25,
        max_results: int = 50,
    ) -> dict:
        """Start an Apify actor run to scrape Google Maps for mechanics.

        Args:
            location: City/area to search, e.g. "Austin, TX"
            radius_miles: Search radius
            max_results: Max results per search query

        Returns:
            Dict with run_id and status
        """
        if not self.api_token:
            raise ValueError("APIFY_API_TOKEN is not configured")

        # Build search queries with the location
        search_queries = [
            f"{q} in {location}" for q in DEFAULT_SEARCH_QUERIES
        ]

        actor_input = {
            "searchStringsArray": search_queries,
            "maxCrawledPlacesPerSearch": max_results,
            "language": "en",
            "deeperCityScrape": False,
            "includeWebResults": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{APIFY_BASE_URL}/acts/{ACTOR_ID}/runs",
                headers=self.headers,
                json=actor_input,
            )
            resp.raise_for_status()
            data = resp.json()["data"]

        run_id = data["id"]
        status = data["status"]

        logger.info(
            f"Apify scrape started: run_id={run_id}, status={status}, "
            f"location={location}, queries={len(search_queries)}"
        )

        return {
            "run_id": run_id,
            "status": status,
            "started_at": data.get("startedAt"),
        }

    async def get_run_status(self, run_id: str) -> dict:
        """Check the status of an Apify run."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{APIFY_BASE_URL}/actor-runs/{run_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()["data"]

        return {
            "run_id": run_id,
            "status": data["status"],
            "started_at": data.get("startedAt"),
            "finished_at": data.get("finishedAt"),
            "dataset_id": data.get("defaultDatasetId"),
        }

    async def fetch_results(self, run_id: str) -> list[dict]:
        """Fetch dataset items from a completed Apify run.

        Returns raw Apify result dicts.
        """
        # First get the dataset ID
        status = await self.get_run_status(run_id)
        dataset_id = status.get("dataset_id")
        if not dataset_id:
            raise ValueError(f"No dataset found for run {run_id}")

        if status["status"] not in ("SUCCEEDED",):
            raise ValueError(
                f"Run {run_id} is not complete (status: {status['status']})"
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(
                f"{APIFY_BASE_URL}/datasets/{dataset_id}/items",
                headers=self.headers,
                params={"format": "json", "clean": "true"},
            )
            resp.raise_for_status()
            items = resp.json()

        logger.info(f"Fetched {len(items)} results from Apify run {run_id}")
        return items

    def parse_result(self, item: dict) -> Optional[MechanicCreateRequest]:
        """Parse an Apify Google Maps result into a MechanicCreateRequest.

        Returns None if the result is missing required fields.
        """
        phone = item.get("phone")
        name = item.get("title") or item.get("name")
        lat = item.get("location", {}).get("lat")
        lng = item.get("location", {}).get("lng")

        # Phone is required for upsert (our unique key)
        if not phone or not name or lat is None or lng is None:
            return None

        # Clean up phone number
        phone = self._normalize_phone(phone)
        if not phone:
            return None

        # Infer service types from categories and title
        categories = item.get("categories", []) or []
        service_types = self._infer_service_types(name, categories)

        # Parse hours of operation
        hours = self._parse_hours(item.get("openingHours"))

        # Compute a confidence score based on data completeness
        confidence = self._compute_confidence(item)

        return MechanicCreateRequest(
            company_name=name[:255],
            contact_name=name[:255],  # Google Maps doesn't give individual names
            phone=phone,
            service_types=service_types,
            vehicle_types_supported=[],  # can't infer from Google Maps
            base_lat=lat,
            base_lng=lng,
            active=True,
            accepts_mobile_roadside=self._is_mobile_service(name, categories),
            rating=item.get("totalScore"),
            review_count=item.get("reviewsCount"),
            source="apify_google_maps",
            source_confidence=confidence,
            source_url=item.get("url"),
            hours_of_operation=hours,
            address=item.get("address"),
            website=item.get("website"),
            email=None,  # Google Maps doesn't expose email
        )

    def _normalize_phone(self, phone: str) -> Optional[str]:
        """Normalize phone to E.164-ish format."""
        digits = re.sub(r"[^\d+]", "", phone)
        if digits.startswith("+"):
            return digits[:16] if len(digits) >= 8 else None
        if len(digits) == 10:
            return f"+1{digits}"
        if len(digits) == 11 and digits.startswith("1"):
            return f"+{digits}"
        return digits[:16] if len(digits) >= 7 else None

    def _infer_service_types(self, name: str, categories: list[str]) -> list[str]:
        """Infer service types from business name and Google Maps categories."""
        combined = f"{name} {' '.join(categories)}".lower()
        types = set()

        for svc_type, keywords in SERVICE_TYPE_KEYWORDS.items():
            if any(kw in combined for kw in keywords):
                types.add(svc_type)

        # If no specific match, default to engine_trouble (general mechanic)
        if not types and any(
            kw in combined for kw in ("auto", "car", "vehicle", "motor")
        ):
            types.add("engine_trouble")

        return list(types)

    def _is_mobile_service(self, name: str, categories: list[str]) -> bool:
        """Guess whether this is a mobile service based on name/categories."""
        combined = f"{name} {' '.join(categories)}".lower()
        mobile_keywords = ["mobile", "roadside", "emergency", "24 hour", "on-site"]
        return any(kw in combined for kw in mobile_keywords)

    def _parse_hours(self, raw_hours: any) -> Optional[dict]:
        """Parse Apify's openingHours format into a clean dict."""
        if not raw_hours:
            return None
        if isinstance(raw_hours, dict):
            return raw_hours
        if isinstance(raw_hours, list):
            return {"schedule": raw_hours}
        return None

    def _compute_confidence(self, item: dict) -> float:
        """Compute a confidence score (0–1) based on data completeness.

        Higher confidence = more data points, more reviews, higher rating.
        """
        score = 0.0

        # Has a phone (required, so always true here)
        score += 0.15

        # Has address
        if item.get("address"):
            score += 0.10

        # Has website
        if item.get("website"):
            score += 0.10

        # Has opening hours
        if item.get("openingHours"):
            score += 0.10

        # Review count tiers
        reviews = item.get("reviewsCount", 0) or 0
        if reviews >= 50:
            score += 0.20
        elif reviews >= 20:
            score += 0.15
        elif reviews >= 5:
            score += 0.10
        elif reviews >= 1:
            score += 0.05

        # Rating
        rating = item.get("totalScore", 0) or 0
        if rating >= 4.5:
            score += 0.20
        elif rating >= 4.0:
            score += 0.15
        elif rating >= 3.5:
            score += 0.10
        elif rating >= 3.0:
            score += 0.05

        # Has categories (means Google has classified it)
        if item.get("categories"):
            score += 0.10

        # Has location coordinates (required, always true)
        score += 0.05

        return round(min(score, 1.0), 2)
