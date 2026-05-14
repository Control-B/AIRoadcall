"""Public, limited directory APIs for SEO-safe discovery pages.

These endpoints expose only display-safe directory fields: name, city/state,
phone, address, ratings, and public category/service labels. They intentionally
omit emails, websites, internal IDs, source URLs, coordinates, DOT/MC numbers,
and enrichment metadata. Admin-only APIs remain the source for full records.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.business_directory import NationalVendor, TruckingCompany

router = APIRouter(prefix="/directories", tags=["public-directories"])
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _like(term: str) -> str:
    return f"%{term.strip()}%"


def _split_public_tags(value: str | None, limit: int = 4) -> list[str]:
    if not value:
        return []
    raw = value.replace(";", ",").split(",")
    tags = []
    for tag in raw:
        cleaned = tag.strip()
        if cleaned and cleaned.lower() not in {t.lower() for t in tags}:
            tags.append(cleaned[:48])
        if len(tags) >= limit:
            break
    return tags


def _to_float(value: str | float | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: str | int | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=4)
def _load_csv(filename: str) -> list[dict[str, str]]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _contains(row: dict[str, str], term: str, fields: tuple[str, ...]) -> bool:
    needle = term.strip().lower()
    return any(needle in (row.get(field) or "").lower() for field in fields)


def _state_matches(row: dict[str, str], state: str | None) -> bool:
    return not state or (row.get("state") or "").upper() == state.upper()


def _csv_stats(rows: list[dict[str, str]]) -> dict:
    state_counts: dict[str, int] = {}
    for row in rows:
        state = (row.get("state") or "").upper()
        if state:
            state_counts[state] = state_counts.get(state, 0) + 1
    top_states = sorted(state_counts.items(), key=lambda item: item[1], reverse=True)[:12]
    return {
        "total": len(rows),
        "top_states": [{"state": state, "count": count} for state, count in top_states],
    }


def _public_trucking_row(row) -> dict:
    return {
        "company_name": row.company_name if hasattr(row, "company_name") else row.get("company_name"),
        "phone": row.phone if hasattr(row, "phone") else row.get("phone"),
        "address": row.address if hasattr(row, "address") else row.get("address"),
        "city": row.city if hasattr(row, "city") else row.get("city"),
        "state": row.state if hasattr(row, "state") else row.get("state"),
        "rating": row.rating if hasattr(row, "rating") else _to_float(row.get("rating")),
        "review_count": row.review_count if hasattr(row, "review_count") else _to_int(row.get("review_count")),
        "categories": _split_public_tags(row.categories if hasattr(row, "categories") else row.get("categories")),
    }


def _public_vendor_row(row) -> dict:
    return {
        "brand_name": row.brand_name if hasattr(row, "brand_name") else row.get("brand_name"),
        "location_name": row.location_name if hasattr(row, "location_name") else row.get("location_name"),
        "phone": row.phone if hasattr(row, "phone") else row.get("phone"),
        "address": row.address if hasattr(row, "address") else row.get("address"),
        "city": row.city if hasattr(row, "city") else row.get("city"),
        "state": row.state if hasattr(row, "state") else row.get("state"),
        "rating": row.rating if hasattr(row, "rating") else _to_float(row.get("rating")),
        "review_count": row.review_count if hasattr(row, "review_count") else _to_int(row.get("review_count")),
        "services": _split_public_tags((row.services or row.categories) if hasattr(row, "services") else (row.get("services") or row.get("categories"))),
    }


async def _public_stats(db: AsyncSession, model) -> dict:
    total = await db.scalar(select(func.count(model.id))) or 0
    state_rows = await db.execute(
        select(model.state, func.count(model.id))
        .where(model.state.isnot(None), model.state != "")
        .group_by(model.state)
        .order_by(func.count(model.id).desc())
        .limit(12)
    )
    return {
        "total": int(total),
        "top_states": [{"state": row[0], "count": int(row[1])} for row in state_rows.all()],
    }


@router.get("/trucking-companies/stats")
async def public_trucking_company_stats(db: AsyncSession = Depends(get_session)):
    stats = await _public_stats(db, TruckingCompany)
    if stats["total"] > 0:
        return stats
    return _csv_stats(_load_csv("trucking_companies_us.csv"))


@router.get("/trucking-companies")
async def public_trucking_companies(
    q: str | None = Query(default=None, max_length=80),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    limit: int = Query(default=24, ge=1, le=48),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    filters = []
    if q:
        term = _like(q)
        filters.append(or_(TruckingCompany.company_name.ilike(term), TruckingCompany.city.ilike(term), TruckingCompany.categories.ilike(term)))
    if state:
        filters.append(TruckingCompany.state == state.upper())

    count_query = select(func.count(TruckingCompany.id))
    data_query = (
        select(TruckingCompany)
        .order_by(TruckingCompany.state.asc(), TruckingCompany.city.asc(), TruckingCompany.company_name.asc())
        .limit(limit)
        .offset(offset)
    )
    for condition in filters:
        count_query = count_query.where(condition)
        data_query = data_query.where(condition)

    total = await db.scalar(count_query) or 0
    rows = list((await db.execute(data_query)).scalars().all())
    if not total:
        csv_rows = [
            row for row in _load_csv("trucking_companies_us.csv")
            if _state_matches(row, state)
            and (not q or _contains(row, q, ("company_name", "city", "state", "categories", "address", "phone")))
        ]
        return {
            "total": len(csv_rows),
            "limit": limit,
            "offset": offset,
            "items": [_public_trucking_row(row) for row in csv_rows[offset:offset + limit]],
        }
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [_public_trucking_row(row) for row in rows],
    }


@router.get("/national-vendors/stats")
async def public_national_vendor_stats(db: AsyncSession = Depends(get_session)):
    stats = await _public_stats(db, NationalVendor)
    if stats["total"] > 0:
        brand_rows = await db.execute(
            select(NationalVendor.brand_name, func.count(NationalVendor.id))
            .group_by(NationalVendor.brand_name)
            .order_by(func.count(NationalVendor.id).desc())
            .limit(16)
        )
        stats["brands"] = [{"brand": row[0], "count": int(row[1])} for row in brand_rows.all()]
        return stats
    csv_rows = _load_csv("national_vendors_us.csv")
    stats = _csv_stats(csv_rows)
    brand_counts: dict[str, int] = {}
    for row in csv_rows:
        brand = row.get("brand_name") or "Unknown"
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
    stats["brands"] = [
        {"brand": brand, "count": count}
        for brand, count in sorted(brand_counts.items(), key=lambda item: item[1], reverse=True)[:16]
    ]
    return stats


@router.get("/national-vendors")
async def public_national_vendors(
    q: str | None = Query(default=None, max_length=80),
    brand: str | None = Query(default=None, max_length=80),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    limit: int = Query(default=24, ge=1, le=48),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    filters = []
    if q:
        term = _like(q)
        filters.append(or_(NationalVendor.brand_name.ilike(term), NationalVendor.location_name.ilike(term), NationalVendor.city.ilike(term), NationalVendor.services.ilike(term)))
    if brand:
        filters.append(NationalVendor.brand_name.ilike(_like(brand)))
    if state:
        filters.append(NationalVendor.state == state.upper())

    count_query = select(func.count(NationalVendor.id))
    data_query = (
        select(NationalVendor)
        .order_by(NationalVendor.brand_name.asc(), NationalVendor.state.asc(), NationalVendor.city.asc())
        .limit(limit)
        .offset(offset)
    )
    for condition in filters:
        count_query = count_query.where(condition)
        data_query = data_query.where(condition)

    total = await db.scalar(count_query) or 0
    rows = list((await db.execute(data_query)).scalars().all())
    if not total:
        csv_rows = [
            row for row in _load_csv("national_vendors_us.csv")
            if _state_matches(row, state)
            and (not brand or brand.lower() in (row.get("brand_name") or "").lower())
            and (not q or _contains(row, q, ("brand_name", "location_name", "city", "state", "services", "categories", "address", "phone")))
        ]
        return {
            "total": len(csv_rows),
            "limit": limit,
            "offset": offset,
            "items": [_public_vendor_row(row) for row in csv_rows[offset:offset + limit]],
        }
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [_public_vendor_row(row) for row in rows],
    }
