"""Export mechanics as State → City → Mechanics JSON.

Usage:
  DATABASE_URL="postgresql://..." uv run python3 scripts/export_mechanics_grouped.py
  OUTPUT=/tmp/mechanics_grouped.json uv run python3 scripts/export_mechanics_grouped.py
"""

from __future__ import annotations

import asyncio
import json
import os
import ssl
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


QUERY = """
SELECT
    id,
    company_name,
    service_types,
    vehicle_types_supported,
    address,
    city,
    state,
    phone,
    base_lat,
    base_lng,
    hours_of_operation,
    emergency_service,
    accepts_mobile_roadside,
    service_radius_miles,
    priority_score,
    rating,
    review_count,
    source,
    source_confidence,
    website,
    email
FROM mechanics
WHERE active = true
ORDER BY state, city, company_name
"""


def _async_url(url: str) -> str:
    if "sslmode=" in url:
        url = url.split("?")[0]
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _connect_args(url: str) -> dict:
    if "localhost" in url or "127.0.0.1" in url or "@postgres:" in url:
        return {}
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return {"ssl": context}


async def main() -> None:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL is required")

    output = Path(os.environ.get("OUTPUT", "data/mechanics_grouped.json"))
    engine = create_async_engine(_async_url(db_url), connect_args=_connect_args(db_url))
    grouped: dict[str, dict[str, list[dict]]] = {}

    async with engine.connect() as conn:
        result = await conn.execute(text(QUERY))
        for row in result.mappings():
            state = row["state"] or "UNKNOWN"
            city = row["city"] or "UNKNOWN"
            grouped.setdefault(state, {}).setdefault(city, []).append(
                {
                    "id": str(row["id"]),
                    "businessName": row["company_name"],
                    "services": row["service_types"] or [],
                    "vehicleTypes": row["vehicle_types_supported"] or [],
                    "address": row["address"],
                    "city": row["city"],
                    "state": row["state"],
                    "phone": row["phone"],
                    "latitude": row["base_lat"],
                    "longitude": row["base_lng"],
                    "hours": row["hours_of_operation"],
                    "emergencyService": row["emergency_service"],
                    "mobileService": row["accepts_mobile_roadside"],
                    "serviceRadiusMiles": row["service_radius_miles"],
                    "priorityScore": row["priority_score"],
                    "rating": float(row["rating"]) if row["rating"] is not None else None,
                    "reviewCount": row["review_count"],
                    "source": row["source"],
                    "sourceConfidence": row["source_confidence"],
                    "website": row["website"],
                    "email": row["email"],
                }
            )

    await engine.dispose()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(grouped, indent=2, default=str))
    print(f"Exported grouped mechanics to {output}")


if __name__ == "__main__":
    asyncio.run(main())
