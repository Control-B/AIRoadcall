"""
Import scraped heavy-duty mechanics into the database.

Usage:
  # Set DATABASE_URL in .env first (Render External URL)
  cd backend
  source ../.env && export DATABASE_URL
  uv run python3 scripts/import_mechanics.py

  # Or with explicit URL:
  DATABASE_URL=postgresql://user:pass@host/db uv run python3 scripts/import_mechanics.py

  # Dry-run (no DB writes, just preview):
  DRY_RUN=1 uv run python3 scripts/import_mechanics.py
"""

import asyncio
import json
import os
import ssl
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Parse raw data into mechanic dicts ──────────────────────
def parse_raw_mechanics(raw_path: str = "data/heavy_duty_raw.json") -> list[dict]:
    """Parse raw Apify Google Maps data into mechanic records."""
    with open(raw_path) as f:
        items = json.load(f)

    print(f"Loaded {len(items)} raw results from {raw_path}")

    seen_phones: set[str] = set()
    mechanics: list[dict] = []

    for item in items:
        phone = item.get("phone") or item.get("phoneUnformatted")
        name = item.get("title") or item.get("name")
        location = item.get("location") or {}
        lat = location.get("lat")
        lng = location.get("lng")

        # Skip if missing critical fields
        if not phone or not name or lat is None or lng is None:
            continue

        # Normalize phone
        digits = "".join(c for c in phone if c.isdigit() or c == "+")
        if not digits.startswith("+"):
            if len(digits) == 10:
                digits = f"+1{digits}"
            elif len(digits) == 11 and digits.startswith("1"):
                digits = f"+{digits}"

        # Deduplicate by phone
        if digits in seen_phones:
            continue
        seen_phones.add(digits)

        # Categorize
        cats = item.get("categories", []) or []
        combined = f"{name} {' '.join(cats)}".lower()

        # Vehicle types
        vt = []
        if any(k in combined for k in ("heavy duty", "semi", "18 wheeler", "commercial truck", "heavy equip")):
            vt.append("heavy_duty")
        if any(k in combined for k in ("diesel", "fleet")):
            vt.append("diesel")
        if any(k in combined for k in ("trailer", "flatbed")):
            vt.append("trailer")
        if not vt:
            vt.append("commercial")

        # Service types
        st = []
        if any(k in combined for k in ("tire", "flat")):
            st.append("flat_tire")
        if any(k in combined for k in ("tow", "wrecker")):
            st.append("tow_needed")
        if any(k in combined for k in ("battery", "jump")):
            st.append("dead_battery")
        if any(k in combined for k in ("engine", "repair", "mechanic", "diesel")):
            st.append("engine_trouble")
        if not st:
            st.append("engine_trouble")

        # Roadside detection
        is_roadside = any(
            k in combined
            for k in ("mobile", "roadside", "emergency", "24 hour", "24/7", "breakdown", "field service")
        )

        # Confidence score based on data completeness
        confidence = 0.5
        if item.get("totalScore"):
            confidence += 0.1
        if (item.get("reviewsCount") or 0) > 10:
            confidence += 0.1
        if item.get("website"):
            confidence += 0.1
        if item.get("openingHours"):
            confidence += 0.1
        if is_roadside:
            confidence += 0.1
        confidence = min(confidence, 1.0)

        mechanics.append({
            "id": str(uuid.uuid4()),
            "company_name": name.strip(),
            "contact_name": name.strip(),  # Same as company for scraped data
            "phone": digits,
            "service_types": st,
            "vehicle_types_supported": vt,
            "base_lat": lat,
            "base_lng": lng,
            "active": True,
            "accepts_mobile_roadside": is_roadside,
            "rating": item.get("totalScore"),
            "review_count": item.get("reviewsCount", 0),
            "source": "apify_google_maps",
            "source_confidence": round(confidence, 2),
            "source_url": item.get("url", ""),
            "hours_of_operation": item.get("openingHours"),
            "address": item.get("address", ""),
            "website": item.get("website", ""),
            "total_dispatches": 0,
            "successful_dispatches": 0,
        })

    return mechanics


