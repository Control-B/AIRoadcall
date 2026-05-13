#!/usr/bin/env python3
"""Import trucking companies and national vendors CSV/JSON exports into Postgres.

Usage:
  cd backend
  uv run python scripts/import_business_directories.py --kind trucking --path data/trucking_companies_us.csv
  uv run python scripts/import_business_directories.py --kind vendors --path data/national_vendors_us.csv

The importer is additive/idempotent. It creates the destination table if missing
and upserts by phone where available, otherwise by business/location identity.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import ssl
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for env_path in (ROOT / ".env", ROOT / "backend" / ".env"):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

DATABASE_URL = os.environ.get("DATABASE_URL", "")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
DOT_RE = re.compile(r"\b(?:USDOT|DOT)\s*#?\s*(\d{4,9})\b", re.IGNORECASE)
MC_RE = re.compile(r"\bMC\s*#?\s*(\d{4,9})\b", re.IGNORECASE)
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


def _sync_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")


def _connect():
    import psycopg2

    if not DATABASE_URL:
        raise SystemExit("Missing DATABASE_URL")
    db_url = _sync_db_url(DATABASE_URL)
    is_local = "localhost" in db_url or "127.0.0.1" in db_url or "@postgres:" in db_url
    if is_local:
        return psycopg2.connect(db_url)
    return psycopg2.connect(db_url, sslmode="require")


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return [row for row in data if isinstance(row, dict)]
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _none_if_blank(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return value


def _float_or_none(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except Exception:
        return None


def _state_to_abbr(raw: Any) -> str | None:
    value = _none_if_blank(raw)
    if not value:
        return None
    value = str(value).strip()
    if len(value) == 2:
        value = value.upper()
        return value if value in set(STATE_ABBR.values()) else None
    return STATE_ABBR.get(value.lower())


def _extract_email(row: dict[str, Any]) -> str | None:
    for key in ("email", "emails"):
        raw = str(row.get(key) or "")
        match = EMAIL_RE.search(raw)
        if match:
            return match.group(0).lower()
    return None


def _extract_dot_mc(row: dict[str, Any]) -> tuple[str | None, str | None]:
    haystack = " ".join(str(row.get(key) or "") for key in ("dot_number", "mc_number", "categories", "company_name", "source_url", "address"))
    dot = _none_if_blank(row.get("dot_number"))
    mc = _none_if_blank(row.get("mc_number"))
    if not dot:
        dot_match = DOT_RE.search(haystack)
        dot = dot_match.group(1) if dot_match else None
    if not mc:
        mc_match = MC_RE.search(haystack)
        mc = mc_match.group(1) if mc_match else None
    return dot, mc


def ensure_tables(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trucking_companies (
            id UUID PRIMARY KEY,
            company_name VARCHAR(255) NOT NULL,
            phone VARCHAR(30),
            email VARCHAR(255),
            website TEXT,
            address TEXT,
            city VARCHAR(120),
            state VARCHAR(10),
            lat DOUBLE PRECISION,
            lng DOUBLE PRECISION,
            rating DOUBLE PRECISION,
            review_count INTEGER,
            categories TEXT,
            dot_number VARCHAR(40),
            mc_number VARCHAR(40),
            source VARCHAR(80),
            source_url TEXT,
            last_enriched_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_trucking_companies_phone_not_null ON trucking_companies(phone) WHERE phone IS NOT NULL AND phone <> ''")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_trucking_companies_company_name ON trucking_companies(company_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_trucking_companies_state ON trucking_companies(state)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_trucking_companies_dot_number ON trucking_companies(dot_number)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_trucking_companies_mc_number ON trucking_companies(mc_number)")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS national_vendors (
            id UUID PRIMARY KEY,
            brand_name VARCHAR(120) NOT NULL,
            location_name VARCHAR(255) NOT NULL,
            phone VARCHAR(30),
            email VARCHAR(255),
            website TEXT,
            address TEXT,
            city VARCHAR(120),
            state VARCHAR(10),
            lat DOUBLE PRECISION,
            lng DOUBLE PRECISION,
            rating DOUBLE PRECISION,
            review_count INTEGER,
            categories TEXT,
            services TEXT,
            is_national_chain BOOLEAN NOT NULL DEFAULT true,
            source VARCHAR(80),
            source_url TEXT,
            last_enriched_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_national_vendors_brand_phone_address_idx ON national_vendors(brand_name, phone, address)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_national_vendors_brand_name ON national_vendors(brand_name)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_national_vendors_state ON national_vendors(state)")


def import_trucking(cur, rows: list[dict[str, Any]]) -> tuple[int, int]:
    inserted = updated = 0
    for row in rows:
        company_name = _none_if_blank(row.get("company_name"))
        if not company_name:
            continue
        state = _state_to_abbr(row.get("state"))
        if not state:
            continue
        dot, mc = _extract_dot_mc(row)
        params = {
            "id": str(uuid.uuid4()),
            "company_name": company_name,
            "phone": _none_if_blank(row.get("phone")),
            "email": _extract_email(row),
            "website": _none_if_blank(row.get("website")),
            "address": _none_if_blank(row.get("address")),
            "city": _none_if_blank(row.get("city")),
            "state": state,
            "lat": _float_or_none(row.get("lat")),
            "lng": _float_or_none(row.get("lng")),
            "rating": _float_or_none(row.get("rating")),
            "review_count": _int_or_none(row.get("review_count")),
            "categories": _none_if_blank(row.get("categories")),
            "dot_number": dot,
            "mc_number": mc,
            "source": _none_if_blank(row.get("source")) or "apify_google_maps",
            "source_url": _none_if_blank(row.get("source_url")),
        }
        if params["phone"]:
            cur.execute(
                """
                INSERT INTO trucking_companies (
                    id, company_name, phone, email, website, address, city, state, lat, lng,
                    rating, review_count, categories, dot_number, mc_number, source, source_url
                ) VALUES (
                    %(id)s, %(company_name)s, %(phone)s, %(email)s, %(website)s, %(address)s, %(city)s, %(state)s, %(lat)s, %(lng)s,
                    %(rating)s, %(review_count)s, %(categories)s, %(dot_number)s, %(mc_number)s, %(source)s, %(source_url)s
                )
                ON CONFLICT (phone) WHERE phone IS NOT NULL AND phone <> '' DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    email = COALESCE(trucking_companies.email, EXCLUDED.email),
                    website = COALESCE(EXCLUDED.website, trucking_companies.website),
                    address = COALESCE(EXCLUDED.address, trucking_companies.address),
                    city = COALESCE(EXCLUDED.city, trucking_companies.city),
                    state = COALESCE(EXCLUDED.state, trucking_companies.state),
                    lat = COALESCE(EXCLUDED.lat, trucking_companies.lat),
                    lng = COALESCE(EXCLUDED.lng, trucking_companies.lng),
                    rating = COALESCE(EXCLUDED.rating, trucking_companies.rating),
                    review_count = COALESCE(EXCLUDED.review_count, trucking_companies.review_count),
                    categories = COALESCE(EXCLUDED.categories, trucking_companies.categories),
                    dot_number = COALESCE(trucking_companies.dot_number, EXCLUDED.dot_number),
                    mc_number = COALESCE(trucking_companies.mc_number, EXCLUDED.mc_number),
                    source_url = COALESCE(EXCLUDED.source_url, trucking_companies.source_url),
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS inserted
                """,
                params,
            )
        else:
            cur.execute(
                """
                INSERT INTO trucking_companies (
                    id, company_name, phone, email, website, address, city, state, lat, lng,
                    rating, review_count, categories, dot_number, mc_number, source, source_url
                ) VALUES (
                    %(id)s, %(company_name)s, %(phone)s, %(email)s, %(website)s, %(address)s, %(city)s, %(state)s, %(lat)s, %(lng)s,
                    %(rating)s, %(review_count)s, %(categories)s, %(dot_number)s, %(mc_number)s, %(source)s, %(source_url)s
                )
                RETURNING true AS inserted
                """,
                params,
            )
        was_insert = bool(cur.fetchone()[0])
        inserted += 1 if was_insert else 0
        updated += 0 if was_insert else 1
    return inserted, updated


def import_vendors(cur, rows: list[dict[str, Any]]) -> tuple[int, int]:
    inserted = updated = 0
    for row in rows:
        brand_name = _none_if_blank(row.get("brand_name")) or _none_if_blank(row.get("brand"))
        location_name = _none_if_blank(row.get("location_name")) or _none_if_blank(row.get("company_name")) or brand_name
        if not brand_name or not location_name:
            continue
        state = _state_to_abbr(row.get("state"))
        if not state:
            continue
        params = {
            "id": str(uuid.uuid4()),
            "brand_name": brand_name,
            "location_name": location_name,
            "phone": _none_if_blank(row.get("phone")),
            "email": _extract_email(row),
            "website": _none_if_blank(row.get("website")),
            "address": _none_if_blank(row.get("address")),
            "city": _none_if_blank(row.get("city")),
            "state": state,
            "lat": _float_or_none(row.get("lat")),
            "lng": _float_or_none(row.get("lng")),
            "rating": _float_or_none(row.get("rating")),
            "review_count": _int_or_none(row.get("review_count")),
            "categories": _none_if_blank(row.get("categories")),
            "services": _none_if_blank(row.get("services")),
            "source": _none_if_blank(row.get("source")) or "apify_google_maps",
            "source_url": _none_if_blank(row.get("source_url")),
        }
        cur.execute(
            """
            INSERT INTO national_vendors (
                id, brand_name, location_name, phone, email, website, address, city, state, lat, lng,
                rating, review_count, categories, services, source, source_url
            ) VALUES (
                %(id)s, %(brand_name)s, %(location_name)s, %(phone)s, %(email)s, %(website)s, %(address)s, %(city)s, %(state)s, %(lat)s, %(lng)s,
                %(rating)s, %(review_count)s, %(categories)s, %(services)s, %(source)s, %(source_url)s
            )
            ON CONFLICT (brand_name, phone, address) DO UPDATE SET
                location_name = EXCLUDED.location_name,
                email = COALESCE(national_vendors.email, EXCLUDED.email),
                website = COALESCE(EXCLUDED.website, national_vendors.website),
                city = COALESCE(EXCLUDED.city, national_vendors.city),
                state = COALESCE(EXCLUDED.state, national_vendors.state),
                lat = COALESCE(EXCLUDED.lat, national_vendors.lat),
                lng = COALESCE(EXCLUDED.lng, national_vendors.lng),
                rating = COALESCE(EXCLUDED.rating, national_vendors.rating),
                review_count = COALESCE(EXCLUDED.review_count, national_vendors.review_count),
                categories = COALESCE(EXCLUDED.categories, national_vendors.categories),
                services = COALESCE(EXCLUDED.services, national_vendors.services),
                source_url = COALESCE(EXCLUDED.source_url, national_vendors.source_url),
                updated_at = CURRENT_TIMESTAMP
            RETURNING (xmax = 0) AS inserted
            """,
            params,
        )
        was_insert = bool(cur.fetchone()[0])
        inserted += 1 if was_insert else 0
        updated += 0 if was_insert else 1
    return inserted, updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["trucking", "vendors"], required=True)
    parser.add_argument("--path", required=True)
    args = parser.parse_args()

    path = Path(args.path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[1] / path
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    rows = _load_rows(path)
    print(f"Loaded {len(rows):,} rows from {path}")

    conn = _connect()
    try:
        with conn.cursor() as cur:
            ensure_tables(cur)
            if args.kind == "trucking":
                inserted, updated = import_trucking(cur, rows)
            else:
                inserted, updated = import_vendors(cur, rows)
        conn.commit()
    finally:
        conn.close()

    print(f"Import complete: inserted={inserted:,} updated={updated:,} kind={args.kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
