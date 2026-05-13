"""Secured admin APIs for trucking companies and national vendor directories."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.admin_auth import verify_admin
from app.models.business_directory import NationalVendor, TruckingCompany

router = APIRouter(prefix="/admin/directories", tags=["admin", "directories"])


def _like(term: str):
    return f"%{term.strip()}%"


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