# ── Database insert ─────────────────────────────────────────
async def import_to_db(mechanics: list[dict]) -> None:
    """Insert or update mechanics in the database."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import text

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set. Export it first.")
        sys.exit(1)

    # Strip sslmode param — asyncpg handles SSL via connect_args
    if "sslmode=" in db_url:
        db_url = db_url.split("?")[0]

    # Convert to asyncpg driver
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    # SSL for managed DB (non-localhost)
    connect_args = {}
    if "localhost" not in db_url and "127.0.0.1" not in db_url:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context

    # Mask password for display
    display_url = db_url.split("@")[-1] if "@" in db_url else db_url
    print(f"Connecting to: ...@{display_url}")

    engine = create_async_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        # Check if table exists
        result = await session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'mechanics')"
        ))
        table_exists = result.scalar()

        if not table_exists:
            print("\n⚠️  Table 'mechanics' does not exist yet!")
            print("   Run migrations first:")
            print("   DATABASE_URL=... uv run alembic upgrade head")
            print("\n   Or create tables directly:")
            create = input("   Create tables now? [y/N]: ").strip().lower()
            if create == "y":
                from app.core.database import Base
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                print("   ✅ Tables created!")
            else:
                await engine.dispose()
                return

        # Upsert mechanics (ON CONFLICT by phone)
        inserted = 0
        updated = 0
        errors = 0

        upsert_sql = text("""
            INSERT INTO mechanics (
                id, company_name, contact_name, phone,
                service_types, vehicle_types_supported,
                base_lat, base_lng, active, accepts_mobile_roadside,
                rating, review_count, source, source_confidence, source_url,
                hours_of_operation, address, website,
                total_dispatches, successful_dispatches,
                created_at, updated_at
            ) VALUES (
                :id, :company_name, :contact_name, :phone,
                :service_types, :vehicle_types_supported,
                :base_lat, :base_lng, :active, :accepts_mobile_roadside,
                :rating, :review_count, :source, :source_confidence, :source_url,
                :hours_of_operation, :address, :website,
                :total_dispatches, :successful_dispatches,
                :now, :now
            )
            ON CONFLICT (phone) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                service_types = EXCLUDED.service_types,
                vehicle_types_supported = EXCLUDED.vehicle_types_supported,
                base_lat = EXCLUDED.base_lat,
                base_lng = EXCLUDED.base_lng,
                rating = EXCLUDED.rating,
                review_count = EXCLUDED.review_count,
                source_confidence = EXCLUDED.source_confidence,
                source_url = EXCLUDED.source_url,
                hours_of_operation = EXCLUDED.hours_of_operation,
                address = EXCLUDED.address,
                website = EXCLUDED.website,
                updated_at = EXCLUDED.updated_at
            RETURNING (xmax = 0) AS is_insert
        """)

        now = datetime.now(timezone.utc)

        for mech in mechanics:
            try:
                result = await session.execute(upsert_sql, {
                    **mech,
                    "service_types": json.dumps(mech["service_types"]),
                    "vehicle_types_supported": json.dumps(mech["vehicle_types_supported"]),
                    "hours_of_operation": json.dumps(mech["hours_of_operation"]) if mech["hours_of_operation"] else None,
                    "now": now,
                })
                row = result.fetchone()
                if row and row.is_insert:
                    inserted += 1
                else:
                    updated += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  ⚠️ Error on {mech['phone']}: {e}")

        await session.commit()

    await engine.dispose()

    print()
    print("=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"  ✅ Inserted: {inserted}")
    print(f"  🔄 Updated:  {updated}")
    if errors:
        print(f"  ❌ Errors:   {errors}")
    print(f"  📊 Total:    {inserted + updated + errors}")


# ── Main ────────────────────────────────────────────────────
async def main():
    raw_path = Path(__file__).parent.parent / "data" / "heavy_duty_raw.json"

    if not raw_path.exists():
        print(f"ERROR: {raw_path} not found. Run the scrape first.")
        sys.exit(1)

    mechanics = parse_raw_mechanics(str(raw_path))

    print()
    print("=" * 60)
    print("PARSED DATA SUMMARY")
    print("=" * 60)
    print(f"  Total unique mechanics: {len(mechanics)}")
    print(f"  Roadside/mobile:        {len([m for m in mechanics if m['accepts_mobile_roadside']])}")
    print(f"  With coordinates:       {len([m for m in mechanics if m['base_lat']])}")
    print(f"  With rating:            {len([m for m in mechanics if m['rating']])}")
    print()

    dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

    if dry_run:
        print("DRY RUN — skipping database insert")
        print("\nSample records:")
        for m in mechanics[:3]:
            print(f"  📍 {m['company_name']}")
            print(f"     {m['phone']} | {m['address']}")
            print(f"     lat={m['base_lat']}, lng={m['base_lng']}")
            print(f"     types={m['vehicle_types_supported']} services={m['service_types']}")
            print(f"     roadside={m['accepts_mobile_roadside']} rating={m['rating']}")
            print()
        return

    await import_to_db(mechanics)


if __name__ == "__main__":
    asyncio.run(main())
