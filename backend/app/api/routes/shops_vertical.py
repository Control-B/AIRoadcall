"""
Roadcall Shops vertical API routes.

Profile, call stats, and settings endpoints for the Shops CRM vertical.
These complement the existing /shops telephony endpoints.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.organization import Organization, VerticalType
from app.models.shop_call_log import ShopCallLog
from app.models.shop_customer import ShopCustomer
from app.models.integration_connection import IntegrationConnection, IntegrationProvider

router = APIRouter(prefix="/shops/profile", tags=["shops-profile"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OrganizationCreate(BaseModel):
    name: str
    slug: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    is_active: Optional[bool] = None


class GhlIntegrationSettings(BaseModel):
    """GoHighLevel / LC Phone integration settings."""
    organization_id: str
    ghl_api_key: str
    ghl_location_id: str
    ghl_from_number: Optional[str] = None


# ---------------------------------------------------------------------------
# Organization / Profile endpoints
# ---------------------------------------------------------------------------

@router.post("/organizations")
async def create_shop_organization(payload: OrganizationCreate, db: AsyncSession = Depends(get_session)):
    """Create a new Shops vertical organization."""
    result = await db.execute(select(Organization).where(Organization.slug == payload.slug))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Slug already taken")
    org = Organization(
        name=payload.name,
        slug=payload.slug,
        vertical_type=VerticalType.shops,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        website=payload.website,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return {"organization_id": str(org.id), "slug": org.slug, "vertical_type": org.vertical_type}


@router.get("/organizations/{org_id}")
async def get_shop_organization(org_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Organization).where(Organization.id == uuid.UUID(org_id)))
    org = result.scalar_one_or_none()
    if not org or org.vertical_type != VerticalType.shops:
        raise HTTPException(status_code=404, detail="Shop organization not found")
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "contact_email": org.contact_email,
        "contact_phone": org.contact_phone,
        "website": org.website,
        "is_active": org.is_active,
        "created_at": org.created_at.isoformat(),
    }


@router.patch("/organizations/{org_id}")
async def update_shop_organization(org_id: str, payload: OrganizationUpdate, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Organization).where(Organization.id == uuid.UUID(org_id)))
    org = result.scalar_one_or_none()
    if not org or org.vertical_type != VerticalType.shops:
        raise HTTPException(status_code=404, detail="Shop organization not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(org, k, v)
    await db.commit()
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# Call stats
# ---------------------------------------------------------------------------

@router.get("/organizations/{org_id}/calls/stats")
async def get_call_stats(org_id: str, db: AsyncSession = Depends(get_session)):
    """Summary stats for the shop's call log."""
    from sqlalchemy import func
    cust_result = await db.execute(
        select(ShopCustomer).where(ShopCustomer.shop_id == uuid.UUID(org_id))
    )
    customers = cust_result.scalars().all()
    customer_ids = [c.id for c in customers]

    total_calls = 0
    if customer_ids:
        count_result = await db.execute(
            select(func.count()).select_from(ShopCallLog).where(
                ShopCallLog.shop_customer_id.in_(customer_ids)
            )
        )
        total_calls = count_result.scalar() or 0

    return {
        "organization_id": org_id,
        "total_customers": len(customers),
        "total_calls_logged": total_calls,
    }


# ---------------------------------------------------------------------------
# GHL integration settings
# ---------------------------------------------------------------------------

@router.post("/integrations/ghl")
async def save_ghl_integration(payload: GhlIntegrationSettings, db: AsyncSession = Depends(get_session)):
    """Save or update GHL/LC Phone integration credentials for a Shops org."""
    import json
    org_uuid = uuid.UUID(payload.organization_id)

    result = await db.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.organization_id == org_uuid,
            IntegrationConnection.provider == IntegrationProvider.ghl,
        )
    )
    existing = result.scalar_one_or_none()

    creds = {
        "api_key": payload.ghl_api_key,
        "location_id": payload.ghl_location_id,
        "from_number": payload.ghl_from_number,
    }

    if existing:
        existing.credentials_json = json.dumps(creds)
        existing.is_active = True
        await db.commit()
        return {"status": "updated"}

    conn = IntegrationConnection(
        organization_id=org_uuid,
        provider=IntegrationProvider.ghl,
        credentials_json=json.dumps(creds),
        is_active=True,
    )
    db.add(conn)
    await db.commit()
    return {"status": "created"}


@router.get("/integrations/{org_id}")
async def list_integrations(org_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(IntegrationConnection).where(
            IntegrationConnection.organization_id == uuid.UUID(org_id)
        )
    )
    conns = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "provider": c.provider,
            "is_active": c.is_active,
            "external_account_id": c.external_account_id,
        }
        for c in conns
    ]
