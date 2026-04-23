"""
Import scraped mechanic data into the PostgreSQL mechanics table.

Reads from data/heavy_duty_raw.json (46,460 records with full lat/lng, city, state).
Deduplicates by phone. Skips permanently/temporarily closed businesses.
Produces ~35,000 unique active mechanics across all 50 US states.

Usage
-----
  # From the backend/ directory:
  DATABASE_URL="postgresql://user:pass@host:port/dbname" uv run python3 scripts/import_mechanics.py

  # Dry-run (preview only, no DB writes):
  DRY_RUN=1 DATABASE_URL=any uv run python3 scripts/import_mechanics.py

  # Export the DO managed DB URL then run:
  export DATABASE_URL="<your DO db connection string>"
  uv run python3 scripts/import_mechanics.py
"""

from __future__ import annotations

import asyncio
import json
import os
import ssl
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── State name → abbreviation map ───────────────────────────────────────────
STATE_ABBR: dict[str, str] = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "puerto rico": "PR", "guam": "GU",
}


def _state_to_abbr(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 2 and raw.upper() in STATE_ABBR.values():
        return raw.upper()
    return STATE_ABBR.get(raw.lower())


def _normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return None


# ── Classifiers ──────────────────────────────────────────────────────────────

SERVICE_KEYWORDS: list[tuple[list[str], str]] = [
    (["flat tire", "tire repair", "tire service", "tyre"], "flat_tire"),
    (["tow", "wrecker", "towing service"], "tow_needed"),
    (["battery", "jump start", "jumpstart", "jump-start"], "dead_battery"),
    (["lockout", "locksmith", "lock out", "locked out"], "lockout"),
    (["fuel", "gas delivery", "fuel delivery"], "fuel_delivery"),
    (["engine", "diesel repair", "diesel engine", "mechanic", "repair shop",
      "auto repair", "truck repair", "transmission"], "engine_trouble"),
    (["overheating", "radiator", "coolant", "cooling"], "overheating"),
]

VEHICLE_KEYWORDS: list[tuple[list[str], str]] = [
    (["heavy duty", "semi", "18 wheel", "18-wheel", "big rig", "tractor trailer",
      "tractor-trailer", "commercial truck", "heavy truck", "heavy equip"], "heavy_duty"),
    (["diesel"], "diesel"),
    (["trailer", "flatbed", "reefer"], "trailer"),
    (["rv", "motorhome", "motor home", "recreational vehicle"], "rv"),
    (["fleet", "fleet service"], "fleet"),
]


def classify(name: str, categories: list[str]) -> tuple[list[str], list[str]]:
    text = f"{name} {' '.join(categories)}".lower()
    st = [s for kws, s in SERVICE_KEYWORDS if any(kw in text for kw in kws)]
    vt = [v for kws, v in VEHICLE_KEYWORDS if any(kw in text for kw in kws)]
    if not st:
        st = ["engine_trouble"]
    if not vt:
        vt = ["commercial"]
    return list(dict.fromkeys(st)), list(dict.fromkeys(vt))  # preserve order, dedupe


def is_roadside(name: str, categories: list[str], hours: list[dict]) -> bool:
    text = f"{name} {' '.join(categories)}".lower()
    if any(kw in text for kw in ("mobile", "roadside", "emergency", "24 hour", "24/7",
                                  "24 hr", "breakdown", "field service", "road service")):
        return True
    if hours and sum(1 for h in hours if "open 24 hours" in (h.get("hours") or "").lower()) >= 5:
        return True
    return False


def source_confidence(item: dict, roadside: bool) -> float:
    score = 0.5
    if item.get("totalScore"):
        score += 0.1
    if (item.get("reviewsCount") or 0) > 10:
        score += 0.1
    if item.get("website"):
        score += 0.1
    if item.get("openingHours"):
        score += 0.1
    if roadside:
        score += 0.1
    return round(min(score, 1.0), 2)


# ── Parse raw JSON → mechanic dicts ─────────────────────────────────────────

def parse_raw(path: Path) -> list[dict]:
    print(f"Loading {path} ...")
    with open(path) as f:
        items = json.load(f)
    print(f"  {len(items):,} raw records")

    seen_phones: set[str] = set()
    mechanics: list[dict] = []
    skipped = {"no_phone": 0, "bad_coords": 0, "closed": 0, "dupe": 0, "foreign": 0}

    for item in items:
        if item.get("permanentlyClosed") or item.get("temporarilyClosed"):
            skipped["closed"] += 1
            continue

        raw_phone = item.get("phone") or item.get("phoneUnformatted") or ""
        phone = _normalize_phone(raw_phone)
        if not phone:
            skipped["no_phone"] += 1
            continue
        if not phone.startswith("+1"):
            skipped["foreign"] += 1
            continue

        location = item.get("location") or {}
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            skipped["bad_coords"] += 1
            continue

        if phone in seen_phones:
            skipped["dupe"] += 1
            continue
        seen_phones.add(phone)

        name = (item.get("title") or item.get("name") or "").strip() or "Mechanic"
        categories = item.get("categories") or []
        hours = item.get("openingHours") or item.get("hours") or []
        state_abbr = _state_to_abbr(item.get("state"))
        city = (item.get("city") or "").strip() or None

        if state_abbr is None:
            skipped["foreign"] += 1
            continue

        st, vt = classify(name, categories)
        roadside = is_roadside(name, categories, hours)
        conf = source_confidence(item, roadside)

        mechanics.append({
            "id": str(uuid.uuid4()),
            "company_name": name,
            "contact_name": name,
            "phone": phone,
            "service_types": st,
            "vehicle_types_supported": vt,
            "base_lat": float(lat),
            "base_lng": float(lng),
            "active": True,
            "accepts_mobile_roadside": roadside,
            "rating": item.get("totalScore") or item.get("rating"),
            "review_count": item.get("reviewsCount") or item.get("reviews") or 0,
            "source": "apify_google_maps",
            "source_confidence": conf,
            "source_url": item.get("url") or "",
            "hours_of_operation": hours or None,
            "address": item.get("address") or "",
            "city": city,
            "state": state_abbr,
            "website": item.get("website") or "",
            "total_dispatches": 0,
            "successful_dispatches": 0,
        })

    print(f"  Parsed {len(mechanics):,} valid mechanics")
    print(f"  Skipped -> {skipped}")
    return mechanics


# ── Database upsert ──────────────────────────────────────────────────────────

UPSERT_SQL = """
    INSERT INTO mechanics (
        id, company_name, contact_name, phone,
        service_types, vehicle_types_supported,
        base_lat, base_lng, active, accepts_mobile_roadside,
        rating, review_count,
        source, source_confidence, source_url,
        hours_of_operation, address, city, state, website,
        total_dispatches, successful_dispatches,
        created_at, updated_at
    ) VALUES (
        :id, :company_name, :contact_name, :phone,
        :service_types::jsonb, :vehicle_types_supported::jsonb,
        :base_lat, :base_lng, :active, :accepts_mobile_roadside,
        :rating, :review_count,
        :source, :source_confidence, :source_url,
        :hours_of_operation::jsonb, :address, :city, :state, :website,
        :total_dispatches, :successful_dispatches,
        :now, :now
    )
    ON CONFLICT (phone) DO UPDATE SET
        company_name            = EXCLUDED.company_name,
        service_types           = EXCLUDED.service_types,
        vehicle_types_supported = EXCLUDED.vehicle_types_supported,
        base_lat                = EXCLUDED.base_lat,
        base_lng                = EXCLUDED.base_lng,
        city                    = EXCLUDED.city,
        state                   = EXCLUDED.state,
        rating                  = EXCLUDED.rating,
        review_count            = EXCLUDED.review_count,
        source_confidence       = EXCLUDED.source_confidence,
        source_url              = EXCLUDED.source_url,
        hours_of_operation      = EXCLUDED.hours_of_operation,
        address                 = EXCLUDED.address,
        website                 = EXCLUDED.website,
        updated_at              = EXCLUDED.updated_at
    RETURNING (xmax = 0) AS is_insert
"""


async def import_to_db(mechanics: list[dict]) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import text

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set.")
        sys.exit(1)

    if "sslmode=" in db_url:
        db_url = db_url.split("?")[0]
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

    connect_args: dict = {}
    if "localhost" not in db_url and "127.0.0.1" not in db_url:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ctx

    display = db_url.split("@")[-1] if "@" in db_url else db_url
    print(f"\nConnecting to: ...@{display}")

    engine = create_async_engine(db_url, pool_pre_ping=True, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        check = await session.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'mechanics')"
        ))
        if not check.scalar():
            print("\n  Table 'mechanics' does not exist!")
            print("  Run migrations first: DATABASE_URL=... uv run alembic upgrade head")
            await engine.dispose()
            return

        now = datetime.now(timezone.utc)
        inserted = updated = errors = 0
        BATCH = 500

        print(f"\nInserting {len(mechanics):,} mechanics in batches of {BATCH}...")

        for i in range(0, len(mechanics), BATCH):
            batch = mechanics[i: i + BATCH]
            for m in batch:
                try:
                    result = await session.execute(text(UPSERT_SQL), {
                        **m,
                        "service_types": json.dumps(m["service_types"]),
                        "vehicle_types_supported": json.dumps(m["vehicle_types_supported"]),
                        "hours_of_operation": json.dumps(m["hours_of_operation"]) if m["hours_of_operation"] else None,
                        "now": now,
                    })
                    row = result.fetchone()
                    if row and row.is_insert:
                        inserted += 1
                    else:
                        updated += 1
                except Exception as e:
                    errors += 1
                    if errors <= 10:
                        print(f"  ERROR on {m['phone']}: {e}")

            await session.commit()
            done = min(i + BATCH, len(mechanics))
            print(f"  {done:>6,}/{len(mechanics):,}  ({done/len(mechanics)*100:.0f}%)  "
                  f"inserted={inserted:,}  updated={updated:,}  errors={errors}", end="\r")

        print()

    await engine.dispose()

    print()
    print("=" * 60)
    print("IMPORT COMPLETE")
    print("=" * 60)
    print(f"  Inserted : {inserted:,}")
    print(f"  Updated  : {updated:,}")
    if errors:
        print(f"  Errors   : {errors:,}")
    print(f"  Total    : {inserted + updated + errors:,}")


# ── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    base = Path(__file__).resolve().parent.parent / "data"
    raw_path = base / "heavy_duty_raw.json"

    if not raw_path.exists():
        print(f"ERROR: {raw_path} not found.")
        sys.exit(1)

    mechanics = parse_raw(raw_path)

    from collections import Counter
    state_counts = Counter(m["state"] for m in mechanics if m["state"])
    print()
    print("=" * 60)
    print("PARSED DATA SUMMARY")
    print("=" * 60)
    print(f"  Total unique mechanics : {len(mechanics):,}")
    print(f"  Mobile / roadside      : {sum(1 for m in mechanics if m['accepts_mobile_roadside']):,}")
    print(f"  With rating            : {sum(1 for m in mechanics if m['rating']):,}")
    print(f"  States covered         : {len(state_counts)}")
    top5 = ', '.join(f"{s}={n:,}" for s, n in state_counts.most_common(5))
    print(f"  Top states             : {top5}")
    print()

    dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    if dry_run:
        print("DRY RUN -- skipping database insert.\n")
        print("Sample records:")
        for m in mechanics[:3]:
            print(f"  {m['company_name']}")
            print(f"    phone={m['phone']}  coords=({m['base_lat']}, {m['base_lng']})")
            print(f"    city={m['city']}, state={m['state']}")
            print(f"    vt={m['vehicle_types_supported']}  st={m['service_types']}")
            print(f"    roadside={m['accepts_mobile_roadside']}  rating={m['rating']}")
            print()
        return

    await import_to_db(mechanics)


if __name__ == "__main__":
    asyncio.run(main())
