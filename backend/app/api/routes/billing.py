from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin_api_key
from app.core.config import get_settings
from app.schemas.billing import (
    AIActivationOut,
    BillingPlanView,
    CheckoutSessionCreateIn,
    CheckoutSessionCreateOut,
    CustomerPortalCreateIn,
    CustomerPortalCreateOut,
    MechanicDashboardView,
    ResendDashboardLinkIn,
    ResendDashboardLinkOut,
    ShopProfileUpdateIn,
)
from app.services.partner_badge_billing_service import PartnerBadgeBillingService
from app.services.subscription_billing_service import SubscriptionBillingService

router = APIRouter(prefix="/billing", tags=["billing"])
service = SubscriptionBillingService()


@router.get("/plans", response_model=list[BillingPlanView])
async def list_billing_plans():
    return service.billing_plan_views()


@router.post("/checkout", response_model=CheckoutSessionCreateOut)
async def create_checkout_session(payload: CheckoutSessionCreateIn, db: AsyncSession = Depends(get_db)):
    try:
        result = await service.create_checkout_session(db, payload)
        await db.commit()
        return CheckoutSessionCreateOut(**result)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not create Stripe checkout: {exc}") from exc


@router.post("/partner-badge/payment-link", dependencies=[Depends(require_admin_api_key)])
async def create_partner_badge_payment_link():
    try:
        return PartnerBadgeBillingService(get_settings()).create_or_reuse_payment_link()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Could not create Stripe payment link: {exc}") from exc


@router.post("/resend-dashboard-link", response_model=ResendDashboardLinkOut)
async def resend_dashboard_link(payload: ResendDashboardLinkIn, db: AsyncSession = Depends(get_db)):
    generic_message = (
        f"If an account exists for {payload.email}, we just re-sent the dashboard link."
    )
    # Fleet/admin do not have password-less magic-link dashboards yet; treat as no-op
    # but still respond generically so we never disclose account existence.
    if payload.vertical != "shop":
        return ResendDashboardLinkOut(message=generic_message)
    try:
        await service.resend_dashboard_link(db, payload.email)
    except Exception:  # noqa: BLE001 - never surface lookup/email errors to the caller
        pass
    return ResendDashboardLinkOut(message=generic_message)


@router.post("/customer-portal", response_model=CustomerPortalCreateOut)
async def create_customer_portal(payload: CustomerPortalCreateIn, db: AsyncSession = Depends(get_db)):
    try:
        url = await service.create_customer_portal(db, uuid.UUID(payload.tenant_id), payload.dashboard_token)
        return CustomerPortalCreateOut(portal_url=url)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/mechanic-dashboard/{tenant_id}", response_model=MechanicDashboardView)
async def mechanic_dashboard(tenant_id: str, token: str = Query(...), db: AsyncSession = Depends(get_db)):
    try:
        return MechanicDashboardView(**await service.dashboard(db, uuid.UUID(tenant_id), token))
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.patch("/mechanic-dashboard/{tenant_id}/profile", response_model=MechanicDashboardView)
async def update_mechanic_profile(
    tenant_id: str,
    payload: ShopProfileUpdateIn,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        await service.update_profile(db, uuid.UUID(tenant_id), token, payload)
        await db.commit()
        return MechanicDashboardView(**await service.dashboard(db, uuid.UUID(tenant_id), token))
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/mechanic-dashboard/{tenant_id}/activate-ai", response_model=AIActivationOut)
async def activate_mechanic_ai(tenant_id: str, token: str = Query(...), db: AsyncSession = Depends(get_db)):
    try:
        result = await service.activate_ai(db, uuid.UUID(tenant_id), token)
        await db.commit()
        return AIActivationOut(**result)
    except PermissionError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"AI activation failed: {exc}") from exc
