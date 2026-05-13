#!/usr/bin/env python3
"""Enrich business directory records with emails and trucking DOT/MC numbers.

Usage:
  cd backend
  uv run python scripts/enrich_business_directories.py --emails trucking --email-limit 200
  uv run python scripts/enrich_business_directories.py --emails vendors --email-limit 200
  uv run python scripts/enrich_business_directories.py --dot-limit 500

Notes:
  - Email enrichment fetches company websites directly and parses contact emails.
  - DOT enrichment queries the public FMCSA SAFER keyword search by company name.
  - This is additive: existing email/DOT/MC values are not overwritten.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
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
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
TAVILY_API_URL = "https://api.tavily.com/search"
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
DOT_RE = re.compile(r"USDOT[^0-9]{0,100}(\d{4,9})", re.IGNORECASE)
MC_RE = re.compile(r"\bMC[^0-9]{0,30}(\d{4,9})", re.IGNORECASE)

IGNORE_EMAIL_DOMAINS = {
    "example.com", "sentry.io", "wixpress.com", "squarespace.com", "shopify.com",
    "wordpress.com", "amazonaws.com", "cloudflare.com", "google.com", "facebook.com",
    "twitter.com", "instagram.com", "schema.org", "w3.org",
    "domain.com", "company.com", "email.com",
}

IGNORE_EMAIL_LOCALS = {"noreply", "no-reply", "donotreply", "do-not-reply", "user", "yourname", "name", "example"}

PREFERRED_EMAIL_LOCALS = ["dispatch", "contact", "info", "sales", "support", "service", "office"]


def _sync_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")


def _connect():
    import psycopg2

    if not DATABASE_URL:
        raise SystemExit("Missing DATABASE_URL")
    db_url = _sync_db_url(DATABASE_URL)
    is_local = "localhost" in db_url or "127.0.0.1" in db_url or "@postgres:" in db_url
    return psycopg2.connect(db_url) if is_local else psycopg2.connect(db_url, sslmode="require")


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    value = url.strip()
    if not value:
        return None
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    return value.rstrip("/")


def _domain(url: str | None) -> str | None:
    normalized = _normalize_url(url)
    if not normalized:
        return None
    host = urllib.parse.urlparse(normalized).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _valid_email(email: str) -> bool:
    email = email.lower().strip().strip(".,;:'\"()[]{}<>")
    if len(email) > 254 or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1]
    local = email.split("@", 1)[0]
    if local in IGNORE_EMAIL_LOCALS:
        return False
    if domain in IGNORE_EMAIL_DOMAINS or any(domain.endswith("." + d) for d in IGNORE_EMAIL_DOMAINS):
        return False
    if any(email.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
        return False
    return "." in domain


def _pick_email(candidates: list[str], website: str | None) -> str | None:
    site_domain = _domain(website)
    unique = []
    seen = set()
    for candidate in candidates:
        email = candidate.lower().strip().strip(".,;:'\"()[]{}<>")
        if _valid_email(email) and email not in seen:
            seen.add(email)
            unique.append(email)
    if not unique:
        return None

    def score(email: str) -> int:
        local, _, domain = email.partition("@")
        value = 0
        if site_domain and (domain == site_domain or domain.endswith("." + site_domain)):
            value += 100
        for index, preferred in enumerate(PREFERRED_EMAIL_LOCALS):
            if local == preferred or local.startswith(preferred):
                value += 50 - index
        if local in {"noreply", "no-reply", "donotreply", "do-not-reply"}:
            value -= 100
        return value

    return sorted(unique, key=score, reverse=True)[0]


def _fetch_url(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 Roadcall Directory Enrichment/1.0"},
    )
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(request, timeout=12, context=ctx) as response:
        raw = response.read(500_000)
        return raw.decode("utf-8", errors="ignore")


def find_website_email(website: str | None) -> str | None:
    base = _normalize_url(website)
    if not base:
        return None
    paths = ["", "/contact", "/contact-us", "/about", "/about-us"]
    found: list[str] = []
    for path in paths:
        url = base + path
        try:
            html = _fetch_url(url)
        except Exception:
            continue
        found.extend(EMAIL_RE.findall(html))
        if found:
            break
    return _pick_email(found, base)


def safer_lookup(company_name: str) -> tuple[str | None, str | None]:
    search_url = "https://safer.fmcsa.dot.gov/keywordx.asp?searchstring=" + urllib.parse.quote(company_name) + "&SEARCHTYPE="
    try:
        request = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0 Roadcall DOT Enrichment/1.0"})
        with urllib.request.urlopen(request, timeout=18) as response:
            html = response.read().decode("latin-1", errors="ignore")
    except Exception:
        return None, None
    dot_match = DOT_RE.search(html)
    mc_match = MC_RE.search(html)
    dot = dot_match.group(1) if dot_match else None
    mc = mc_match.group(1) if mc_match else None
    if dot and not mc:
        snapshot_url = "https://safer.fmcsa.dot.gov/query.asp?searchtype=ANY&query_type=queryCarrierSnapshot&query_param=USDOT&query_string=" + urllib.parse.quote(dot)
        try:
            request = urllib.request.Request(snapshot_url, headers={"User-Agent": "Mozilla/5.0 Roadcall DOT Enrichment/1.0"})
            with urllib.request.urlopen(request, timeout=18) as response:
                snapshot_html = response.read().decode("latin-1", errors="ignore")
            snapshot_mc = MC_RE.search(snapshot_html)
            mc = snapshot_mc.group(1) if snapshot_mc else None
        except Exception:
            pass
    return dot, mc


def tavily_search(query: str) -> dict[str, Any]:
    if not TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY is not configured")
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "include_raw_content": False,
        "max_results": 8,
    }
    request = urllib.request.Request(
        TAVILY_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _extract_from_tavily(data: dict[str, Any], website: str | None) -> tuple[str | None, str | None, str | None]:
    haystack_parts: list[str] = []
    if data.get("answer"):
        haystack_parts.append(str(data["answer"]))
    for result in data.get("results") or []:
        if not isinstance(result, dict):
            continue
        haystack_parts.extend(str(result.get(key) or "") for key in ("title", "url", "content"))
    haystack = "\n".join(haystack_parts)
    email = _pick_email(EMAIL_RE.findall(haystack), website)
    dot_match = DOT_RE.search(haystack)
    mc_match = MC_RE.search(haystack)
    return (
        email,
        dot_match.group(1) if dot_match else None,
        mc_match.group(1) if mc_match else None,
    )


def enrich_with_tavily(kind: str, limit: int, sleep_sec: float) -> tuple[int, int]:
    table = "trucking_companies" if kind == "trucking" else "national_vendors"
    name_col = "company_name" if kind == "trucking" else "location_name"
    select_extra = ", dot_number, mc_number" if kind == "trucking" else ""
    missing_clause = "(email IS NULL OR email = '' OR dot_number IS NULL OR dot_number = '' OR mc_number IS NULL OR mc_number = '')" if kind == "trucking" else "(email IS NULL OR email = '')"
    conn = _connect()
    attempted = updated = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, {name_col}, city, state, website{select_extra}
                FROM {table}
                WHERE {missing_clause}
                ORDER BY updated_at NULLS FIRST, id
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            for row in rows:
                attempted += 1
                row_id, name, city, state, website, *rest = row
                location = ", ".join(part for part in (city, state) if part)
                if kind == "trucking":
                    query = f'"{name}" trucking company {location} email USDOT MC number official website'
                else:
                    query = f'"{name}" {location} official email phone truck service location'
                try:
                    data = tavily_search(query)
                    email, dot, mc = _extract_from_tavily(data, website)
                except Exception as exc:
                    print(f"⚠ Tavily failed for {name}: {exc}")
                    continue

                if kind == "trucking":
                    cur.execute(
                        """
                        UPDATE trucking_companies
                        SET email = COALESCE(email, %s),
                            dot_number = COALESCE(dot_number, %s),
                            mc_number = COALESCE(mc_number, %s),
                            last_enriched_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                          AND ((email IS NULL OR email = '') OR (dot_number IS NULL OR dot_number = '') OR (mc_number IS NULL OR mc_number = ''))
                        """,
                        (email, dot, mc, row_id),
                    )
                    changed = bool(email or dot or mc)
                    if changed:
                        print(f"✓ {name} -> email={email or '-'} DOT={dot or '-'} MC={mc or '-'}")
                else:
                    cur.execute(
                        """
                        UPDATE national_vendors
                        SET email = COALESCE(email, %s),
                            last_enriched_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                          AND (email IS NULL OR email = '')
                        """,
                        (email, row_id),
                    )
                    changed = bool(email)
                    if changed:
                        print(f"✓ {name} -> {email}")
                updated += 1 if changed else 0
                conn.commit()
                if sleep_sec:
                    time.sleep(sleep_sec)
    finally:
        conn.close()
    return attempted, updated


def enrich_emails(kind: str, limit: int, sleep_sec: float) -> tuple[int, int]:
    table = "trucking_companies" if kind == "trucking" else "national_vendors"
    name_col = "company_name" if kind == "trucking" else "location_name"
    conn = _connect()
    updated = attempted = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, {name_col}, website
                FROM {table}
                WHERE website IS NOT NULL AND website <> ''
                  AND (email IS NULL OR email = '')
                ORDER BY updated_at NULLS FIRST, id
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            for row_id, name, website in rows:
                attempted += 1
                email = find_website_email(website)
                if email:
                    cur.execute(
                        f"UPDATE {table} SET email = %s, last_enriched_at = NOW(), updated_at = NOW() WHERE id = %s AND (email IS NULL OR email = '')",
                        (email, row_id),
                    )
                    updated += cur.rowcount
                    print(f"✓ {name} -> {email}")
                else:
                    cur.execute(f"UPDATE {table} SET last_enriched_at = NOW(), updated_at = NOW() WHERE id = %s", (row_id,))
                conn.commit()
                if sleep_sec:
                    time.sleep(sleep_sec)
    finally:
        conn.close()
    return attempted, updated


def enrich_dot_numbers(limit: int, sleep_sec: float) -> tuple[int, int, int]:
    conn = _connect()
    attempted = dot_updates = mc_updates = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, company_name
                FROM trucking_companies
                WHERE (dot_number IS NULL OR dot_number = '')
                ORDER BY updated_at NULLS FIRST, id
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
            for row_id, company_name in rows:
                attempted += 1
                dot, mc = safer_lookup(company_name)
                if dot or mc:
                    cur.execute(
                        """
                        UPDATE trucking_companies
                        SET dot_number = COALESCE(dot_number, %s),
                            mc_number = COALESCE(mc_number, %s),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (dot, mc, row_id),
                    )
                    dot_updates += 1 if dot else 0
                    mc_updates += 1 if mc else 0
                    print(f"✓ {company_name} -> DOT={dot or '-'} MC={mc or '-'}")
                if attempted % 25 == 0:
                    conn.commit()
                if sleep_sec:
                    time.sleep(sleep_sec)
            conn.commit()
    finally:
        conn.close()
    return attempted, dot_updates, mc_updates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emails", choices=["trucking", "vendors"], default=None)
    parser.add_argument("--email-limit", type=int, default=100)
    parser.add_argument("--dot-limit", type=int, default=0)
    parser.add_argument("--tavily", choices=["trucking", "vendors"], default=None, help="Use Tavily search to enrich missing email/DOT/MC values")
    parser.add_argument("--tavily-limit", type=int, default=25)
    parser.add_argument("--sleep", type=float, default=0.15)
    args = parser.parse_args()

    if args.tavily:
        attempted, updated = enrich_with_tavily(args.tavily, args.tavily_limit, args.sleep)
        print(f"Tavily enrichment complete: kind={args.tavily} attempted={attempted} updated={updated}")
    if args.emails:
        attempted, updated = enrich_emails(args.emails, args.email_limit, args.sleep)
        print(f"Email enrichment complete: kind={args.emails} attempted={attempted} updated={updated}")
    if args.dot_limit > 0:
        attempted, dot_updates, mc_updates = enrich_dot_numbers(args.dot_limit, args.sleep)
        print(f"DOT/MC enrichment complete: attempted={attempted} dot_updates={dot_updates} mc_updates={mc_updates}")
    if not args.tavily and not args.emails and args.dot_limit <= 0:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
