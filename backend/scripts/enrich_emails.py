#!/usr/bin/env python3
"""
Enrich mechanics DB with email addresses by scraping their websites via Apify.

Strategy:
  1. Pull all mechanics with a website but no email from the DB.
  2. For each batch of websites, run Apify's website-content-crawler actor
     (apify/website-content-crawler) scoped to 1-2 pages per site (home + contact).
  3. Parse mailto: links and bare email patterns from the crawled HTML.
  4. Write the first valid email back to the DB and mark enriched_at.

Usage:
    uv run python scripts/enrich_emails.py [--limit 200] [--batch 20] [--dry-run]

Requires:
    APIFY_API_TOKEN  (already in .env)
    DATABASE_URL     (already in .env)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────────────────
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not APIFY_TOKEN:
    sys.exit("ERROR: APIFY_API_TOKEN not set in .env")
if not DATABASE_URL:
    sys.exit("ERROR: DATABASE_URL not set in .env")

# ── Email regex ───────────────────────────────────────────────────────────────
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

# Domains to discard (image hosts, CDNs, common false-positives)
_IGNORE_EMAIL_DOMAINS = {
    "sentry.io", "example.com", "wixpress.com", "squarespace.com",
    "shopify.com", "wordpress.com", "amazonaws.com", "cloudflare.com",
    "google.com", "facebook.com", "twitter.com", "instagram.com",
    "png", "jpg", "jpeg", "gif", "svg", "webp",
}

_PREFERRED_LOCALS = {
    "service", "support", "info", "dispatch", "contact", "sales", "office", "help", "admin",
}

_DISCOURAGED_LOCALS = {
    "noreply", "no-reply", "donotreply", "do-not-reply", "mailer-daemon",
}

_FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com", "proton.me", "protonmail.com",
}


def _is_valid_email(email: str) -> bool:
    if len(email) > 254:
        return False
    domain = email.split("@")[-1].lower()
    if domain in _IGNORE_EMAIL_DOMAINS:
        return False
    if any(domain.endswith("." + d) for d in _IGNORE_EMAIL_DOMAINS):
        return False
    # Must have a dot in the domain part
    return "." in domain


def _normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    value = url.strip().lower()
    if not value:
        return None
    if "://" in value:
        value = value.split("://", 1)[1]
    if value.startswith("www."):
        value = value[4:]
    value = value.split("/", 1)[0].split(":", 1)[0].strip()
    return value or None


def _email_score(email: str, root_domain: str | None) -> int:
    local, _, domain = email.partition("@")
    local = local.lower()
    domain = domain.lower()

    score = 0
    if root_domain and (domain == root_domain or domain.endswith(f".{root_domain}")):
        score += 120
    if local in _PREFERRED_LOCALS:
        score += 35
    if local in _DISCOURAGED_LOCALS:
        score -= 50
    if domain in _FREE_EMAIL_PROVIDERS and (not root_domain or domain != root_domain):
        score -= 20
    if any(local.startswith(prefix) for prefix in ("info", "support", "service", "sales")):
        score += 10
    return score


def pick_best_email(candidates: list[str], website_url: str) -> str | None:
    if not candidates:
        return None

    root_domain = _normalize_domain(website_url)
    unique: list[str] = []
    seen: set[str] = set()
    for email in candidates:
        normalized = email.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)

    ranked = sorted(unique, key=lambda e: _email_score(e, root_domain), reverse=True)
    return ranked[0] if ranked else None


def extract_emails_from_text(text: str) -> list[str]:
    found = EMAIL_RE.findall(text)
    seen: set[str] = set()
    emails: list[str] = []
    for email in found:
        normalized = email.lower().strip().strip(".,;:'\"()[]{}<>")
        if _is_valid_email(normalized) and normalized not in seen:
            seen.add(normalized)
            emails.append(normalized)
    return emails


# ── Apify helpers ─────────────────────────────────────────────────────────────
APIFY_BASE = "https://api.apify.com/v2"


def _apify(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{APIFY_BASE}{path}?token={APIFY_TOKEN}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method.upper(),
        headers={"Content-Type": "application/json"},
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode()
        print(f"  Apify HTTP {e.code}: {msg[:300]}")
        raise


def run_crawler_batch(urls: list[str]) -> dict[str, str]:
    """
    Run Apify website-content-crawler for a batch of root URLs.
    Returns {website_url: first_email_found}.

    Each site is crawled up to max_crawl_pages=3 (home + contact + about)
    with a 30s timeout per page. We use the lightweight `cheerio` crawler
    (server-side JS, no browser) for speed and cost.
    """
    print(f"  → Starting Apify crawler for {len(urls)} URLs …")

    # Start only at the root and let the crawler follow internal links to
    # contact / about / locations pages. Hard-coding /contact often yields
    # 404s on sites that use different paths (e.g. /get-in-touch).
    start_urls = [{"url": u.rstrip("/")} for u in urls]

    run_input = {
        "startUrls": start_urls,
        # Allow up to ~6 pages per site (home + a few internal)
        "maxCrawlPages": len(urls) * 6,
        "maxCrawlPagesPerStartUrl": 6,
        "maxCrawlDepth": 2,
        "pageLoadTimeoutSecs": 30,
        "maxConcurrency": 20,
        "crawlerType": "cheerio",
        "saveHtml": True,
        "saveMarkdown": True,
        # Prefer links that look like contact / about / footer / team pages
        "linkSelector": "a[href*='contact' i], a[href*='about' i], a[href*='touch' i], a[href*='team' i], a[href*='locations' i], a[href*='reach' i], footer a",
        "proxyConfiguration": {"useApifyProxy": True},
    }

    # Start the run
    resp = _apify("POST", "/acts/apify~website-content-crawler/runs", run_input)
    run_id = resp["data"]["id"]
    print(f"  → Run ID: {run_id}")

    # Poll until done (max 10 min)
    deadline = time.time() + 600
    while time.time() < deadline:
        time.sleep(8)
        status_resp = _apify("GET", f"/actor-runs/{run_id}")
        phase = status_resp["data"]["status"]
        print(f"  … status={phase}")
        if phase in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break

    if phase != "SUCCEEDED":
        print(f"  ⚠ Run ended with status={phase}, extracting partial results.")

    # Fetch dataset items
    dataset_id = status_resp["data"]["defaultDatasetId"]
    items_resp = _apify("GET", f"/datasets/{dataset_id}/items?limit=1000")

    # The items endpoint returns a list directly
    if isinstance(items_resp, list):
        items = items_resp
    elif isinstance(items_resp, dict):
        items = items_resp.get("items", items_resp.get("data", []))
        if isinstance(items, dict):
            items = []
    else:
        items = []

    print(f"  → Crawled {len(items)} pages")

    # Map page url back to a root url in our input list
    def _root_match(page_url: str) -> str | None:
        for u in urls:
            root = u.rstrip("/").lower()
            pu = page_url.lower()
            if pu.startswith(root) or root in pu:
                return u
        return None

    results: dict[str, str] = {}
    for item in items:
        page_url = item.get("url", "")
        # Combine all text fields including raw HTML (catches mailto:) and markdown.
        text_blob = " ".join(filter(None, [
            item.get("text", ""),
            item.get("markdown", ""),
            item.get("html", "") or "",
            json.dumps(item.get("metadata", {})),
        ]))
        candidates = extract_emails_from_text(text_blob)
        if not candidates:
            continue
        root = _root_match(page_url)
        if root and root not in results:
            best = pick_best_email(candidates, root)
            if best:
                results[root] = best
                print(f"    ✓ {root} → {best}")

    return results


# ── DB helpers ────────────────────────────────────────────────────────────────
def _sync_db_url(url: str) -> str:
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgres://", "postgresql://")
    return url


def get_mechanics_needing_email(limit: int, state: str | None = None) -> list[dict]:
    import psycopg2
    db_url = _sync_db_url(DATABASE_URL)
    is_local = "localhost" in db_url or "127.0.0.1" in db_url
    extra = {} if is_local else {"sslmode": "require"}
    conn = psycopg2.connect(db_url, **extra)
    try:
        with conn.cursor() as cur:
            state_clause = ""
            params: list = []
            if state:
                state_clause = "AND upper(state) = %s"
                params.append(state.upper())
            params.append(limit)
            cur.execute(
                f"""
                SELECT id, company_name, website
                FROM mechanics
                WHERE website IS NOT NULL AND website != ''
                  AND (email IS NULL OR email = '')
                  AND (last_enriched_at IS NULL OR last_enriched_at < NOW() - INTERVAL '30 days')
                  {state_clause}
                ORDER BY last_enriched_at NULLS FIRST, id
                LIMIT %s
                """,
                tuple(params),
            )
            rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "website": r[2]} for r in rows]
    finally:
        conn.close()


def write_emails(email_map: dict[str, str]) -> int:
    """email_map: {mechanic_id: email}"""
    if not email_map:
        return 0
    import psycopg2
    db_url = _sync_db_url(DATABASE_URL)
    is_local = "localhost" in db_url or "127.0.0.1" in db_url
    extra = {} if is_local else {"sslmode": "require"}
    conn = psycopg2.connect(db_url, **extra)
    updated = 0
    try:
        with conn.cursor() as cur:
            for mech_id, email in email_map.items():
                cur.execute(
                    "UPDATE mechanics SET email = %s, last_enriched_at = NOW() WHERE id = %s AND (email IS NULL OR email = '')",
                    (email, mech_id),
                )
                updated += cur.rowcount
        conn.commit()
    finally:
        conn.close()
    return updated


def stamp_attempted(mech_ids: list[str]) -> None:
    """Mark a batch of mechanic IDs as attempted so we don't re-crawl them soon."""
    if not mech_ids:
        return
    import psycopg2
    db_url = _sync_db_url(DATABASE_URL)
    is_local = "localhost" in db_url or "127.0.0.1" in db_url
    extra = {} if is_local else {"sslmode": "require"}
    conn = psycopg2.connect(db_url, **extra)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE mechanics SET last_enriched_at = NOW() WHERE id = ANY(%s::uuid[])",
                ([str(i) for i in mech_ids],),
            )
        conn.commit()
    finally:
        conn.close()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Enrich mechanics DB with email addresses via Apify")
    parser.add_argument("--limit", type=int, default=200, help="Max mechanics to process (default 200)")
    parser.add_argument("--batch", type=int, default=20, help="Websites per Apify run (default 20)")
    parser.add_argument("--state", type=str, default=None, help="Two-letter state code to target (e.g. FL)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done, no DB writes")
    args = parser.parse_args()

    print(f"=== Roadcall Email Enrichment via Apify ===")
    print(f"  Limit : {args.limit}")
    print(f"  Batch : {args.batch}")
    print(f"  State : {args.state or 'ALL'}")
    print(f"  Mode  : {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()

    print("Fetching mechanics with websites but no email …")
    try:
        mechanics = get_mechanics_needing_email(args.limit, state=args.state)
    except Exception as e:
        print(f"ERROR connecting to DB: {e}")
        print("Tip: ensure psycopg2 is installed: uv pip install psycopg2-binary")
        sys.exit(1)

    print(f"Found {len(mechanics)} mechanics to enrich")
    if not mechanics:
        print("Nothing to do.")
        return

    total_found = 0
    total_written = 0

    # Process in batches
    for batch_start in range(0, len(mechanics), args.batch):
        batch = mechanics[batch_start : batch_start + args.batch]
        print(f"\n--- Batch {batch_start // args.batch + 1}: mechanics {batch_start+1}–{batch_start+len(batch)} ---")

        # website → mechanic_id map for this batch
        website_to_id: dict[str, str] = {}
        valid_websites = []
        for m in batch:
            ws = (m["website"] or "").strip()
            if not ws.startswith("http"):
                ws = "https://" + ws
            website_to_id[ws] = m["id"]
            website_to_id[ws.rstrip("/")] = m["id"]
            valid_websites.append(ws)

        if args.dry_run:
            print(f"  [DRY RUN] Would crawl: {valid_websites[:3]} …")
            continue

        try:
            # website_url → email
            url_email_map = run_crawler_batch(valid_websites)
        except Exception as e:
            print(f"  ⚠ Apify error: {e}. Skipping batch.")
            continue

        # Translate to mechanic_id → email
        id_email_map: dict[str, str] = {}
        for ws, email in url_email_map.items():
            mech_id = website_to_id.get(ws) or website_to_id.get(ws.rstrip("/"))
            if mech_id:
                id_email_map[mech_id] = email

        total_found += len(id_email_map)
        print(f"  Found emails for {len(id_email_map)}/{len(batch)} mechanics in this batch")

        written = write_emails(id_email_map)
        total_written += written
        print(f"  Wrote {written} emails to DB")

        # Mark every attempted mechanic so we don't recrawl misses for 30 days.
        try:
            stamp_attempted([m["id"] for m in batch])
        except Exception as e:
            print(f"  ⚠ Failed to stamp last_enriched_at: {e}")

    print(f"\n=== Done ===")
    print(f"  Emails found : {total_found}")
    print(f"  DB rows updated : {total_written}")


if __name__ == "__main__":
    main()
