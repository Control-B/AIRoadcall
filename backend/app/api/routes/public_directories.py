"""Public, limited directory APIs for SEO-safe discovery pages.

These endpoints expose only display-safe directory fields: name, city/state,
phone, address, ratings, public category/service labels, and map coordinates.
They intentionally omit emails, websites, internal IDs, source URLs, DOT/MC
numbers, and enrichment metadata. Admin-only APIs remain the source for full records.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.business_directory import NationalVendor, TruckingCompany

router = APIRouter(prefix="/directories", tags=["public-directories"])
DATA_DIR = Path(__file__).resolve().parents[3] / "data"
US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}
CANADIAN_PROVINCE_CODES = {
    "AB", "ALBERTA", "BC", "BRITISH COLUMBIA", "MB", "MANITOBA", "NB", "NEW BRUNSWICK",
    "NL", "NEWFOUNDLAND AND LABRADOR", "NS", "NOVA SCOTIA", "NT", "NORTHWEST TERRITORIES",
    "NU", "NUNAVUT", "ON", "ONTARIO", "PE", "PRINCE EDWARD ISLAND", "QC", "QUEBEC",
    "SK", "SASKATCHEWAN", "YT", "YUKON",
}
MEXICAN_STATE_NAMES = {
    "AGUASCALIENTES", "BAJA CALIFORNIA", "BAJA CALIFORNIA SUR", "CAMPECHE", "CHIAPAS",
    "CHIHUAHUA", "CIUDAD DE MEXICO", "COAHUILA", "COLIMA", "DURANGO",
    "GUANAJUATO", "GUERRERO", "HIDALGO", "JALISCO", "MEXICO", "MICHOACAN",
    "MORELOS", "NAYARIT", "NUEVO LEON", "OAXACA", "PUEBLA",
    "QUERETARO", "QUINTANA ROO", "SAN LUIS POTOSI",
    "SINALOA", "SONORA", "TABASCO", "TAMAULIPAS", "TLAXCALA", "VERACRUZ", "YUCATAN",
    "YUCATÁN", "ZACATECAS",
}
NORTH_AMERICA_STATE_CODES = US_STATE_CODES | CANADIAN_PROVINCE_CODES | MEXICAN_STATE_NAMES
NORTH_AMERICA_COUNTRY_TERMS = ("united states", "usa", "u.s.a", "canada", "mexico")
NORTH_AMERICA_BOUNDS = {
    "min_lat": 7.0,
    "max_lat": 84.0,
    "min_lng": -170.0,
    "max_lng": -52.0,
}


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


def _is_north_america_coordinate(lat: float | None, lng: float | None) -> bool:
    return (
        lat is not None
        and lng is not None
        and NORTH_AMERICA_BOUNDS["min_lat"] <= lat <= NORTH_AMERICA_BOUNDS["max_lat"]
        and NORTH_AMERICA_BOUNDS["min_lng"] <= lng <= NORTH_AMERICA_BOUNDS["max_lng"]
    )


def _is_north_america_directory_row(row: dict[str, str]) -> bool:
    state = (row.get("state") or "").strip().upper()
    if state in NORTH_AMERICA_STATE_CODES:
        return True
    if _is_north_america_coordinate(_to_float(row.get("lat")), _to_float(row.get("lng"))):
        return True
    address = (row.get("address") or "").lower()
    return any(term in address for term in NORTH_AMERICA_COUNTRY_TERMS)


def _north_america_db_condition(model):
    return or_(
        func.upper(model.state).in_(NORTH_AMERICA_STATE_CODES),
        and_(
            model.lat >= NORTH_AMERICA_BOUNDS["min_lat"],
            model.lat <= NORTH_AMERICA_BOUNDS["max_lat"],
            model.lng >= NORTH_AMERICA_BOUNDS["min_lng"],
            model.lng <= NORTH_AMERICA_BOUNDS["max_lng"],
        ),
        model.address.ilike("%United States%"),
        model.address.ilike("%USA%"),
        model.address.ilike("%Canada%"),
        model.address.ilike("%Mexico%"),
    )


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
    address = row.address if hasattr(row, "address") else row.get("address")
    city = row.city if hasattr(row, "city") else row.get("city")
    state = row.state if hasattr(row, "state") else row.get("state")
    has_place = bool(address or (city and state))
    return {
        "company_name": row.company_name if hasattr(row, "company_name") else row.get("company_name"),
        "phone": row.phone if hasattr(row, "phone") else row.get("phone"),
        "website": row.website if hasattr(row, "website") else row.get("website"),
        "address": address,
        "city": city,
        "state": state,
        "lat": (row.lat if hasattr(row, "lat") else _to_float(row.get("lat"))) if has_place else None,
        "lng": (row.lng if hasattr(row, "lng") else _to_float(row.get("lng"))) if has_place else None,
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
        "lat": row.lat if hasattr(row, "lat") else _to_float(row.get("lat")),
        "lng": row.lng if hasattr(row, "lng") else _to_float(row.get("lng")),
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
    total = await db.scalar(select(func.count(TruckingCompany.id)).where(_north_america_db_condition(TruckingCompany))) or 0
    if total > 0:
        state_rows = await db.execute(
            select(TruckingCompany.state, func.count(TruckingCompany.id))
            .where(_north_america_db_condition(TruckingCompany))
            .group_by(TruckingCompany.state)
            .order_by(func.count(TruckingCompany.id).desc())
            .limit(12)
        )
        return {
            "total": int(total),
            "top_states": [{"state": row[0], "count": int(row[1])} for row in state_rows.all()],
        }
    stats = _csv_stats([row for row in _load_csv("trucking_companies_us.csv") if _is_north_america_directory_row(row)])
    if stats["total"] > 0:
        return stats
    return stats


@router.get("/trucking-companies")
async def public_trucking_companies(
    q: str | None = Query(default=None, max_length=80),
    city: str | None = Query(default=None, max_length=80),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
    min_lng: float | None = Query(default=None, ge=-180, le=180),
    max_lng: float | None = Query(default=None, ge=-180, le=180),
    limit: int = Query(default=24, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    filters = [_north_america_db_condition(TruckingCompany)]
    if q:
        term = _like(q)
        filters.append(or_(TruckingCompany.company_name.ilike(term), TruckingCompany.city.ilike(term), TruckingCompany.categories.ilike(term), TruckingCompany.address.ilike(term), TruckingCompany.phone.ilike(term)))
    if city:
        filters.append(TruckingCompany.city.ilike(_like(city)))
    if state:
        filters.append(TruckingCompany.state == state.upper())
    if min_lat is not None:
        filters.append(TruckingCompany.lat >= min_lat)
    if max_lat is not None:
        filters.append(TruckingCompany.lat <= max_lat)
    if min_lng is not None:
        filters.append(TruckingCompany.lng >= min_lng)
    if max_lng is not None:
        filters.append(TruckingCompany.lng <= max_lng)

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
            if _is_north_america_directory_row(row)
            and _state_matches(row, state)
            and (not city or city.lower() in (row.get("city") or "").lower())
            and (not q or _contains(row, q, ("company_name", "city", "state", "categories", "address", "phone")))
            and (min_lat is None or ((_to_float(row.get("lat")) is not None) and _to_float(row.get("lat")) >= min_lat))
            and (max_lat is None or ((_to_float(row.get("lat")) is not None) and _to_float(row.get("lat")) <= max_lat))
            and (min_lng is None or ((_to_float(row.get("lng")) is not None) and _to_float(row.get("lng")) >= min_lng))
            and (max_lng is None or ((_to_float(row.get("lng")) is not None) and _to_float(row.get("lng")) <= max_lng))
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
    city: str | None = Query(default=None, max_length=80),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    min_lat: float | None = Query(default=None, ge=-90, le=90),
    max_lat: float | None = Query(default=None, ge=-90, le=90),
    min_lng: float | None = Query(default=None, ge=-180, le=180),
    max_lng: float | None = Query(default=None, ge=-180, le=180),
    limit: int = Query(default=24, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
):
    filters = []
    if q:
        term = _like(q)
        filters.append(or_(NationalVendor.brand_name.ilike(term), NationalVendor.location_name.ilike(term), NationalVendor.city.ilike(term), NationalVendor.services.ilike(term)))
    if brand:
        filters.append(NationalVendor.brand_name.ilike(_like(brand)))
    if city:
        filters.append(NationalVendor.city.ilike(_like(city)))
    if state:
        filters.append(NationalVendor.state == state.upper())
    if min_lat is not None:
        filters.append(NationalVendor.lat >= min_lat)
    if max_lat is not None:
        filters.append(NationalVendor.lat <= max_lat)
    if min_lng is not None:
        filters.append(NationalVendor.lng >= min_lng)
    if max_lng is not None:
        filters.append(NationalVendor.lng <= max_lng)

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
            and (not city or city.lower() in (row.get("city") or "").lower())
            and (not brand or brand.lower() in (row.get("brand_name") or "").lower())
            and (not q or _contains(row, q, ("brand_name", "location_name", "city", "state", "services", "categories", "address", "phone")))
            and (min_lat is None or ((_to_float(row.get("lat")) is not None) and _to_float(row.get("lat")) >= min_lat))
            and (max_lat is None or ((_to_float(row.get("lat")) is not None) and _to_float(row.get("lat")) <= max_lat))
            and (min_lng is None or ((_to_float(row.get("lng")) is not None) and _to_float(row.get("lng")) >= min_lng))
            and (max_lng is None or ((_to_float(row.get("lng")) is not None) and _to_float(row.get("lng")) <= max_lng))
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
