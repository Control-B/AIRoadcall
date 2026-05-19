from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin_api_key
from app.api.routes.admin_auth import verify_admin
from app.core.plan_config import get_plan_config, get_plan_configs, plan_payload
from app.models.tenant_provisioning import (
    DispatchEvent,
    GHLConnection,
    ProvisioningEvent,
    RetellConnection,
    ShopAutomationWorkflow,
    ShopMessagingConfig,
    ShopOnboardingTask,
    ShopProvisioningSnapshot,
    Tenant,
)
from app.models.fleet_profile import FleetProfile
from app.models.mechanic_subscription import PlanUsage, ShopCall
from app.models.organization import Organization
from app.models.vehicle import Vehicle
from app.schemas.provisioning import (
    DispatchEventView,
    FeatureFlagUpdateIn,
    GHLConnectionView,
    PlanAccessView,
    PlanConfigView,
    ProvisioningSnapshotView,
    ProvisionTenantIn,
    ProvisionTenantOut,
    ProvisioningEventView,
    RetellConnectionView,
    ShopAutomationWorkflowView,
    ShopMessagingConfigView,
    ShopOnboardingTaskView,
    ShopSnapshotProvisionIn,
    ShopSnapshotProvisionOut,
    ShopSnapshotRecordView,
    TenantGHLRepairIn,
    TenantListResponse,
    TenantPlanUpdateIn,
    TenantRetellProvisionIn,
    TenantView,
)
from app.services.provisioning_service import ProvisioningService, all_feature_values, locked_features_for
from app.services.shop_snapshot_service import ShopSnapshotService

router = APIRouter(prefix="/provisioning", tags=["provisioning"])
service = ProvisioningService()
shop_snapshot_service = ShopSnapshotService()


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


def _retell_connection_view(connection: RetellConnection | None) -> RetellConnectionView | None:
    if not connection:
        return None
    metadata = connection.metadata_json or {}
    return RetellConnectionView(
        agent_id=connection.agent_id,
        conversation_flow_id=connection.conversation_flow_id,
        phone_number_id=connection.phone_number_id,
        agent_name=connection.agent_name,
        provisioning_status=connection.provisioning_status,
        last_error=connection.last_error,
        last_synced_at=connection.last_synced_at,
        dynamic_variables=metadata.get("dynamic_variables") or {},
    )


def _metadata_value(metadata: dict, *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    dynamic_variables = metadata.get("dynamic_variables")
    if isinstance(dynamic_variables, dict):
        for key in keys:
            value = dynamic_variables.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _tenant_view(
    tenant: Tenant,
    connection: GHLConnection | None = None,
    retell_connection: RetellConnection | None = None,
    latest_activity: DispatchEvent | ProvisioningEvent | None = None,
    operations: dict | None = None,
) -> TenantView:
    operations = operations or {}
    metadata = retell_connection.metadata_json if retell_connection and retell_connection.metadata_json else {}
    return TenantView(
        id=str(tenant.id),
        organization_id=str(tenant.organization_id),
        name=tenant.name,
        slug=tenant.slug,
        vertical_type=operations.get("vertical_type") or "shops",
        contact_email=getattr(tenant, "contact_email", None),
        contact_phone=getattr(tenant, "contact_phone", None),
        current_plan=tenant.current_plan,
        subscription_status=tenant.subscription_status,
        onboarding_status=tenant.onboarding_status,
        setup_fee_status=tenant.setup_fee_status,
        enabled_features=tenant.enabled_features or [],
        locked_features=locked_features_for(tenant.current_plan, tenant.enabled_features or []),
        ghl_connection=_connection_view(connection),
        retell_connection=_retell_connection_view(retell_connection),
        latest_activity_type=latest_activity.event_type if latest_activity else None,
        latest_activity_status=latest_activity.status if latest_activity else None,
        latest_activity_at=latest_activity.created_at if latest_activity else None,
        llm_model=operations.get("llm_model") or _metadata_value(metadata, "llm_model", "language_model", "model") or "Retell conversation flow",
        voice_id=operations.get("voice_id") or _metadata_value(metadata, "voice_id", "retell_voice_id"),
        calls_handled=operations.get("calls_handled", 0),
        leads_allocated=operations.get("leads_allocated", 0),
        vehicle_count=operations.get("vehicle_count", 0),
        fleet_size=operations.get("fleet_size"),
        snapshot_status=operations.get("snapshot_status"),
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
    )


def _snapshot_status(vertical_type: str, shop_snapshot: ShopProvisioningSnapshot | None, fleet_size: int | None, vehicle_count: int) -> str:
    if vertical_type == "fleet":
        return "ready" if (fleet_size or vehicle_count) else "needs_fleet_profile"
    if shop_snapshot:
        return shop_snapshot.status
    return "not_created"


def _snapshot_rollups(tenants: list[TenantView]) -> list[ProvisioningSnapshotView]:
    config = {
        "shops": {
            "label": "Shop AI Snapshot",
            "description": "Provision repair shops, AI reception, SMS follow-up, CRM sync, and lead intake.",
        },
        "fleet": {
            "label": "Fleet AI Snapshot",
            "description": "Provision fleet accounts, dispatch workflows, vehicles, roadside intake, and fleet notifications.",
        },
    }
    snapshots: list[ProvisioningSnapshotView] = []
    for vertical_type, details in config.items():
        scoped = [tenant for tenant in tenants if tenant.vertical_type == vertical_type]
        snapshots.append(
            ProvisioningSnapshotView(
                vertical_type=vertical_type,
                label=details["label"],
                description=details["description"],
                tenant_count=len(scoped),
                active_subscribers=sum(1 for tenant in scoped if tenant.is_active and tenant.subscription_status == "active"),
                ai_phone_active=sum(1 for tenant in scoped if tenant.retell_connection and tenant.retell_connection.provisioning_status == "active"),
                calls_handled=sum(tenant.calls_handled for tenant in scoped),
                vehicle_count=sum(tenant.vehicle_count for tenant in scoped),
                fleet_size=sum(tenant.fleet_size or 0 for tenant in scoped),
                snapshot_ready=sum(1 for tenant in scoped if tenant.snapshot_status in {"ready", "active", "completed", "configured"}),
                snapshot_pending=sum(1 for tenant in scoped if tenant.snapshot_status not in {"ready", "active", "completed", "configured"}),
                llm_models=sorted({tenant.llm_model for tenant in scoped if tenant.llm_model}),
            )
        )
    return snapshots


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


def _shop_snapshot_view(snapshot: ShopProvisioningSnapshot) -> ShopSnapshotRecordView:
    return ShopSnapshotRecordView(
        id=str(snapshot.id),
        snapshot_key=snapshot.snapshot_key,
        snapshot_version=snapshot.snapshot_version,
        status=snapshot.status,
        snapshot_json=snapshot.snapshot_json or {},
        readiness_json=snapshot.readiness_json or {},
        updated_at=snapshot.updated_at,
    )


def _shop_messaging_view(messaging: ShopMessagingConfig) -> ShopMessagingConfigView:
    return ShopMessagingConfigView(
        provider=messaging.provider,
        from_number=messaging.from_number,
        messaging_service_sid=messaging.messaging_service_sid,
        status=messaging.status,
        templates_json=messaging.templates_json or {},
    )


def _shop_workflow_view(workflow: ShopAutomationWorkflow) -> ShopAutomationWorkflowView:
    return ShopAutomationWorkflowView(
        id=str(workflow.id),
        workflow_key=workflow.workflow_key,
        name=workflow.name,
        trigger_event=workflow.trigger_event,
        channel=workflow.channel,
        enabled=workflow.enabled,
        status=workflow.status,
        config_json=workflow.config_json or {},
    )


def _shop_task_view(task: ShopOnboardingTask) -> ShopOnboardingTaskView:
    return ShopOnboardingTaskView(
        id=str(task.id),
        task_key=task.task_key,
        title=task.title,
        category=task.category,
        status=task.status,
        manual_required=task.manual_required,
        instructions=task.instructions,
        metadata_json=task.metadata_json or {},
        completed_at=task.completed_at,
    )


def _shop_snapshot_response(bundle: dict) -> ShopSnapshotProvisionOut:
    return ShopSnapshotProvisionOut(
        tenant=_tenant_view(bundle["tenant"], None, bundle.get("retell_connection")),
        snapshot=_shop_snapshot_view(bundle["snapshot"]),
        messaging=_shop_messaging_view(bundle["messaging"]),
        retell_connection=_retell_connection_view(bundle.get("retell_connection")),
        workflows=[_shop_workflow_view(workflow) for workflow in bundle.get("workflows", [])],
        onboarding_tasks=[_shop_task_view(task) for task in bundle.get("tasks", [])],
        readiness=bundle.get("readiness", {}),
    )


@router.get("/plans", response_model=list[PlanConfigView])
async def list_plans():
    return [PlanConfigView(**plan_payload(config)) for config in get_plan_configs().values()]


@router.post("/tenants", response_model=ProvisionTenantOut, dependencies=[Depends(verify_admin)])
async def provision_tenant(payload: ProvisionTenantIn, db: AsyncSession = Depends(get_db)):
    try:
        provisioned = await service.provision_tenant(db, payload)
        if len(provisioned) == 5:
            tenant, plan, event, ghl_result, warnings = provisioned
            retell_result = None
        else:
            tenant, plan, event, ghl_result, retell_result, warnings = provisioned
        result = await db.execute(select(GHLConnection).where(GHLConnection.tenant_id == tenant.id))
        connection = result.scalar_one_or_none()
        retell_lookup = await db.execute(select(RetellConnection).where(RetellConnection.tenant_id == tenant.id))
        retell_connection = retell_lookup.scalar_one_or_none()
        await db.commit()
        await db.refresh(tenant)
        return ProvisionTenantOut(
            tenant=_tenant_view(tenant, connection, retell_connection),
            plan=PlanConfigView(**plan),
            provisioning_event_id=str(event.id),
            ghl_result=ghl_result,
            retell_result=retell_result,
            warnings=warnings,
        )
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Provisioning failed: {exc}") from exc


@router.post("/admin/shops/snapshot", response_model=ShopSnapshotProvisionOut, dependencies=[Depends(verify_admin)])
async def provision_shop_snapshot(payload: ShopSnapshotProvisionIn, db: AsyncSession = Depends(get_db)):
    try:
        bundle = await shop_snapshot_service.provision_shop_snapshot(db, payload)
        await db.commit()
        return _shop_snapshot_response(bundle)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Shop snapshot provisioning failed: {exc}") from exc


@router.get("/admin/shops/{tenant_id}/snapshot", response_model=ShopSnapshotProvisionOut, dependencies=[Depends(verify_admin)])
async def get_shop_snapshot(tenant_id: str, db: AsyncSession = Depends(get_db)):
    bundle = await shop_snapshot_service.get_shop_snapshot(db, uuid.UUID(tenant_id))
    if not bundle or not bundle.get("snapshot") or not bundle.get("messaging"):
        raise HTTPException(status_code=404, detail="Shop snapshot not found")
    return _shop_snapshot_response(bundle)


@router.post("/admin/shops/{tenant_id}/snapshot/readiness", response_model=dict[str, object], dependencies=[Depends(verify_admin)])
async def refresh_shop_snapshot_readiness(tenant_id: str, db: AsyncSession = Depends(get_db)):
    try:
        readiness = await shop_snapshot_service.refresh_readiness(db, uuid.UUID(tenant_id))
        await db.commit()
        return readiness
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/admin/tenants", response_model=TenantListResponse, dependencies=[Depends(verify_admin)])
async def list_tenants(db: AsyncSession = Depends(get_db)):
    pairs = await service.list_tenants(db)
    tenant_ids = [tenant.id for tenant, _, _ in pairs]
    organization_ids = [tenant.organization_id for tenant, _, _ in pairs]
    latest_activity: dict[uuid.UUID, DispatchEvent | ProvisioningEvent] = {}
    organizations: dict[uuid.UUID, Organization] = {}
    usage_totals: dict[uuid.UUID, dict[str, int]] = {}
    call_counts: dict[uuid.UUID, int] = {}
    vehicle_counts: dict[uuid.UUID, int] = {}
    fleet_profiles: dict[uuid.UUID, FleetProfile] = {}
    shop_snapshots: dict[uuid.UUID, ShopProvisioningSnapshot] = {}
    if tenant_ids:
        provisioning_result = await db.execute(
            select(ProvisioningEvent)
            .where(ProvisioningEvent.tenant_id.in_(tenant_ids))
            .order_by(ProvisioningEvent.created_at.desc())
            .limit(500)
        )
        dispatch_result = await db.execute(
            select(DispatchEvent)
            .where(DispatchEvent.tenant_id.in_(tenant_ids))
            .order_by(DispatchEvent.created_at.desc())
            .limit(500)
        )
        for event in [*provisioning_result.scalars().all(), *dispatch_result.scalars().all()]:
            if event.tenant_id is None:
                continue
            current = latest_activity.get(event.tenant_id)
            if current is None or event.created_at > current.created_at:
                latest_activity[event.tenant_id] = event
        usage_result = await db.execute(
            select(
                PlanUsage.tenant_id,
                func.coalesce(func.sum(PlanUsage.calls_handled), 0),
                func.coalesce(func.sum(PlanUsage.leads_allocated), 0),
            )
            .where(PlanUsage.tenant_id.in_(tenant_ids))
            .group_by(PlanUsage.tenant_id)
        )
        usage_totals = {
            tenant_id: {"calls_handled": int(calls_handled or 0), "leads_allocated": int(leads_allocated or 0)}
            for tenant_id, calls_handled, leads_allocated in usage_result.all()
        }
        call_result = await db.execute(
            select(ShopCall.tenant_id, func.count(ShopCall.id))
            .where(ShopCall.tenant_id.in_(tenant_ids))
            .group_by(ShopCall.tenant_id)
        )
        call_counts = {tenant_id: int(count or 0) for tenant_id, count in call_result.all()}
        snapshot_result = await db.execute(select(ShopProvisioningSnapshot).where(ShopProvisioningSnapshot.tenant_id.in_(tenant_ids)))
        shop_snapshots = {snapshot.tenant_id: snapshot for snapshot in snapshot_result.scalars().all()}
    if organization_ids:
        org_result = await db.execute(select(Organization).where(Organization.id.in_(organization_ids)))
        organizations = {org.id: org for org in org_result.scalars().all()}
        vehicle_result = await db.execute(
            select(Vehicle.organization_id, func.count(Vehicle.id))
            .where(Vehicle.organization_id.in_(organization_ids), Vehicle.is_active == True)  # noqa: E712
            .group_by(Vehicle.organization_id)
        )
        vehicle_counts = {organization_id: int(count or 0) for organization_id, count in vehicle_result.all()}
        fleet_result = await db.execute(select(FleetProfile).where(FleetProfile.organization_id.in_(organization_ids)))
        fleet_profiles = {profile.organization_id: profile for profile in fleet_result.scalars().all()}
    tenant_views: list[TenantView] = []
    for tenant, connection, retell_connection in pairs:
        org = organizations.get(tenant.organization_id)
        vertical_type = org.vertical_type.value if org and hasattr(org.vertical_type, "value") else str(org.vertical_type) if org else "shops"
        usage = usage_totals.get(tenant.id, {})
        vehicle_count = vehicle_counts.get(tenant.organization_id, 0)
        fleet_profile = fleet_profiles.get(tenant.organization_id)
        calls_handled = usage.get("calls_handled", 0) or call_counts.get(tenant.id, 0)
        operations = {
            "vertical_type": vertical_type,
            "calls_handled": calls_handled,
            "leads_allocated": usage.get("leads_allocated", 0),
            "vehicle_count": vehicle_count,
            "fleet_size": fleet_profile.fleet_size if fleet_profile else None,
            "snapshot_status": _snapshot_status(vertical_type, shop_snapshots.get(tenant.id), fleet_profile.fleet_size if fleet_profile else None, vehicle_count),
        }
        tenant_views.append(_tenant_view(tenant, connection, retell_connection, latest_activity.get(tenant.id), operations))
    return TenantListResponse(
        tenants=tenant_views,
        plans=[PlanConfigView(**plan_payload(config)) for config in get_plan_configs().values()],
        snapshots=_snapshot_rollups(tenant_views),
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
    retell_result = await db.execute(select(RetellConnection).where(RetellConnection.tenant_id == tenant.id))
    retell_connection = retell_result.scalar_one_or_none()
    if connection:
        connection.snapshot_id = payload.ghl_snapshot_id or plan_config.snapshot_id
        connection.snapshot_status = "pending"
    await service.record_event(db, event_type="subscription.updated", tenant_id=tenant.id, organization_id=tenant.organization_id, status="plan_updated", payload={"plan_id": tenant.current_plan})
    await db.commit()
    return _tenant_view(tenant, connection, retell_connection)


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


@router.post("/admin/tenants/{tenant_id}/retell/provision", response_model=TenantView, dependencies=[Depends(verify_admin)])
async def provision_tenant_retell(tenant_id: str, payload: TenantRetellProvisionIn, db: AsyncSession = Depends(get_db)):
    tenant = await db.get(Tenant, uuid.UUID(tenant_id))
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    try:
        retell_connection, result = await service.provision_retell_for_tenant(
            db,
            tenant,
            metadata=payload.metadata,
            agent_id=payload.agent_id,
            conversation_flow_id=payload.conversation_flow_id,
            phone_number_id=payload.phone_number_id,
            voice_id=payload.voice_id,
        )
        ghl_result = await db.execute(select(GHLConnection).where(GHLConnection.tenant_id == tenant.id))
        ghl_connection = ghl_result.scalar_one_or_none()
        await db.commit()
        return _tenant_view(tenant, ghl_connection, retell_connection)
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=502, detail=f"Retell provisioning failed: {exc}") from exc


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
        for plan_id in ("starter", "growth", "pro"):
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