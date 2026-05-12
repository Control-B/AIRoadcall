#!/usr/bin/env python3
"""Name Apify email-enrichment datasets and sync harvested emails into Postgres.

This script reads recent `apify/website-content-crawler` runs, assigns stable
names to their default datasets, extracts emails from result payloads, matches
those emails to mechanics by website domain, and updates mechanics.email in the
configured production database.

Usage:
  python backend/scripts/sync_apify_email_datasets.py --runs 100 --apply
  python backend/scripts/sync_apify_email_datasets.py --runs 20 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
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

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
APIFY_BASE = "https://api.apify.com/v2"
ACTOR_ID = "apify~website-content-crawler"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
IGNORE_DOMAINS = {
    "example.com", "sentry.io", "wixpress.com", "squarespace.com", "shopify.com",
    "wordpress.com", "amazonaws.com", "cloudflare.com", "google.com", "facebook.com",
    "twitter.com", "instagram.com", "schema.org", "w3.org", "mapbox.com",
}


def require_env() -> None:
    missing = [name for name, value in {"APIFY_API_TOKEN": APIFY_TOKEN, "DATABASE_URL": DATABASE_URL}.items() if not value]
    if missing:
        raise SystemExit(f"Missing required env values: {', '.join(missing)}")


def apify_request(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    separator = "&" if "?" in path else "?"
    url = f"{APIFY_BASE}{path}{separator}token={urllib.parse.quote(APIFY_TOKEN)}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url,
        method=method.upper(),
        data=data,
        headers={"Content-Type": "application/json"},
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, context=ctx, timeout=90) as response:
            raw = response.read()
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Apify HTTP {exc.code} for {path}: {message}") from exc


def normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if "://" not in url:
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    host = (parsed.netloc or parsed.path).split("/")[0].lower()
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        return None
    return host


def is_valid_email(email: str) -> bool:
    email = email.lower().strip().strip(".,;:'\"()[]{}<>")
    if len(email) > 254 or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1]
    if domain in IGNORE_DOMAINS or any(domain.endswith("." + ignored) for ignored in IGNORE_DOMAINS):
        return False
    if any(email.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
        return False
    return "." in domain


def extract_emails(item: dict[str, Any]) -> list[str]:
    text = " ".join(
        str(part)
        for part in (
            item.get("url", ""),
            item.get("text", ""),
            item.get("markdown", ""),
            item.get("html", ""),
            json.dumps(item.get("metadata", {}), ensure_ascii=False),
        )
        if part
    )
    seen: set[str] = set()
    emails: list[str] = []
    for raw in EMAIL_RE.findall(text):
        email = raw.lower().strip().strip(".,;:'\"()[]{}<>")
        if is_valid_email(email) and email not in seen:
            seen.add(email)
            emails.append(email)
    return emails


def dataset_items(dataset_id: str, limit: int = 5000) -> list[dict[str, Any]]:
    result = apify_request("GET", f"/datasets/{dataset_id}/items?clean=1&limit={limit}")
    if isinstance(result, list):
        return [item for item in result if isinstance(item, dict)]
    if isinstance(result, dict):
        items = result.get("items") or result.get("data") or []
        return [item for item in items if isinstance(item, dict)]
    return []


def list_recent_runs(limit: int) -> list[dict[str, Any]]:
    result = apify_request("GET", f"/acts/{ACTOR_ID}/runs?limit={limit}&desc=1")
    return result.get("data", {}).get("items", []) if isinstance(result, dict) else []


def name_dataset(dataset_id: str, name: str, dry_run: bool) -> bool:
    if dry_run:
        return False
    try:
        apify_request("PUT", f"/datasets/{dataset_id}", {"name": name})
        return True
    except Exception as exc:
        print(f"  ⚠ Could not name dataset {dataset_id} as {name}: {exc}")
        return False


def sync_db(domain_to_email: dict[str, str], apply: bool) -> tuple[int, int, int]:
    import psycopg2

    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")
    sslmode = None if "localhost" in db_url or "127.0.0.1" in db_url or "@postgres:" in db_url else "require"
    conn = psycopg2.connect(db_url, sslmode=sslmode) if sslmode else psycopg2.connect(db_url)
    matched = updated = skipped_existing = 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, website, email FROM mechanics WHERE website IS NOT NULL AND website <> ''")
            rows = cur.fetchall()
            for mechanic_id, website, existing_email in rows:
                domain = normalize_domain(website)
                if not domain:
                    continue
                email = domain_to_email.get(domain)
                if not email:
                    parts = domain.split(".")
                    if len(parts) > 2:
                        email = domain_to_email.get(".".join(parts[-2:]))
                if not email:
                    continue
                matched += 1
                if existing_email:
                    skipped_existing += 1
                    continue
                if apply:
                    cur.execute(
                        """
                        UPDATE mechanics
                        SET email = %s,
                            last_enriched_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                          AND (email IS NULL OR email = '')
                        """,
                        (email, mechanic_id),
                    )
                    updated += cur.rowcount
            if apply:
                conn.commit()
            else:
                conn.rollback()
    finally:
        conn.close()
    return matched, skipped_existing, updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100, help="Recent crawler runs to inspect")
    parser.add_argument("--dataset-limit", type=int, default=5000, help="Items to fetch per dataset")
    parser.add_argument("--apply", action="store_true", help="Write updates to DB and Apify dataset names")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()
    apply = args.apply and not args.dry_run

    require_env()
    runs = list_recent_runs(args.runs)
    print(f"Found {len(runs)} recent website-content-crawler runs")

    domain_to_email: dict[str, str] = {}
    named = 0
    processed = 0
    date_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for index, run in enumerate(reversed(runs), start=1):
        status = run.get("status")
        dataset_id = run.get("defaultDatasetId")
        if status not in {"SUCCEEDED", "RUNNING", "TIMED-OUT"} or not dataset_id:
            continue
        dataset_name = f"roadcall-email-enrichment-{date_prefix}-batch-{index:03d}"
        if name_dataset(dataset_id, dataset_name, dry_run=not apply):
            named += 1
        items = dataset_items(dataset_id, args.dataset_limit)
        processed += 1
        found_in_dataset = 0
        dataset_domain_emails: dict[str, list[str]] = defaultdict(list)
        for item in items:
            domain = normalize_domain(item.get("url"))
            if not domain:
                continue
            emails = extract_emails(item)
            if not emails:
                continue
            dataset_domain_emails[domain].extend(emails)
        for domain, emails in dataset_domain_emails.items():
            for email in emails:
                if domain not in domain_to_email:
                    domain_to_email[domain] = email
                    found_in_dataset += 1
                    break
        print(f"  {dataset_id} ({status}) -> {len(items)} pages, {found_in_dataset} domains with emails, name={dataset_name}")

    matched, skipped_existing, updated = sync_db(domain_to_email, apply=apply)
    print("\nSummary")
    print(f"  datasets processed: {processed}")
    print(f"  datasets named: {named}")
    print(f"  unique domains with emails: {len(domain_to_email)}")
    print(f"  DB website-domain matches: {matched}")
    print(f"  already had email: {skipped_existing}")
    print(f"  DB rows updated: {updated}")
    print(f"  mode: {'APPLY' if apply else 'DRY RUN'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
