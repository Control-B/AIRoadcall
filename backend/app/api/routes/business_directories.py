"""Secured admin APIs for trucking companies and national vendor directories."""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.admin_auth import verify_admin
from app.models.business_directory import NationalVendor, TruckingCompany

router = APIRouter(prefix="/admin/directories", tags=["admin", "directories"])
DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _like(term: str):
    return f"%{term.strip()}%"


@lru_cache(maxsize=4)
def _load_csv(filename: str) -> list[dict[str, str]]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


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


def _state_matches(row: dict[str, str], state: str | None) -> bool:
    return not state or (row.get("state") or "").upper() == state.upper()


def _contains(row: dict[str, str], term: str | None, fields: tuple[str, ...]) -> bool:
    if not term:
        return True
    needle = term.strip().lower()
    return any(needle in (row.get(field) or "").lower() for field in fields)


def _has_value(row: dict[str, str], key: str, expected: bool | None) -> bool:
    if expected is None:
        return True
    has_value = bool((row.get(key) or "").strip())
    return has_value is expected


def _csv_stats(rows: list[dict[str, str]]) -> dict:
    state_counts: dict[str, int] = {}
    for row in rows:
        state = (row.get("state") or "").upper()
        if state:
            state_counts[state] = state_counts.get(state, 0) + 1
    top_states = sorted(state_counts.items(), key=lambda item: item[1], reverse=True)[:15]
    return {
        "total": len(rows),
        "with_phone": sum(1 for row in rows if (row.get("phone") or "").strip()),
        "with_email": sum(1 for row in rows if (row.get("email") or "").strip()),
        "with_website": sum(1 for row in rows if (row.get("website") or "").strip()),
        "top_states": [{"state": state, "count": count} for state, count in top_states],
    }


def _admin_trucking_csv_row(row: dict[str, str], index: int) -> dict:
    return {
        "id": f"csv-trucking-{index}",
        "company_name": row.get("company_name") or "Unknown company",
        "phone": row.get("phone") or None,
        "email": row.get("email") or None,
        "website": row.get("website") or None,
        "address": row.get("address") or None,
        "city": row.get("city") or None,
        "state": row.get("state") or None,
        "rating": _to_float(row.get("rating")),
        "review_count": _to_int(row.get("review_count")),
        "dot_number": row.get("dot_number") or None,
        "mc_number": row.get("mc_number") or None,
        "source": row.get("source") or "csv_fallback",
        "source_url": row.get("source_url") or None,
        "last_enriched_at": None,
        "created_at": None,
    }


def _admin_vendor_csv_row(row: dict[str, str], index: int) -> dict:
    return {
        "id": f"csv-vendor-{index}",
        "brand_name": row.get("brand_name") or "Unknown vendor",
        "location_name": row.get("location_name") or row.get("brand_name") or "Unknown location",
        "phone": row.get("phone") or None,
        "email": row.get("email") or None,
        "website": row.get("website") or None,
        "address": row.get("address") or None,
        "city": row.get("city") or None,
        "state": row.get("state") or None,
        "rating": _to_float(row.get("rating")),
        "review_count": _to_int(row.get("review_count")),
        "services": row.get("services") or row.get("categories") or None,
        "source": row.get("source") or "csv_fallback",
        "source_url": row.get("source_url") or None,
        "last_enriched_at": None,
        "created_at": None,
    }


def _csv_page(rows: list[dict[str, str]], limit: int, offset: int) -> tuple[int, list[tuple[int, dict[str, str]]]]:
    indexed_rows = list(enumerate(rows))
    return len(indexed_rows), indexed_rows[offset:offset + limit]


async def _stats(db: AsyncSession, model) -> dict:
    total = await db.scalar(select(func.count(model.id))) or 0
    with_phone = await db.scalar(select(func.count(model.id)).where(model.phone.isnot(None), model.phone != "")) or 0
    with_email = await db.scalar(select(func.count(model.id)).where(model.email.isnot(None), model.email != "")) or 0
    with_website = await db.scalar(select(func.count(model.id)).where(model.website.isnot(None), model.website != "")) or 0
    state_rows = await db.execute(
        select(model.state, func.count(model.id))
        .where(model.state.isnot(None), model.state != "")
        .group_by(model.state)
        .order_by(func.count(model.id).desc())
        .limit(15)
    )
    return {
        "total": int(total),
        "with_phone": int(with_phone),
        "with_email": int(with_email),
        "with_website": int(with_website),
        "top_states": [{"state": row[0], "count": row[1]} for row in state_rows.all()],
    }


@router.get("/trucking-companies/stats", dependencies=[Depends(verify_admin)])
async def trucking_company_stats(db: AsyncSession = Depends(get_session)):
    stats = await _stats(db, TruckingCompany)
    if stats["total"] == 0:
        rows = _load_csv("trucking_companies_us.csv")
        csv_stats = _csv_stats(rows)
        csv_stats.update({
            "with_dot": sum(1 for row in rows if (row.get("dot_number") or "").strip()),
            "with_mc": sum(1 for row in rows if (row.get("mc_number") or "").strip()),
        })
        return csv_stats
    with_dot = await db.scalar(select(func.count(TruckingCompany.id)).where(TruckingCompany.dot_number.isnot(None), TruckingCompany.dot_number != "")) or 0
    with_mc = await db.scalar(select(func.count(TruckingCompany.id)).where(TruckingCompany.mc_number.isnot(None), TruckingCompany.mc_number != "")) or 0
    stats.update({"with_dot": int(with_dot), "with_mc": int(with_mc)})
    return stats


