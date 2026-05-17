from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.routes.admin_auth import verify_admin
from app.core.plan_config import get_plan_config, get_plan_configs, plan_payload
from app.models.tenant_provisioning import DispatchEvent, GHLConnection, ProvisioningEvent, Tenant
from app.schemas.provisioning import (
    DispatchEventView,
    FeatureFlagUpdateIn,
    GHLConnectionView,
    PlanAccessView,
    PlanConfigView,
    ProvisionTenantIn,
    ProvisionTenantOut,
    ProvisioningEventView,
    TenantGHLRepairIn,
    TenantListResponse,
    TenantPlanUpdateIn,
    TenantView,
)
from app.services.provisioning_service import ProvisioningService, all_feature_values, locked_features_for

router = APIRouter(prefix="/provisioning", tags=["provisioning"])
service = ProvisioningService()


def _connection_view(connection: GHLConnection | None) -> GHLConnectionView | None:
    if not connection:
        return None
    return GHLConnectionView(
        location_id=connection.location_id,
        subaccount_name=connection.subaccount_name,
        snapshot_id=connection.snapshot_id,
        snapshot_status=connection.snapshot_status,
        connection_status=connection.connection_status,
        last_synced_at=connection.last_synced_at,
    )


def _tenant_view(tenant: Tenant, connection: GHLConnection | None = None) -> TenantView:
    return TenantView(
        id=str(tenant.id),
        organization_id=str(tenant.organization_id),
        name=tenant.name,
        slug=tenant.slug,
        current_plan=tenant.current_plan,
        subscription_status=tenant.subscription_status,
        onboarding_status=tenant.onboarding_status,
        setup_fee_status=tenant.setup_fee_status,
        enabled_features=tenant.enabled_features or [],
        locked_features=locked_features_for(tenant.current_plan, tenant.enabled_features or []),
        ghl_connection=_connection_view(connection),
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


def _event_view(event: ProvisioningEvent) -> ProvisioningEventView:
    return ProvisioningEventView(
        id=str(event.id),
        tenant_id=str(event.tenant_id) if event.tenant_id else None,
        organization_id=str(event.organization_id) if event.organization_id else None,
        event_type=event.event_type,
        source=event.source,
        status=event.status,
        error_message=event.error_message,
        retry_count=event.retry_count,
        created_at=event.created_at,
    )


@router.get("/plans", response_model=list[PlanConfigView])
async def list_plans():
    return [PlanConfigView(**plan_payload(config)) for config in get_plan_configs().values()]


@router.post("/tenants", response_model=ProvisionTenantOut, dependencies=[Depends(verify_admin)])
async def provision_tenant(payload: ProvisionTenantIn, db: AsyncSession = Depends(get_db)):
    try:
        tenant, plan, event, ghl_result, warnings = await service.provision_tenant(db, payload)
        result = await db.execute(select(GHLConnection).where(GHLConnection.tenant_id == tenant.id))
        connection = result.scalar_one_or_none()
        await db.commit()
        await db.refresh(tenant)
        return ProvisionTenantOut(
            tenant=_tenant_view(tenant, connection),
            plan=PlanConfigView(**plan),
            provisioning_event_id=str(event.id),
            ghl_result=ghl_result,
            warnings=warnings,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Provisioning failed: {exc}") from exc


@router.get("/admin/tenants", response_model=TenantListResponse, dependencies=[Depends(verify_admin)])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    pairs = await service.list_tenants(db)
    return TenantListResponse(
        tenants=[_tenant_view(tenant, connection) for tenant, connection in pairs],
        plans=[PlanConfigView(**plan_payload(config)) for config in get_plan_configs().values()],
    )


@router.patch("/admin/tenants/{tenant_id}/plan", response_model=TenantView, dependencies=[Depends(verify_admin)])
async def update_tenant_plan(tenant_id: str, payload: TenantPlanUpdateIn, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, uuid.UUID(tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    plan_config = get_plan_config(payload.plan_id)
    tenant.current_plan = plan_config.id.value
    tenant.enabled_features = [feature.value for feature in plan_config.features]
    if payload.subscription_status:
        tenant.subscription_status = payload.subscription_status
    if payload.setup_fee_status:
        tenant.setup_fee_status = payload.setup_fee_status
    if payload.onboarding_status:
        tenant.onboarding_status = payload.onboarding_status
    for feature in tenant.enabled_features:
        await service.set_feature_flag(db, tenant.id, feature, True, "plan_change")
    result = await db.execute(select(GHLConnection).where(GHLConnection.tenant_id == tenant.id))
    connection = result.scalar_one_or_none()
    if connection:
        connection.snapshot_id = payload.ghl_snapshot_id or plan_config.snapshot_id
        connection.snapshot_status = "pending"
    await service.record_event(db, event_type="subscription.updated", tenant_id=tenant.id, organization_id=tenant.organization_id, status="plan_updated", payload={"plan_id": tenant.current_plan})
    await db.commit()
    return _tenant_view(tenant, connection)


@router.patch("/admin/tenants/{tenant_id}/ghl", response_model=TenantView, dependencies=[Depends(verify_admin)])
async def repair_tenant_ghl(tenant_id: str, payload: TenantGHLRepairIn, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, uuid.UUID(tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    result = await db.execute(select(GHLConnection).where(GHLConnection.tenant_id == tenant.id))
    connection = result.scalar_one_or_none()
    if connection is None:
        connection = GHLConnection(tenant_id=tenant.id, organization_id=tenant.organization_id)
        db.add(connection)
    for field in ("location_id", "subaccount_name", "snapshot_id", "snapshot_status", "connection_status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(connection, field, value)
    await service.record_event(db, event_type="ghl.location.created", tenant_id=tenant.id, organization_id=tenant.organization_id, status="manual_repair", payload=payload.model_dump(exclude_none=True))
    await db.commit()
    return _tenant_view(tenant, connection)


@router.patch("/admin/tenants/{tenant_id}/features", response_model=PlanAccessView, dependencies=[Depends(verify_admin)])
async def update_feature_flag(tenant_id: str, payload: FeatureFlagUpdateIn, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, uuid.UUID(tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await service.set_feature_flag(db, tenant.id, payload.feature, payload.enabled, "admin", payload.reason)
    await db.commit()
    return PlanAccessView(allowed=payload.enabled, tenant_id=str(tenant.id), plan_id=tenant.current_plan, feature=payload.feature, detail="Feature flag updated")


@router.post("/admin/provisioning-events/{event_id}/retry", response_model=ProvisioningEventView, dependencies=[Depends(verify_admin)])
async def retry_provisioning_event(event_id: str, db: AsyncSession = Depends(get_db)):
    try:
        event = await service.retry_failed_provisioning(db, uuid.UUID(event_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    return _event_view(event)


@router.get("/admin/provisioning-events", response_model=list[ProvisioningEventView], dependencies=[Depends(verify_admin)])
async def list_provisioning_events(db: AsyncSession = Depends(get_db), limit: int = 50):
    result = await db.execute(select(ProvisioningEvent).order_by(ProvisioningEvent.created_at.desc()).limit(min(limit, 200)))
    return [_event_view(event) for event in result.scalars().all()]


@router.get("/admin/dispatch-events", response_model=list[DispatchEventView], dependencies=[Depends(verify_admin)])
async def list_dispatch_events(db: AsyncSession = Depends(get_db), tenant_id: str | None = None, limit: int = 50):
    events = await service.latest_dispatch_events(db, uuid.UUID(tenant_id) if tenant_id else None, min(limit, 200))
    return [
        DispatchEventView(
            id=str(event.id),
            tenant_id=str(event.tenant_id) if event.tenant_id else None,
            organization_id=str(event.organization_id) if event.organization_id else None,
            incident_id=str(event.incident_id) if event.incident_id else None,
            job_id=str(event.job_id) if event.job_id else None,
            event_type=event.event_type,
            status=event.status,
            payload_json=event.payload_json,
            created_at=event.created_at,
        )
        for event in events
    ]


@router.get("/features/check", response_model=PlanAccessView)
async def check_feature_access(tenant_id: str, feature: str, db: AsyncSession = Depends(get_db)):
    if feature not in all_feature_values():
        raise HTTPException(status_code=400, detail="Unknown feature")
    allowed, tenant = await service.tenant_has_feature(db, uuid.UUID(tenant_id), feature)
    upgrade_required = None
    if not allowed:
        for plan_id in ("standard", "professional", "premium"):
            config = get_plan_config(plan_id)
            if feature in [item.value for item in config.features]:
                upgrade_required = plan_id
                break
    return PlanAccessView(
        allowed=allowed,
        tenant_id=str(tenant.id) if tenant else None,
        plan_id=tenant.current_plan if tenant else None,
        feature=feature,
        upgrade_required=upgrade_required,
        detail="Feature enabled" if allowed else "Feature locked for this plan",
    )