#!/usr/bin/env python3
"""Scrape national roadside/truck-service vendor locations via Apify.

Outputs:
  backend/data/national_vendors_us_raw.json
  backend/data/national_vendors_us_parsed.json
  backend/data/national_vendors_us.csv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None

ROOT = Path(__file__).resolve().parents[2]
for env_path in (ROOT / ".env", ROOT / "backend" / ".env"):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "nwua9Gu5YrADL7ZDj"

US_STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
]

STATE_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}

BRANDS = [
    {"brand": "Love's", "queries": ["Love's Travel Stop", "Love's Truck Care"]},
    {"brand": "TA Petro", "queries": ["TravelCenters of America truck service", "Petro Stopping Centers"]},
    {"brand": "Speedco", "queries": ["Speedco truck service"]},
    {"brand": "Pilot Flying J", "queries": ["Pilot Flying J truck care", "Pilot Travel Center truck service"]},
    {"brand": "Southern Tire Mart", "queries": ["Southern Tire Mart"]},
    {"brand": "Boss Truck Shops", "queries": ["Boss Truck Shops"]},
    {"brand": "Goodyear Commercial Tire", "queries": ["Goodyear Commercial Tire"]},
    {"brand": "Bridgestone Commercial", "queries": ["Bridgestone Commercial tire"]},
    {"brand": "Rush Truck Centers", "queries": ["Rush Truck Centers"]},
    {"brand": "MHC Kenworth", "queries": ["MHC Kenworth"]},
    {"brand": "TruckPro", "queries": ["TruckPro"]},
    {"brand": "FleetPride", "queries": ["FleetPride"]},
    {"brand": "Ryder", "queries": ["Ryder truck maintenance"]},
    {"brand": "Penske", "queries": ["Penske truck maintenance"]},
    {"brand": "Thermo King", "queries": ["Thermo King dealer service"]},
]


def _normalize_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return None


def _state_to_abbr(raw: str | None) -> str:
    value = (raw or "").strip()
    if len(value) == 2 and value.upper() in US_STATE_CODES:
        return value.upper()
    return STATE_ABBR.get(value.lower(), value.upper())


def _detect_brand(name: str, query: str) -> str:
    haystack = f"{name} {query}".lower()
    for brand in BRANDS:
        if any(token.lower().replace("'", "") in haystack.replace("'", "") for token in [brand["brand"], *brand["queries"]]):
            return brand["brand"]
    return query.split(" in ", 1)[0]


def _parse_item(item: dict[str, Any]) -> dict[str, Any] | None:
    name = (item.get("title") or item.get("name") or "").strip()
    if not name:
        return None
    location = item.get("location") or {}
    categories = item.get("categories") or []
    if not isinstance(categories, list):
        categories = []
    search_string = item.get("searchString") or item.get("searchStringUrl") or ""
    brand = _detect_brand(name, search_string)
    lat = location.get("lat")
    lng = location.get("lng")
    return {
        "brand_name": brand,
        "location_name": name,
        "phone": _normalize_phone(item.get("phone") or item.get("phoneUnformatted")),
        "email": "",
        "website": item.get("website") or "",
        "address": item.get("address") or "",
        "city": item.get("city") or "",
        "state": _state_to_abbr(item.get("state")),
        "lat": float(lat) if lat is not None else None,
        "lng": float(lng) if lng is not None else None,
        "rating": item.get("totalScore") or item.get("rating"),
        "review_count": item.get("reviewsCount") or item.get("reviews") or 0,
        "categories": ";".join(categories),
        "services": "truck_service;tire_service;roadside_vendor",
        "source_url": item.get("url") or "",
        "source": "apify_google_maps",
    }


def _record_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row.get("brand_name") or "").lower(),
        str(row.get("phone") or "").lower(),
        str(row.get("address") or "").lower(),
    )


async def _start_run(client, token: str, search_strings: list[str], max_per_search: int) -> tuple[str, str]:
    response = await client.post(
        f"{APIFY_BASE}/acts/{ACTOR_ID}/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "searchStringsArray": search_strings,
            "maxCrawledPlacesPerSearch": max_per_search,
            "language": "en",
            "deeperCityScrape": False,
            "includeWebResults": False,
        },
    )
    if response.status_code != 201:
        raise RuntimeError(f"Failed to start Apify run ({response.status_code}): {response.text[:300]}")
    data = response.json()["data"]
    return data["id"], data["defaultDatasetId"]


async def _poll_run(client, token: str, run_id: str) -> None:
    while True:
        response = await client.get(f"{APIFY_BASE}/actor-runs/{run_id}", headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        status = response.json()["data"]["status"]
        print(f"   Status: {status}")
        if status == "SUCCEEDED":
            return
        if status in {"FAILED", "TIMED-OUT", "ABORTED"}:
            raise RuntimeError(f"Apify run ended with status={status}")
        await asyncio.sleep(20)


async def _fetch_items(client, token: str, dataset_id: str) -> list[dict[str, Any]]:
    response = await client.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "json", "clean": "true"},
        timeout=180.0,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def _export_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = ["brand_name", "location_name", "phone", "email", "website", "address", "city", "state", "lat", "lng", "rating", "review_count", "categories", "services", "source_url", "source"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--states", type=int, default=51)
    parser.add_argument("--max-per-search", type=int, default=12)
    parser.add_argument("--output-prefix", default="national_vendors_us")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--dataset-id", default="")
    args = parser.parse_args()

    if httpx is None:
        raise SystemExit("Missing dependency: httpx")
    token = os.environ.get("APIFY_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("Missing APIFY_API_TOKEN")

    search_strings = []
    for brand in BRANDS:
        for query in brand["queries"]:
            for state in US_STATE_CODES[: min(args.states, len(US_STATE_CODES))]:
                search_strings.append(f"{query} in {state}, USA")

    print(f"🔍 National vendor search strings: {len(search_strings)}")
    print(f"📈 Max raw rows estimate: {len(search_strings) * args.max_per_search}")

    started = time.time()
    async with httpx.AsyncClient(timeout=60.0) as client:
        if args.run_id:
            run_id, dataset_id = args.run_id, args.dataset_id
            print(f"🔁 Resuming Apify run: {run_id}")
        else:
            print("🚀 Starting Apify run...")
            run_id, dataset_id = await _start_run(client, token, search_strings, args.max_per_search)
            print(f"✅ Run started: {run_id}")
            print(f"   Dataset: {dataset_id}")
            print(f"   Console: https://console.apify.com/actors/runs/{run_id}")
        await _poll_run(client, token, run_id)
        print("📥 Downloading dataset items...")
        items = await _fetch_items(client, token, dataset_id)

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    raw_path = data_dir / f"{args.output_prefix}_raw.json"
    parsed_path = data_dir / f"{args.output_prefix}_parsed.json"
    csv_path = data_dir / f"{args.output_prefix}.csv"
    raw_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

    seen = set()
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = _parse_item(item)
        if not row:
            continue
        key = _record_key(row)
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)

    parsed_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    _export_csv(csv_path, rows)

    brands: dict[str, int] = {}
    for row in rows:
        brands[row["brand_name"]] = brands.get(row["brand_name"], 0) + 1
    print("\n" + "=" * 72)
    print("NATIONAL VENDOR SCRAPE SUMMARY")
    print("=" * 72)
    print(f"Run seconds:       {int(time.time() - started)}")
    print(f"Raw rows:          {len(items):,}")
    print(f"Deduped locations: {len(rows):,}")
    print(f"With phone:        {sum(1 for row in rows if row.get('phone')):,}")
    print(f"With website:      {sum(1 for row in rows if row.get('website')):,}")
    print(f"CSV:               {csv_path}")
    for brand, count in sorted(brands.items(), key=lambda item: item[1], reverse=True)[:20]:
        print(f"  - {brand}: {count:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
