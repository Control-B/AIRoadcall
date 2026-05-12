"""Import scraped Apify chain data into the vendor_locations table.

Reads ``backend/data/chains_raw.json`` (the Apify Google Maps export), normalizes
brand names, infers capability flags from the Google "categories" array, and
upserts each location into the ``vendor_locations`` table used by the dispatcher.

Idempotent — keyed on (brand_name, address, city, state). Safe to re-run.

Usage (from /root/AIRoadcall/backend):
    .venv/bin/python -m scripts.import_chain_locations
    .venv/bin/python -m scripts.import_chain_locations --file data/chains_raw.json --limit 500
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import and_, select

from app.core.database import async_session_factory
from app.models.major_vendor_location import MajorVendorLocation
from app.utils.location import STATE_NAME_TO_CODE


# ── brand normalization ───────────────────────────────────────────────
# Map raw title substrings → canonical brand_name + default priority.
BRAND_RULES: list[tuple[re.Pattern[str], str, int]] = [
    (re.compile(r"\blove'?s\b", re.I),                  "Love's Truck Care",          85),
    (re.compile(r"\bta\s+(truck|travel)", re.I),        "TA Truck Service",           90),
    (re.compile(r"\bta\s+express", re.I),               "TA Express",                 80),
    (re.compile(r"\bpetro\b", re.I),                    "Petro Stopping Centers",     90),
    (re.compile(r"\bpilot\b", re.I),                    "Pilot Travel Center",        80),
    (re.compile(r"\bflying\s*j\b", re.I),               "Flying J",                   80),
    (re.compile(r"\bspeedco\b", re.I),                  "Speedco",                    85),
    (re.compile(r"\brush\s*truck", re.I),               "Rush Truck Center",          88),
    (re.compile(r"\bfleetpride\b", re.I),               "FleetPride",                 85),
    (re.compile(r"\bsouthern\s+tire\s+mart\b", re.I),   "Southern Tire Mart",         85),
    (re.compile(r"\bboss\s+truck", re.I),               "Boss Truck Shops",           80),
    (re.compile(r"\bsapp\s+bros", re.I),                "Sapp Bros Travel Center",    78),
    (re.compile(r"\btruckpro\b", re.I),                 "TruckPro",                   80),
    (re.compile(r"\bbruckner'?s\b", re.I),              "Bruckner's Truck & Equipment", 80),
    (re.compile(r"\bvelocity\s+truck", re.I),           "Velocity Truck Centers",     80),
    (re.compile(r"\bnextran\b", re.I),                  "Nextran Truck Centers",      80),
    (re.compile(r"\bsnider\s+fleet", re.I),             "Snider Fleet Solutions",     80),
    (re.compile(r"\bbauer\s+built", re.I),              "Bauer Built Tire & Service", 78),
    (re.compile(r"\bring\s+power\b", re.I),             "Ring Power",                 75),
    (re.compile(r"\bryder\s+truck\s+maintenance", re.I), "Ryder Truck Maintenance",   75),
    (re.compile(r"\bryder\b", re.I),                    "Ryder",                      70),
    (re.compile(r"\bpenske\s+truck\s+(service|leasing)", re.I), "Penske Truck Service", 75),
    (re.compile(r"\bpenske\b", re.I),                   "Penske",                     70),
    (re.compile(r"\bgood\s*year\b", re.I),              "Goodyear Commercial",        75),
    (re.compile(r"\bboulevard\s+tire", re.I),           "Boulevard Tire Center",      75),
    (re.compile(r"\bp&k\s+midwest\b", re.I),            "P&K Midwest",                70),
]

# Brands we never want as a "major vendor" recommendation — retail/grocery/etc.
SKIP_BRANDS_RE = re.compile(
    r"\b(walmart|target|meijer|sam'?s\s+club|costco|home\s+depot|lowe'?s)\b",
    re.I,
)


def normalize_brand(title: str | None) -> tuple[str, int] | None:
    if not title:
        return None
    if SKIP_BRANDS_RE.search(title):
        return None
    for pattern, brand, priority in BRAND_RULES:
        if pattern.search(title):
            return brand, priority
    return None


# ── capability flags from google categories ──────────────────────────
def infer_capabilities(categories: list[str] | None, brand: str) -> dict[str, bool]:
    cats = " ".join(c.lower() for c in (categories or []))
    bl = brand.lower()
    has = lambda *words: any(w in cats for w in words)

    heavy = bool(
        has("truck repair", "truck dealer", "diesel engine", "trailer repair")
        or any(b in bl for b in (
            "truck", "fleetpride", "southern tire mart", "speedco", "rush",
            "boss truck", "ta truck", "petro", "love's truck", "snider", "bauer",
            "truckpro", "bruckner", "velocity", "nextran", "ring power",
        ))
    )
    return {
        "heavy_duty": heavy,
        "rv_service": "rv" in cats or "motorhome" in cats,
        "towing": has("towing", "tow truck"),
        "tire_service": has("tire") or "tire" in bl,
        "mobile_service": "mobile" in cats,
        "is_24_7": False,  # safest default; refined nightly
    }


# ── interstate / exit extraction ─────────────────────────────────────
INTERSTATE_RE = re.compile(r"\b(I[- ]?\d{1,3})\b", re.I)
EXIT_RE = re.compile(r"\b(?:exit|ex\.)\s*([0-9A-Za-z]+)", re.I)


def extract_corridor(address: str | None, neighborhood: str | None) -> tuple[str | None, str | None]:
    blob = " ".join(p for p in (address, neighborhood) if p)
    if not blob:
        return None, None
    interstate = None
    exit_no = None
    m = INTERSTATE_RE.search(blob)
    if m:
        interstate = m.group(1).upper().replace(" ", "-")
        if "-" not in interstate:
            interstate = "I-" + interstate[1:]
    em = EXIT_RE.search(blob)
    if em:
        exit_no = em.group(1)
    return interstate, exit_no


# ── state normalization ──────────────────────────────────────────────
def normalize_state(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip()
    if len(v) == 2:
        return v.upper()
    return STATE_NAME_TO_CODE.get(v.lower())


# ── main row builder ─────────────────────────────────────────────────
def build_row(item: dict[str, Any]) -> dict[str, Any] | None:
    if item.get("permanentlyClosed") or item.get("temporarilyClosed"):
        return None
    brand_info = normalize_brand(item.get("title"))
    if not brand_info:
        return None
    brand_name, priority = brand_info

    state_code = normalize_state(item.get("state"))
    if not state_code:
        return None

    loc = item.get("location") or {}
    lat = loc.get("lat") if isinstance(loc, dict) else None
    lng = loc.get("lng") if isinstance(loc, dict) else None

    phone = item.get("phoneUnformatted") or item.get("phone")
    address = item.get("address") or item.get("street")
    interstate, exit_no = extract_corridor(address, item.get("neighborhood"))
    caps = infer_capabilities(item.get("categories"), brand_name)

    return {
        "brand_name": brand_name,
        "location_name": item.get("title"),
        "phone": phone,
        "address": address,
        "city": item.get("city"),
        "state": state_code,
        "zip_code": item.get("postalCode"),
        "latitude": lat,
        "longitude": lng,
        "interstate": interstate,
        "exit_number": exit_no,
        "services": list(item.get("categories") or [])[:8] or None,
        "heavy_duty": caps["heavy_duty"],
        "rv_service": caps["rv_service"],
        "towing": caps["towing"],
        "tire_service": caps["tire_service"],
        "mobile_service": caps["mobile_service"],
        "is_24_7": caps["is_24_7"],
        "verified": True,
        "active": True,
        "source": "apify_google_maps",
        "priority_score": priority,
    }


async def upsert_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    inserted = 0
    updated = 0
    skipped = 0
    async with async_session_factory() as session:
        for row in rows:
            if not row.get("brand_name") or not row.get("city") or not row.get("state"):
                skipped += 1
                continue
            stmt = select(MajorVendorLocation).where(
                and_(
                    MajorVendorLocation.brand_name == row["brand_name"],
                    MajorVendorLocation.city == row["city"],
                    MajorVendorLocation.state == row["state"],
                    MajorVendorLocation.address == row["address"],
                )
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                for key, value in row.items():
                    if hasattr(existing, key) and value is not None:
                        setattr(existing, key, value)
                updated += 1
            else:
                session.add(MajorVendorLocation(**{
                    k: v for k, v in row.items() if hasattr(MajorVendorLocation, k)
                }))
                inserted += 1
            if (inserted + updated) % 200 == 0:
                await session.commit()
        await session.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


async def main(file_path: Path, limit: int | None) -> None:
    raw = json.loads(file_path.read_text())
    if not isinstance(raw, list):
        raise SystemExit(f"Expected JSON array in {file_path}")
    print(f"loaded {len(raw)} raw chain entries from {file_path}")

    rows: list[dict[str, Any]] = []
    for item in raw:
        row = build_row(item)
        if row is not None:
            rows.append(row)
        if limit and len(rows) >= limit:
            break

    # brand summary
    from collections import Counter
    summary = Counter(r["brand_name"] for r in rows)
    print(f"normalized {len(rows)} chain rows across {len(summary)} brands:")
    for brand, count in summary.most_common():
        print(f"  {brand:32s} {count:>5d}")

    print("upserting into vendor_locations…")
    result = await upsert_rows(rows)
    print(f"done — inserted={result['inserted']} updated={result['updated']} skipped={result['skipped']}")


def cli() -> None:
    parser = argparse.ArgumentParser(description="Import Apify chain scrape into vendor_locations")
    parser.add_argument("--file", default="data/chains_raw.json", help="Path to Apify JSON export")
    parser.add_argument("--limit", type=int, default=None, help="Optional cap on rows for testing")
    args = parser.parse_args()
    asyncio.run(main(Path(args.file), args.limit))


if __name__ == "__main__":
    cli()
