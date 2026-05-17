from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update

from app.core.logging import get_logger
from app.core.plan_config import PlanFeature, PlanTier, get_plan_config, get_plan_configs, plan_payload
from app.models.ghl_integration import GHLTenantMapping
from app.models.organization import Organization, VerticalType
from app.models.tenant_provisioning import (
    DispatchEvent,
    FeatureFlag,
    GHLConnection,
    ProvisioningEvent,
    RetellConnection,
    RoadsideSession,
    Tenant,
    TenantPlan,
)
from app.schemas.provisioning import ProvisionTenantIn
from app.services.ghl_service import GHLService
from app.services.retell_provisioning_service import RetellProvisioningService

logger = get_logger(__name__)


SUPPORTED_PROVISIONING_EVENTS = {
    "subscription.created",
    "subscription.updated",
    "subscription.cancelled",
    "setup_fee.paid",
    "ghl.location.created",
    "ghl.snapshot.installed",
    "ghl.contact.created",
    "ghl.opportunity.updated",
    "retell.agent.provisioned",
    "retell.agent.provision_failed",
    "roadside.location.received",
    "roadside.mechanic.assigned",
    "roadside.dispatch.completed",
}


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or f"tenant-{uuid.uuid4().hex[:8]}"


class ProvisioningService:
    def __init__(self) -> None:
        self.ghl = GHLService()
        self.retell = RetellProvisioningService()

    def plan_views(self) -> list[dict[str, Any]]:
        return [plan_payload(config) for config in get_plan_configs().values()]

    async def _get_or_create_org(self, db, payload: ProvisionTenantIn) -> Organization:
        if payload.organization_id:
            result = await db.execute(select(Organization).where(Organization.id == uuid.UUID(payload.organization_id)))
            org = result.scalar_one_or_none()
            if org:
                return org

        slug = slugify(payload.organization_slug or payload.organization_name)
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        org = result.scalar_one_or_none()
        if org:
            org.name = payload.organization_name or org.name
            org.contact_email = str(payload.contact_email) if payload.contact_email else org.contact_email
            org.contact_phone = payload.contact_phone or org.contact_phone
            org.website = payload.website or org.website
            org.updated_at = datetime.now(timezone.utc)
            return org

        org = Organization(
            id=uuid.UUID(payload.organization_id) if payload.organization_id else uuid.uuid4(),
            name=payload.organization_name,
            slug=slug,
            vertical_type=VerticalType(payload.vertical_type) if payload.vertical_type in {"shops", "fleet"} else VerticalType.shops,
            contact_email=str(payload.contact_email) if payload.contact_email else None,
            contact_phone=payload.contact_phone,
            website=payload.website,
            is_active=True,
        )
        db.add(org)
        await db.flush()
        return org

    async def _get_or_create_tenant(self, db, org: Organization, payload: ProvisionTenantIn) -> Tenant:
        result = await db.execute(select(Tenant).where(Tenant.organization_id == org.id))
        tenant = result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(
                organization_id=org.id,
                name=org.name,
                slug=org.slug,
                contact_email=org.contact_email,
                contact_phone=org.contact_phone,
            )
            db.add(tenant)
            await db.flush()
        tenant.name = org.name
        tenant.slug = org.slug
        tenant.contact_email = org.contact_email
        tenant.contact_phone = org.contact_phone
        tenant.current_plan = payload.plan_id
        tenant.subscription_status = payload.subscription_status
        tenant.setup_fee_status = payload.setup_fee_status
        tenant.onboarding_status = payload.onboarding_status
        tenant.is_active = payload.subscription_status not in {"cancelled", "churned"}
        tenant.updated_at = datetime.now(timezone.utc)
        return tenant

    async def _activate_plan(self, db, tenant: Tenant, payload: ProvisionTenantIn) -> tuple[TenantPlan, dict[str, Any]]:
        config = get_plan_config(payload.plan_id)
        snapshot_id = payload.ghl_snapshot_id or config.snapshot_id
        await db.execute(
            update(TenantPlan)
            .where(TenantPlan.tenant_id == tenant.id, TenantPlan.is_active == True)  # noqa: E712
            .values(is_active=False, ends_at=datetime.now(timezone.utc))
        )
        tenant.enabled_features = [feature.value for feature in config.features]
        plan = TenantPlan(
            tenant_id=tenant.id,
            plan_id=config.id.value,
            plan_name=config.name,
            price_monthly=config.price_monthly,
            setup_fee=config.setup_fee,
            snapshot_id=snapshot_id,
            enabled_features=[feature.value for feature in config.features],
            allowed_modules=list(config.allowed_modules),
            webhook_permissions=list(config.webhook_permissions),
            dashboard_permissions=list(config.dashboard_permissions),
            dispatch_permissions=list(config.dispatch_permissions),
            ai_feature_permissions=list(config.ai_feature_permissions),
            is_active=True,
        )
        db.add(plan)

        for feature in config.features:
            await self.set_feature_flag(db, tenant.id, feature.value, True, "plan")

        return plan, plan_payload(config)

    async def set_feature_flag(self, db, tenant_id: uuid.UUID, feature: str, enabled: bool, source: str = "admin", reason: str | None = None) -> FeatureFlag:
        result = await db.execute(select(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id, FeatureFlag.feature == feature))
        flag = result.scalar_one_or_none()
        if flag is None:
            flag = FeatureFlag(tenant_id=tenant_id, feature=feature)
            db.add(flag)
        flag.enabled = enabled
        flag.source = source
        flag.reason = reason
        flag.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return flag

    async def _upsert_ghl(self, db, tenant: Tenant, org: Organization, payload: ProvisionTenantIn, snapshot_id: str | None) -> GHLConnection:
        result = await db.execute(select(GHLConnection).where(GHLConnection.tenant_id == tenant.id))
        connection = result.scalar_one_or_none()
        if connection is None:
            connection = GHLConnection(tenant_id=tenant.id, organization_id=org.id)
            db.add(connection)
        connection.location_id = payload.ghl_location_id or connection.location_id
        connection.subaccount_name = payload.ghl_subaccount_name or connection.subaccount_name or org.name
        connection.snapshot_id = snapshot_id or connection.snapshot_id
        connection.snapshot_status = "pending" if connection.snapshot_id else "missing_snapshot_id"
        connection.connection_status = "connected" if connection.location_id else "pending_location"
        connection.metadata_json = {"external_customer_id": payload.external_customer_id, **payload.metadata}
        connection.updated_at = datetime.now(timezone.utc)

        if payload.ghl_location_id:
            await self.ghl.upsert_mapping(
                db,
                organization_id=str(org.id),
                location_id=payload.ghl_location_id,
                subaccount_name=payload.ghl_subaccount_name or org.name,
                access_token=payload.access_token,
                refresh_token=payload.refresh_token,
                webhook_secret=payload.webhook_secret,
            )
        return connection

    async def _get_or_create_retell_connection(self, db, tenant: Tenant, org: Organization, payload: ProvisionTenantIn) -> RetellConnection:
        result = await db.execute(select(RetellConnection).where(RetellConnection.tenant_id == tenant.id))
        connection = result.scalar_one_or_none()
        if connection is None:
            connection = RetellConnection(tenant_id=tenant.id, organization_id=org.id)
            db.add(connection)
        connection.agent_id = payload.retell_agent_id or connection.agent_id
        connection.conversation_flow_id = payload.retell_conversation_flow_id or connection.conversation_flow_id
        connection.phone_number_id = payload.retell_phone_number_id or connection.phone_number_id
        connection.metadata_json = {**(connection.metadata_json or {}), **payload.metadata}
        connection.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return connection

    async def provision_retell_for_tenant(
        self,
        db,
        tenant: Tenant,
        *,
        metadata: dict[str, Any] | None = None,
        agent_id: str | None = None,
        conversation_flow_id: str | None = None,
        phone_number_id: str | None = None,
        voice_id: str = "11labs-Lily",
    ) -> tuple[RetellConnection, dict[str, Any]]:
        org = await db.get(Organization, tenant.organization_id)
        if not org:
            raise ValueError("Tenant organization not found")
        result = await db.execute(select(RetellConnection).where(RetellConnection.tenant_id == tenant.id))
        connection = result.scalar_one_or_none()
        if connection is None:
            connection = RetellConnection(tenant_id=tenant.id, organization_id=tenant.organization_id)
            db.add(connection)
            await db.flush()
        if agent_id:
            connection.agent_id = agent_id
        if conversation_flow_id:
            connection.conversation_flow_id = conversation_flow_id
        if phone_number_id:
            connection.phone_number_id = phone_number_id
        connection.provisioning_status = "provisioning"
        connection.last_error = None
        connection.metadata_json = {**(connection.metadata_json or {}), **(metadata or {})}
        await db.flush()
        try:
            result_payload = await self.retell.provision_agent(
                tenant,
                connection,
                metadata=connection.metadata_json or {},
                conversation_flow_id=conversation_flow_id,
                voice_id=voice_id,
            )
            connection.agent_id = result_payload["agent_id"]
            connection.conversation_flow_id = result_payload["conversation_flow_id"]
            connection.agent_name = result_payload["agent_name"]
            connection.provisioning_status = "active"
            connection.last_synced_at = datetime.now(timezone.utc)
            connection.metadata_json = {
                **(connection.metadata_json or {}),
                "dynamic_variables": result_payload.get("dynamic_variables", {}),
                "service_advisor_prompt": result_payload.get("service_advisor_prompt"),
            }
            await self.record_event(
                db,
                event_type="retell.agent.provisioned",
                source="retell",
                status="completed",
                tenant_id=tenant.id,
                organization_id=tenant.organization_id,
                payload={"agent_id": connection.agent_id, "conversation_flow_id": connection.conversation_flow_id},
            )
            return connection, result_payload
        except Exception as exc:
            connection.provisioning_status = "failed"
            connection.last_error = str(exc)
            await self.record_event(
                db,
                event_type="retell.agent.provision_failed",
                source="retell",
                status="failed",
                tenant_id=tenant.id,
                organization_id=tenant.organization_id,
                payload={"agent_id": connection.agent_id, "conversation_flow_id": connection.conversation_flow_id},
                error=str(exc),
            )
            raise

    async def record_event(
        self,
        db,
        *,
        event_type: str,
        source: str = "roadcall",
        status: str = "received",
        tenant_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> ProvisioningEvent:
        event = ProvisioningEvent(
            tenant_id=tenant_id,
            organization_id=organization_id,
            event_type=event_type,
            source=source,
            status=status,
            payload_json=payload or {},
            error_message=error,
        )
        db.add(event)
        await db.flush()
        return event

    async def provision_tenant(self, db, payload: ProvisionTenantIn) -> tuple[Tenant, dict[str, Any], ProvisioningEvent, dict[str, Any], dict[str, Any] | None, list[str]]:
        warnings: list[str] = []
        org = await self._get_or_create_org(db, payload)
        tenant = await self._get_or_create_tenant(db, org, payload)
        tenant_plan, plan_view = await self._activate_plan(db, tenant, payload)
        retell_connection = await self._get_or_create_retell_connection(db, tenant, org, payload)
        event = await self.record_event(
            db,
            event_type="subscription.created" if payload.subscription_status == "active" else "subscription.updated",
            tenant_id=tenant.id,
            organization_id=org.id,
            status="provisioning_started",
            payload={
                "plan_id": tenant.current_plan,
                "retell_agent_id": retell_connection.agent_id,
                "retell_conversation_flow_id": retell_connection.conversation_flow_id,
                "enabled_features": tenant.enabled_features,
            },
        )
        ghl_result = None
        retell_result: dict[str, Any] | None = None
        if payload.provision_retell:
            try:
                retell_connection, retell_result = await self.provision_retell_for_tenant(
                    db,
                    tenant,
                    metadata=payload.metadata,
                    agent_id=payload.retell_agent_id or retell_connection.agent_id,
                    conversation_flow_id=payload.retell_conversation_flow_id or retell_connection.conversation_flow_id,
                    phone_number_id=payload.retell_phone_number_id or retell_connection.phone_number_id,
                    voice_id=payload.retell_voice_id,
                )
            except Exception as exc:
                warnings.append(f"Retell provisioning did not complete: {exc}")
        await db.flush()
        return tenant, plan_view, event, ghl_result, retell_result, warnings

    async def tenant_has_feature(self, db, tenant_id: uuid.UUID, feature: str) -> tuple[bool, Tenant | None]:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant or not tenant.is_active:
            return False, tenant
        result = await db.execute(select(FeatureFlag).where(FeatureFlag.tenant_id == tenant_id, FeatureFlag.feature == feature))
        flag = result.scalar_one_or_none()
        if flag is not None:
            return flag.enabled, tenant
        return feature in (tenant.enabled_features or []), tenant

    async def list_tenants(self, db) -> list[tuple[Tenant, GHLConnection | None, RetellConnection | None]]:
        result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
        tenants = list(result.scalars().all())
        connections: dict[uuid.UUID, GHLConnection] = {}
        retell_connections: dict[uuid.UUID, RetellConnection] = {}
        if tenants:
            connection_result = await db.execute(select(GHLConnection).where(GHLConnection.tenant_id.in_([t.id for t in tenants])))
            connections = {connection.tenant_id: connection for connection in connection_result.scalars().all()}
            retell_result = await db.execute(select(RetellConnection).where(RetellConnection.tenant_id.in_([t.id for t in tenants])))
            retell_connections = {connection.tenant_id: connection for connection in retell_result.scalars().all()}
        return [(tenant, connections.get(tenant.id), retell_connections.get(tenant.id)) for tenant in tenants]

    async def retry_failed_provisioning(self, db, event_id: uuid.UUID) -> ProvisioningEvent:
        event = await db.get(ProvisioningEvent, event_id)
        if not event:
            raise ValueError("Provisioning event not found")
        event.retry_count += 1
        event.status = "retry_scheduled"
        event.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=min(60, 5 * event.retry_count))
        event.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return event

    async def latest_dispatch_events(self, db, tenant_id: uuid.UUID | None = None, limit: int = 50) -> list[DispatchEvent]:
        statement = select(DispatchEvent).order_by(DispatchEvent.created_at.desc()).limit(limit)
        if tenant_id:
            statement = statement.where(DispatchEvent.tenant_id == tenant_id)
        result = await db.execute(statement)
        return list(result.scalars().all())

    async def record_dispatch_event(
        self,
        db,
        *,
        event_type: str,
        tenant_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        incident_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        status: str = "recorded",
    ) -> DispatchEvent:
        event = DispatchEvent(
            tenant_id=tenant_id,
            organization_id=organization_id,
            incident_id=incident_id,
            job_id=job_id,
            event_type=event_type,
            status=status,
            payload_json=payload or {},
        )
        db.add(event)
        await db.flush()
        return event

    async def create_roadside_session(
        self,
        db,
        *,
        tenant: Tenant,
        session_type: str,
        status: str = "pending",
        incident_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> RoadsideSession:
        session = RoadsideSession(
            tenant_id=tenant.id,
            organization_id=tenant.organization_id,
            incident_id=incident_id,
            session_type=session_type,
            status=status,
            payload_json=payload or {},
        )
        db.add(session)
        await db.flush()
        return session


def all_feature_values() -> list[str]:
    return [feature.value for feature in PlanFeature]


def locked_features_for(plan_id: str, enabled_features: list[str]) -> list[str]:
    enabled = set(enabled_features)
    return [feature for feature in all_feature_values() if feature not in enabled]