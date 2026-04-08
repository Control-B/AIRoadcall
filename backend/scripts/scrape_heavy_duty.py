"""Standalone script to scrape heavy-duty mechanics across US metros via Apify.

Usage:
  cd backend
  APIFY_API_TOKEN=apify_xxx python scripts/scrape_heavy_duty.py

This script:
  1. Fires off an Apify Google Maps scrape for heavy-duty/commercial mechanics
  2. Polls until complete
  3. Saves raw JSON results to data/heavy_duty_raw.json
  4. Parses and prints a summary of what was found
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx

# ── Config ───────────────────────────────────────────────

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "nwua9Gu5YrADL7ZDj"  # compass/crawler-google-places (Google Maps Scraper)

# Heavy-duty focused search queries
SEARCH_QUERIES = [
    "heavy duty truck repair",
    "heavy duty mobile mechanic",
    "semi truck roadside assistance",
    "commercial truck repair",
    "diesel mechanic near me",
    "18 wheeler roadside repair",
    "heavy duty towing service",
    "truck tire repair roadside",
    "fleet roadside assistance",
    "commercial vehicle breakdown service",
    "heavy equipment mechanic mobile",
    "trailer repair mobile service",
]

# Major US metro areas for broad coverage
US_METROS = [
    "Dallas, TX",
    "Houston, TX",
    "Atlanta, GA",
    "Chicago, IL",
    "Los Angeles, CA",
    "Phoenix, AZ",
    "Denver, CO",
    "Nashville, TN",
    "Charlotte, NC",
    "Indianapolis, IN",
    "Jacksonville, FL",
    "Memphis, TN",
    "Louisville, KY",
    "Columbus, OH",
    "Kansas City, MO",
    "St. Louis, MO",
    "San Antonio, TX",
    "Oklahoma City, OK",
    "Albuquerque, NM",
    "Las Vegas, NV",
]

MAX_PER_QUERY = 20  # results per search string — keeps cost down


# ── Main ─────────────────────────────────────────────────

async def main():
    if not APIFY_API_TOKEN:
        print("❌ Set APIFY_API_TOKEN env var first")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {APIFY_API_TOKEN}"}

    # Build search strings: each query × each metro
    search_strings = []
    for query in SEARCH_QUERIES:
        for metro in US_METROS:
            search_strings.append(f"{query} in {metro}")

    total_queries = len(search_strings)
    print(f"🔍 Searching {total_queries} query+metro combos ({len(SEARCH_QUERIES)} queries × {len(US_METROS)} metros)")
    print(f"   Max {MAX_PER_QUERY} results per query → up to {total_queries * MAX_PER_QUERY} raw results")
    print()

    # ── Start the actor run ──────────────────────────────
    actor_input = {
        "searchStringsArray": search_strings,
        "maxCrawledPlacesPerSearch": MAX_PER_QUERY,
        "language": "en",
        "deeperCityScrape": False,
        "includeWebResults": False,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        print("🚀 Starting Apify actor run...")
        resp = await client.post(
            f"{APIFY_BASE}/acts/{ACTOR_ID}/runs",
            headers=headers,
            json=actor_input,
        )
        if resp.status_code != 201:
            print(f"❌ Failed to start run: {resp.status_code}")
            print(resp.text)
            sys.exit(1)

        run_data = resp.json()["data"]
        run_id = run_data["id"]
        dataset_id = run_data.get("defaultDatasetId")
        print(f"✅ Run started: {run_id}")
        print(f"   Dataset: {dataset_id}")
        print(f"   Dashboard: https://console.apify.com/actors/runs/{run_id}")
        print()

    # ── Poll for completion (fresh client each time) ────
    print("⏳ Polling for completion (this may take 5-15 minutes)...")
    poll_interval = 20  # seconds
    while True:
        time.sleep(poll_interval)
        try:
            async with httpx.AsyncClient(timeout=30.0) as poll_client:
                resp = await poll_client.get(
                    f"{APIFY_BASE}/actor-runs/{run_id}",
                    headers=headers,
                )
                status = resp.json()["data"]["status"]
        except Exception as e:
            print(f"   ⚠️  Poll error (retrying): {e}")
            continue

        print(f"   Status: {status}")

        if status == "SUCCEEDED":
            print("✅ Scrape complete!")
            break
        elif status in ("FAILED", "TIMED-OUT", "ABORTED"):
            print(f"❌ Run ended with status: {status}")
            sys.exit(1)

    # ── Fetch results ────────────────────────────────
    print()
    print("📥 Fetching results...")
    async with httpx.AsyncClient(timeout=120.0) as dl_client:
        resp = await dl_client.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            headers=headers,
            params={"format": "json", "clean": "true"},
        )
        items = resp.json()

    print(f"   Got {len(items)} raw results")

    # ── Save raw data ────────────────────────────────────
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    raw_path = data_dir / "heavy_duty_raw.json"
    with open(raw_path, "w") as f:
        json.dump(items, f, indent=2, default=str)
    print(f"💾 Raw data saved to {raw_path}")

    # ── Parse and deduplicate ────────────────────────────
    seen_phones = set()
    mechanics = []

    for item in items:
        phone = item.get("phone")
        name = item.get("title") or item.get("name")
        lat = (item.get("location") or {}).get("lat")
        lng = (item.get("location") or {}).get("lng")

        if not phone or not name or lat is None:
            continue

        # Normalize phone
        digits = "".join(c for c in phone if c.isdigit() or c == "+")
        if not digits.startswith("+"):
            if len(digits) == 10:
                digits = f"+1{digits}"
            elif len(digits) == 11 and digits.startswith("1"):
                digits = f"+{digits}"

        if digits in seen_phones:
            continue
        seen_phones.add(digits)

        categories = item.get("categories", []) or []
        combined = f"{name} {' '.join(categories)}".lower()

        # Determine vehicle types supported
        vehicle_types = []
        if any(kw in combined for kw in ("heavy duty", "semi", "18 wheeler", "commercial truck", "heavy equipment")):
            vehicle_types.append("heavy_duty")
        if any(kw in combined for kw in ("diesel", "semi", "fleet")):
            vehicle_types.append("diesel")
        if any(kw in combined for kw in ("trailer", "flatbed")):
            vehicle_types.append("trailer")
        if any(kw in combined for kw in ("rv", "motorhome")):
            vehicle_types.append("rv")
        if not vehicle_types:
            vehicle_types.append("commercial")

        # Determine service types
        service_types = []
        if any(kw in combined for kw in ("tire", "flat")):
            service_types.append("flat_tire")
        if any(kw in combined for kw in ("tow", "wrecker", "haul")):
            service_types.append("tow_needed")
        if any(kw in combined for kw in ("battery", "jump")):
            service_types.append("dead_battery")
        if any(kw in combined for kw in ("engine", "repair", "mechanic", "diesel")):
            service_types.append("engine_trouble")
        if any(kw in combined for kw in ("fuel", "gas")):
            service_types.append("fuel_delivery")
        if not service_types:
            service_types.append("engine_trouble")

        # Is it mobile/roadside?
        is_roadside = any(kw in combined for kw in (
            "mobile", "roadside", "emergency", "24 hour", "24/7",
            "on-site", "on site", "breakdown", "field service"
        ))

        mechanic = {
            "company_name": name,
            "phone": digits,
            "address": item.get("address", ""),
            "lat": lat,
            "lng": lng,
            "rating": item.get("totalScore"),
            "review_count": item.get("reviewsCount", 0),
            "website": item.get("website", ""),
            "categories": categories,
            "service_types": service_types,
            "vehicle_types": vehicle_types,
            "is_roadside": is_roadside,
            "hours": item.get("openingHours"),
            "source_url": item.get("url", ""),
        }
        mechanics.append(mechanic)

    # ── Save parsed data ─────────────────────────────────
    parsed_path = data_dir / "heavy_duty_parsed.json"
    with open(parsed_path, "w") as f:
        json.dump(mechanics, f, indent=2, default=str)
    print(f"💾 Parsed data saved to {parsed_path}")

    # ── Summary ──────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"📊 SUMMARY")
    print("=" * 60)
    print(f"   Total raw results:     {len(items)}")
    print(f"   Unique mechanics:      {len(mechanics)}")
    print(f"   With phone:            {len([m for m in mechanics if m['phone']])}")
    print(f"   Roadside/mobile:       {len([m for m in mechanics if m['is_roadside']])}")
    print(f"   Heavy duty tagged:     {len([m for m in mechanics if 'heavy_duty' in m['vehicle_types']])}")
    print(f"   Diesel tagged:         {len([m for m in mechanics if 'diesel' in m['vehicle_types']])}")
    print(f"   With rating:           {len([m for m in mechanics if m['rating']])}")
    print(f"   With website:          {len([m for m in mechanics if m['website']])}")
    print(f"   With hours:            {len([m for m in mechanics if m['hours']])}")
    print()

    # Show top 10 by rating
    rated = sorted(
        [m for m in mechanics if m["rating"]],
        key=lambda m: (m["rating"], m["review_count"] or 0),
        reverse=True,
    )
    print("🏆 Top 10 by rating:")
    for m in rated[:10]:
        roadside = "🚗 ROADSIDE" if m["is_roadside"] else "🏪 SHOP"
        print(
            f"   ⭐ {m['rating']:.1f} ({m['review_count'] or 0} reviews) — "
            f"{m['company_name'][:40]} — {m['phone']} — {roadside}"
        )

    print()
    print(f"📁 Files saved in: {data_dir}")
    print(f"   → heavy_duty_raw.json    ({len(items)} records)")
    print(f"   → heavy_duty_parsed.json ({len(mechanics)} unique mechanics)")
    print()
    print("Next step: import into database with:")
    print("   python scripts/import_scraped.py")


if __name__ == "__main__":
    asyncio.run(main())
