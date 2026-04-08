"""Tavily Service — Real-time mechanic data enrichment and verification.

Uses Tavily's AI search API to verify and enrich mechanic records:
  - Is the business still operating?
  - Updated phone number, website, hours?
  - Any recent reviews or red flags?
  - Additional service details

Two usage patterns:
  1. BATCH: Periodic enrichment of stale records (cron / manual trigger)
  2. PRE-DISPATCH: Quick verification before calling a mechanic

Results are cached in the mechanic's `enrichment_data` JSON field with
a `last_enriched_at` timestamp. Stale = older than 7 days by default.
"""
import uuid
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.mechanic import Mechanic
from app.schemas.mechanic import EnrichResultView

logger = get_logger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"


class TavilyService:
    """Verify and enrich mechanic records using Tavily AI search."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.TAVILY_API_KEY

    async def enrich_mechanic(
        self, db: AsyncSession, mechanic: Mechanic
    ) -> EnrichResultView:
        """Run a Tavily search to verify/enrich a single mechanic.

        Searches for the business by name + location, extracts relevant
        info, and updates the DB record.
        """
        if not self.api_key:
            return EnrichResultView(
                mechanic_id=str(mechanic.id),
                company_name=mechanic.company_name,
                enriched=False,
                error="TAVILY_API_KEY not configured",
            )

        # Build a targeted search query
        query = self._build_search_query(mechanic)
        updates = {}

        try:
            search_results = await self._search(query)
            updates = self._extract_enrichment(mechanic, search_results)

            # Apply updates to the mechanic record
            if updates.get("still_operating") is False:
                mechanic.active = False
                logger.warning(
                    f"Mechanic {mechanic.company_name} appears to be closed — deactivated"
                )

            if updates.get("phone") and updates["phone"] != mechanic.phone:
                updates["phone_changed"] = True
                # Don't auto-update phone (it's our unique key), just flag it

            if updates.get("website"):
                mechanic.website = updates["website"]
            if updates.get("email"):
                mechanic.email = updates["email"]
            if updates.get("hours_of_operation"):
                mechanic.hours_of_operation = updates["hours_of_operation"]

            # Bump confidence slightly if we got verification data
            if mechanic.source_confidence and updates.get("verified"):
                mechanic.source_confidence = min(
                    1.0, mechanic.source_confidence + 0.05
                )
            elif mechanic.source_confidence and not updates.get("verified"):
                mechanic.source_confidence = max(
                    0.0, mechanic.source_confidence - 0.1
                )

            # Store the raw enrichment data
            mechanic.enrichment_data = {
                "tavily_results": search_results.get("results", [])[:3],
                "query": query,
                "extracted": updates,
                "searched_at": datetime.now(timezone.utc).isoformat(),
            }
            mechanic.last_enriched_at = datetime.now(timezone.utc)
            await db.flush()

            return EnrichResultView(
                mechanic_id=str(mechanic.id),
                company_name=mechanic.company_name,
                enriched=True,
                updates=updates,
            )

        except Exception as e:
            logger.error(
                f"Tavily enrichment failed for {mechanic.company_name}: {e}"
            )
            return EnrichResultView(
                mechanic_id=str(mechanic.id),
                company_name=mechanic.company_name,
                enriched=False,
                error=str(e),
            )

    async def enrich_stale_mechanics(
        self,
        db: AsyncSession,
        max_age_hours: int = 168,  # 7 days
        limit: int = 20,
    ) -> list[EnrichResultView]:
        """Find and enrich mechanics with stale or missing enrichment data."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        result = await db.execute(
            select(Mechanic)
            .where(
                (Mechanic.active == True)  # noqa: E712
                & (
                    (Mechanic.last_enriched_at == None)  # noqa: E711
                    | (Mechanic.last_enriched_at < cutoff)
                )
            )
            .order_by(Mechanic.last_enriched_at.asc().nulls_first())
            .limit(limit)
        )
        mechanics = result.scalars().all()

        logger.info(f"Enriching {len(mechanics)} stale mechanic records")

        results = []
        for m in mechanics:
            r = await self.enrich_mechanic(db, m)
            results.append(r)

        return results

    async def enrich_by_ids(
        self, db: AsyncSession, mechanic_ids: list[str]
    ) -> list[EnrichResultView]:
        """Enrich specific mechanics by their IDs."""
        results = []
        for mid in mechanic_ids:
            result = await db.execute(
                select(Mechanic).where(Mechanic.id == uuid.UUID(mid))
            )
            mechanic = result.scalar_one_or_none()
            if mechanic:
                r = await self.enrich_mechanic(db, mechanic)
                results.append(r)
            else:
                results.append(
                    EnrichResultView(
                        mechanic_id=mid,
                        company_name="unknown",
                        enriched=False,
                        error="Mechanic not found",
                    )
                )
        return results

    async def pre_dispatch_check(
        self, db: AsyncSession, mechanic: Mechanic
    ) -> dict:
        """Quick verification before dispatching to a mechanic.

        Returns a dict with:
          - verified: bool
          - confidence_adjustment: float
          - warnings: list[str]
        """
        warnings = []

        # If recently enriched, use cached data
        if mechanic.last_enriched_at:
            age = datetime.now(timezone.utc) - mechanic.last_enriched_at
            if age < timedelta(hours=24):
                enrichment = mechanic.enrichment_data or {}
                extracted = enrichment.get("extracted", {})
                if extracted.get("still_operating") is False:
                    warnings.append("Business may be permanently closed")
                return {
                    "verified": extracted.get("verified", True),
                    "confidence_adjustment": 0.0,
                    "warnings": warnings,
                    "cached": True,
                }

        # Do a fresh check
        result = await self.enrich_mechanic(db, mechanic)
        if not result.enriched:
            warnings.append(f"Could not verify: {result.error}")
            return {
                "verified": False,
                "confidence_adjustment": -0.1,
                "warnings": warnings,
                "cached": False,
            }

        if result.updates.get("still_operating") is False:
            warnings.append("Business appears to be permanently closed")
            return {
                "verified": False,
                "confidence_adjustment": -0.5,
                "warnings": warnings,
                "cached": False,
            }

        return {
            "verified": True,
            "confidence_adjustment": 0.05,
            "warnings": warnings,
            "cached": False,
        }

    async def _search(self, query: str) -> dict:
        """Execute a Tavily search."""
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "include_answer": True,
            "max_results": 5,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(TAVILY_API_URL, json=payload)
            resp.raise_for_status()
            return resp.json()

    def _build_search_query(self, mechanic: Mechanic) -> str:
        """Build a targeted search query for the mechanic."""
        parts = [mechanic.company_name]
        if mechanic.address:
            parts.append(mechanic.address)
        elif mechanic.base_lat and mechanic.base_lng:
            # Include approximate location
            parts.append(f"near {mechanic.base_lat:.2f},{mechanic.base_lng:.2f}")
        parts.append("phone hours open reviews")
        return " ".join(parts)

    def _extract_enrichment(self, mechanic: Mechanic, search_data: dict) -> dict:
        """Extract structured enrichment data from Tavily search results.

        Looks at the AI answer and individual results for:
        - Business status (open/closed)
        - Updated contact info
        - Service hours
        - Review sentiment
        """
        updates = {}
        answer = (search_data.get("answer") or "").lower()
        results = search_data.get("results", [])

        # Check if business appears to still be operating
        closed_signals = [
            "permanently closed",
            "no longer in business",
            "out of business",
            "closed down",
            "has closed",
            "was closed",
        ]
        if any(signal in answer for signal in closed_signals):
            updates["still_operating"] = False
            updates["verified"] = True
        else:
            updates["still_operating"] = True
            updates["verified"] = len(results) > 0

        # Try to find website from results
        for r in results:
            url = r.get("url", "")
            # Skip aggregator sites
            if any(
                agg in url
                for agg in ("yelp.com", "google.com", "facebook.com", "yellowpages")
            ):
                continue
            if url and not mechanic.website:
                updates["website"] = url
                break

        # Extract any mentions of hours
        for r in results:
            content = (r.get("content") or "").lower()
            if "24 hour" in content or "24/7" in content:
                updates["hours_of_operation"] = {"note": "24/7 service"}
                break
            if "hours" in content and ("am" in content or "pm" in content):
                # Store the raw mention — better than nothing
                snippet = r.get("content", "")[:200]
                updates["hours_snippet"] = snippet
                break

        return updates
