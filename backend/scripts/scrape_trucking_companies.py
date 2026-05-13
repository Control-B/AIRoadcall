"""Scrape U.S. trucking companies via Apify Google Maps and export clean lists.

Usage:
  cd backend
  APIFY_API_TOKEN=apify_xxx python scripts/scrape_trucking_companies.py

Optional tuning:
  APIFY_API_TOKEN=apify_xxx python scripts/scrape_trucking_companies.py \
    --max-per-search 80 \
    --states 25 \
    --output-prefix trucking_companies_us

What this does:
  1) Builds search strings from trucking-related queries across U.S. states
  2) Runs Apify Google Places actor (compass/crawler-google-places)
  3) Fetches dataset results
  4) Deduplicates records (phone + name/address fallback)
  5) Exports:
      - backend/data/<prefix>_raw.json
      - backend/data/<prefix>_parsed.json
      - backend/data/<prefix>.csv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    httpx = None

APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "nwua9Gu5YrADL7ZDj"  # compass/crawler-google-places

ROOT = Path(__file__).resolve().parents[2]
for env_path in (ROOT / ".env", ROOT / "backend" / ".env"):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

US_STATE_CODES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
]

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
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}

SEARCH_QUERIES = [
    "trucking company",
    "freight carrier",
    "logistics trucking",
    "truck transport company",
    "flatbed trucking company",
    "reefer trucking company",
    "LTL trucking company",
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


def _norm_text(value: str | None) -> str:
    return (value or "").strip().lower()


def _state_to_abbr(raw: str | None) -> str:
    value = (raw or "").strip()
    if len(value) == 2 and value.upper() in US_STATE_CODES:
        return value.upper()
    return STATE_ABBR.get(value.lower(), value.upper())


def _record_key(item: dict[str, Any]) -> tuple[str, str, str] | None:
    phone = _normalize_phone(item.get("phone") or item.get("phoneUnformatted"))
    if phone:
        return ("phone", phone, "")

    name = _norm_text(item.get("title") or item.get("name"))
    address = _norm_text(item.get("address"))
    website = _norm_text(item.get("website"))

    if name and address:
        return ("name_address", name, address)
    if name and website:
        return ("name_website", name, website)
    if name:
        return ("name_only", name, "")
    return None


def _parse_item(item: dict[str, Any]) -> dict[str, Any] | None:
    name = (item.get("title") or item.get("name") or "").strip()
    if not name:
        return None

    location = item.get("location") or {}
    lat = location.get("lat")
    lng = location.get("lng")

    categories = item.get("categories") or []
    if not isinstance(categories, list):
        categories = []

    parsed = {
        "company_name": name,
        "phone": _normalize_phone(item.get("phone") or item.get("phoneUnformatted")),
        "website": item.get("website") or "",
        "address": item.get("address") or "",
        "city": item.get("city") or "",
        "state": _state_to_abbr(item.get("state")),
        "lat": float(lat) if lat is not None else None,
        "lng": float(lng) if lng is not None else None,
        "rating": item.get("totalScore") or item.get("rating"),
        "review_count": item.get("reviewsCount") or item.get("reviews") or 0,
        "categories": categories,
        "source_url": item.get("url") or "",
        "source": "apify_google_maps",
    }

    return parsed


async def _start_run(client: httpx.AsyncClient, token: str, search_strings: list[str], max_per_search: int) -> tuple[str, str]:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "searchStringsArray": search_strings,
        "maxCrawledPlacesPerSearch": max_per_search,
        "language": "en",
        "deeperCityScrape": False,
        "includeWebResults": False,
    }

    response = await client.post(f"{APIFY_BASE}/acts/{ACTOR_ID}/runs", headers=headers, json=payload)
    if response.status_code != 201:
        raise RuntimeError(f"Failed to start Apify run ({response.status_code}): {response.text[:300]}")

    data = response.json().get("data") or {}
    run_id = data.get("id")
    dataset_id = data.get("defaultDatasetId")
    if not run_id or not dataset_id:
        raise RuntimeError("Apify run missing run_id or dataset_id")

    return run_id, dataset_id


async def _poll_run(client: httpx.AsyncClient, token: str, run_id: str, interval_sec: int = 20) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    while True:
        response = await client.get(f"{APIFY_BASE}/actor-runs/{run_id}", headers=headers)
        response.raise_for_status()
        status = (response.json().get("data") or {}).get("status")
        print(f"   Status: {status}")
        if status == "SUCCEEDED":
            return
        if status in {"FAILED", "TIMED-OUT", "ABORTED"}:
            raise RuntimeError(f"Apify run ended with status={status}")
        await asyncio.sleep(interval_sec)


async def _fetch_items(client: httpx.AsyncClient, token: str, dataset_id: str) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        headers=headers,
        params={"format": "json", "clean": "true"},
        timeout=180.0,
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, list):
        return payload
    return []


def _export_csv(path: Path, records: list[dict[str, Any]]) -> None:
    headers = [
        "company_name",
        "phone",
        "website",
        "address",
        "city",
        "state",
        "lat",
        "lng",
        "rating",
        "review_count",
        "categories",
        "source_url",
        "source",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in records:
            output = dict(row)
            output["categories"] = ";".join(output.get("categories") or [])
            writer.writerow(output)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape U.S. trucking companies via Apify Google Places")
    parser.add_argument("--max-per-search", type=int, default=60, help="Max places per search string")
    parser.add_argument("--states", type=int, default=51, help="Number of states/DC to include (for test runs use 3-10)")
    parser.add_argument("--output-prefix", type=str, default="trucking_companies_us", help="Output file prefix")
    parser.add_argument("--run-id", type=str, default="", help="Existing Apify run ID to resume instead of starting a new run")
    parser.add_argument("--dataset-id", type=str, default="", help="Existing Apify dataset ID to fetch when using --run-id")
    args = parser.parse_args()

    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if httpx is None:
        print("❌ Missing dependency: httpx")
        print("   Install with: pip install httpx")
        sys.exit(1)
    if not token:
        print("❌ Missing APIFY_API_TOKEN")
        sys.exit(1)

    if args.states < 1:
        print("❌ --states must be >= 1")
        sys.exit(1)

    target_states = US_STATE_CODES[: min(args.states, len(US_STATE_CODES))]
    search_strings: list[str] = []
    for query in SEARCH_QUERIES:
        for state in target_states:
            search_strings.append(f"{query} in {state}, USA")

    if args.run_id:
        if not args.dataset_id:
            print("❌ --dataset-id is required when using --run-id")
            sys.exit(1)
        print(f"🔁 Resuming Apify run: {args.run_id}")
        print(f"   Dataset: {args.dataset_id}")
    else:
        potential_max = len(search_strings) * args.max_per_search
        print(f"🔍 Search strings: {len(search_strings)} ({len(SEARCH_QUERIES)} queries × {len(target_states)} states)")
        print(f"📈 Max raw rows estimate: {potential_max}")

    started = time.time()
    async with httpx.AsyncClient(timeout=60.0) as client:
        if args.run_id:
            run_id, dataset_id = args.run_id, args.dataset_id
        else:
            print("🚀 Starting Apify run...")
            run_id, dataset_id = await _start_run(client, token, search_strings, args.max_per_search)
            print(f"✅ Run started: {run_id}")
            print(f"   Dataset: {dataset_id}")
            print(f"   Console: https://console.apify.com/actors/runs/{run_id}")

        print("⏳ Waiting for completion...")
        await _poll_run(client, token, run_id)

        print("📥 Downloading dataset items...")
        items = await _fetch_items(client, token, dataset_id)

    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    raw_path = data_dir / f"{args.output_prefix}_raw.json"
    parsed_path = data_dir / f"{args.output_prefix}_parsed.json"
    csv_path = data_dir / f"{args.output_prefix}.csv"

    raw_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

    seen: set[tuple[str, str, str]] = set()
    parsed: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        key = _record_key(item)
        if not key or key in seen:
            continue
        seen.add(key)

        row = _parse_item(item)
        if row:
            parsed.append(row)

    parsed_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    _export_csv(csv_path, parsed)

    elapsed = int(time.time() - started)
    with_phone = sum(1 for row in parsed if row.get("phone"))
    with_website = sum(1 for row in parsed if row.get("website"))
    by_state: dict[str, int] = {}
    for row in parsed:
        st = row.get("state") or ""
        if st:
            by_state[st] = by_state.get(st, 0) + 1

    top_states = sorted(by_state.items(), key=lambda x: x[1], reverse=True)[:10]

    print("\n" + "=" * 72)
    print("TRUCKING COMPANY SCRAPE SUMMARY")
    print("=" * 72)
    print(f"Run seconds:           {elapsed}")
    print(f"Raw rows:              {len(items):,}")
    print(f"Deduped companies:     {len(parsed):,}")
    print(f"With phone:            {with_phone:,}")
    print(f"With website:          {with_website:,}")
    print(f"Raw JSON:              {raw_path}")
    print(f"Parsed JSON:           {parsed_path}")
    print(f"CSV:                   {csv_path}")
    if top_states:
        print("Top states by count:")
        for state, count in top_states:
            print(f"  - {state}: {count:,}")


if __name__ == "__main__":
    asyncio.run(main())