@router.get("/trucking-companies", dependencies=[Depends(verify_admin)])
async def list_trucking_companies(
    q: str | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    has_email: bool | None = Query(default=None),
    has_dot: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    filters = []
    if q:
        term = _like(q)
        filters.append(or_(
            TruckingCompany.company_name.ilike(term),
            TruckingCompany.phone.ilike(term),
            TruckingCompany.email.ilike(term),
            TruckingCompany.website.ilike(term),
            TruckingCompany.address.ilike(term),
            TruckingCompany.city.ilike(term),
            TruckingCompany.dot_number.ilike(term),
            TruckingCompany.mc_number.ilike(term),
        ))
    if state:
        filters.append(TruckingCompany.state == state.upper())
    if has_email is True:
        filters.extend([TruckingCompany.email.isnot(None), TruckingCompany.email != ""])
    elif has_email is False:
        filters.append(or_(TruckingCompany.email.is_(None), TruckingCompany.email == ""))
    if has_dot is True:
        filters.extend([TruckingCompany.dot_number.isnot(None), TruckingCompany.dot_number != ""])
    elif has_dot is False:
        filters.append(or_(TruckingCompany.dot_number.is_(None), TruckingCompany.dot_number == ""))

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
    if total == 0 and not await db.scalar(select(func.count(TruckingCompany.id))):
        csv_rows = [
            row for row in _load_csv("trucking_companies_us.csv")
            if _state_matches(row, state)
            and _contains(row, q, ("company_name", "phone", "email", "website", "address", "city", "state", "categories", "dot_number", "mc_number"))
            and _has_value(row, "email", has_email)
            and _has_value(row, "dot_number", has_dot)
        ]
        csv_total, csv_page = _csv_page(csv_rows, limit, offset)
        return {
            "total": csv_total,
            "limit": limit,
            "offset": offset,
            "items": [_admin_trucking_csv_row(row, index) for index, row in csv_page],
        }
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(row.id),
                "company_name": row.company_name,
                "phone": row.phone,
                "email": row.email,
                "website": row.website,
                "address": row.address,
                "city": row.city,
                "state": row.state,
                "rating": row.rating,
                "review_count": row.review_count,
                "dot_number": row.dot_number,
                "mc_number": row.mc_number,
                "source": row.source,
                "source_url": row.source_url,
                "last_enriched_at": row.last_enriched_at,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }


@router.get("/national-vendors/stats", dependencies=[Depends(verify_admin)])
async def national_vendor_stats(db: AsyncSession = Depends(get_session)):
    stats = await _stats(db, NationalVendor)
    if stats["total"] == 0:
        rows = _load_csv("national_vendors_us.csv")
        csv_stats = _csv_stats(rows)
        brand_counts: dict[str, int] = {}
        for row in rows:
            brand = row.get("brand_name") or "Unknown"
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
        csv_stats["brands"] = [
            {"brand": brand, "count": count}
            for brand, count in sorted(brand_counts.items(), key=lambda item: item[1], reverse=True)[:30]
        ]
        return csv_stats
    brand_rows = await db.execute(
        select(NationalVendor.brand_name, func.count(NationalVendor.id))
        .group_by(NationalVendor.brand_name)
        .order_by(func.count(NationalVendor.id).desc())
        .limit(30)
    )
    stats["brands"] = [{"brand": row[0], "count": row[1]} for row in brand_rows.all()]
    return stats


@router.get("/national-vendors", dependencies=[Depends(verify_admin)])
async def list_national_vendors(
    q: str | None = Query(default=None),
    brand: str | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    has_email: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    filters = []
    if q:
        term = _like(q)
        filters.append(or_(
            NationalVendor.brand_name.ilike(term),
            NationalVendor.location_name.ilike(term),
            NationalVendor.phone.ilike(term),
            NationalVendor.email.ilike(term),
            NationalVendor.website.ilike(term),
            NationalVendor.address.ilike(term),
            NationalVendor.city.ilike(term),
            NationalVendor.services.ilike(term),
        ))
    if brand:
        filters.append(NationalVendor.brand_name.ilike(_like(brand)))
    if state:
        filters.append(NationalVendor.state == state.upper())
    if has_email is True:
        filters.extend([NationalVendor.email.isnot(None), NationalVendor.email != ""])
    elif has_email is False:
        filters.append(or_(NationalVendor.email.is_(None), NationalVendor.email == ""))

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
    if total == 0 and not await db.scalar(select(func.count(NationalVendor.id))):
        csv_rows = [
            row for row in _load_csv("national_vendors_us.csv")
            if _state_matches(row, state)
            and (not brand or brand.lower() in (row.get("brand_name") or "").lower())
            and _contains(row, q, ("brand_name", "location_name", "phone", "email", "website", "address", "city", "state", "categories", "services"))
            and _has_value(row, "email", has_email)
        ]
        csv_total, csv_page = _csv_page(csv_rows, limit, offset)
        return {
            "total": csv_total,
            "limit": limit,
            "offset": offset,
            "items": [_admin_vendor_csv_row(row, index) for index, row in csv_page],
        }
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(row.id),
                "brand_name": row.brand_name,
                "location_name": row.location_name,
                "phone": row.phone,
                "email": row.email,
                "website": row.website,
                "address": row.address,
                "city": row.city,
                "state": row.state,
                "rating": row.rating,
                "review_count": row.review_count,
                "services": row.services,
                "source": row.source,
                "source_url": row.source_url,
                "last_enriched_at": row.last_enriched_at,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }
