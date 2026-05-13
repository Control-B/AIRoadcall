"""Public, limited directory APIs for SEO-safe discovery pages.

These endpoints intentionally omit contact details, precise addresses, IDs,
source URLs, coordinates, DOT/MC numbers, and enrichment metadata. Admin-only
APIs remain the source for full records.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.business_directory import NationalVendor, TruckingCompany

router = APIRouter(prefix="/directories", tags=["public-directories"])


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
    return await _public_stats(db, TruckingCompany)


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
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "company_name": row.company_name,
                "city": row.city,
                "state": row.state,
                "rating": row.rating,
                "review_count": row.review_count,
                "categories": _split_public_tags(row.categories),
            }
            for row in rows
        ],
    }


@router.get("/national-vendors/stats")
async def public_national_vendor_stats(db: AsyncSession = Depends(get_session)):
    stats = await _public_stats(db, NationalVendor)
    brand_rows = await db.execute(
        select(NationalVendor.brand_name, func.count(NationalVendor.id))
        .group_by(NationalVendor.brand_name)
        .order_by(func.count(NationalVendor.id).desc())
        .limit(16)
    )
    stats["brands"] = [{"brand": row[0], "count": int(row[1])} for row in brand_rows.all()]
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
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "brand_name": row.brand_name,
                "location_name": row.location_name,
                "city": row.city,
                "state": row.state,
                "rating": row.rating,
                "review_count": row.review_count,
                "services": _split_public_tags(row.services or row.categories),
            }
            for row in rows
        ],
    }
