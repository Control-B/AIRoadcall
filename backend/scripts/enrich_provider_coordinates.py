#!/usr/bin/env python3
"""Geocode mechanics/providers missing usable coordinates.

Usage:
  cd backend
  .venv/bin/python scripts/enrich_provider_coordinates.py --limit 250
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import or_, select  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.models.mechanic import Mechanic  # noqa: E402
from app.services.geocoding_service import GeocodingService  # noqa: E402


async def run(limit: int, dry_run: bool) -> int:
    updated = 0
    skipped = 0
    async with async_session_factory() as db:
        result = await db.execute(
            select(Mechanic)
            .where(
                Mechanic.active == True,
                or_(Mechanic.base_lat.is_(None), Mechanic.base_lng.is_(None), Mechanic.base_lat == 0, Mechanic.base_lng == 0),
            )
            .limit(limit)
        )
        providers = result.scalars().all()
        for provider in providers:
            location_text = ", ".join(
                part
                for part in [provider.address, provider.city, provider.state, getattr(provider, "zip_code", None)]
                if part
            )
            if not location_text:
                skipped += 1
                continue
            geocoded = await GeocodingService.geocode_location(location_text)
            if not geocoded:
                skipped += 1
                continue
            provider.base_lat = geocoded["latitude"]
            provider.base_lng = geocoded["longitude"]
            provider.city = provider.city or geocoded.get("city")
            provider.state = provider.state or geocoded.get("state")
            enrichment = provider.enrichment_data or {}
            enrichment["geocoding"] = {
                "normalized_location": geocoded.get("normalized_location"),
                "confidence": geocoded.get("confidence"),
                "source": "mapbox",
            }
            provider.enrichment_data = enrichment
            updated += 1
            print(f"geocoded {provider.company_name}: {provider.base_lat:.5f},{provider.base_lng:.5f}")
        if dry_run:
            await db.rollback()
        else:
            await db.commit()
    print(f"updated={updated} skipped={skipped} dry_run={dry_run}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Geocode mechanics/providers missing coordinates.")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return asyncio.run(run(args.limit, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
