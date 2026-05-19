from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.ghl_integration import GHLTenantMapping
from app.models.mechanic_subscription import AIAgent, MechanicAccount, ServiceRequest, ShopCall, ShopCallSummary, ShopProfile
from app.models.organization import Organization, VerticalType
from app.models.tenant_provisioning import GHLConnection, RetellConnection, Tenant
from app.services.ghl_service import GHLService
from app.services.provisioning_service import slugify

logger = get_logger(__name__)


DEFAULT_PIPELINE_STAGES = [
    "New Lead",
    "AI Contacted",
    "Needs Human Follow-Up",
    "Appointment Booked",
    "Roadside Request",
    "Dispatched",
    "Completed",
    "Lost / No Answer",
]

ROADCALL_AI_TAGS = {
    "completed": "ai-call-completed",
    "roadside": "roadside-request",
    "follow_up": "needs-follow-up",
    "booked": "booked",
    "no_answer": "no-answer",
    "urgent": "urgent",
}


class RoadcallOrchestrator:
    def __init__(self) -> None:
        self.ghl = GHLService()

    async def provision_mechanic(self, db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
        business_name = (payload.get("business_name") or payload.get("company_name") or "Mechanic Account").strip()
        email = (payload.get("email") or payload.get("owner_email") or "").strip().lower()
        if not email:
            raise ValueError("email is required")
        slug = slugify(business_name)
        org = (await db.execute(select(Organization).where(Organization.slug == slug))).scalar_one_or_none()
        if org is None:
            org = Organization(
                name=business_name,
                slug=slug,
                vertical_type=VerticalType.shops,
                contact_email=email,
                contact_phone=payload.get("phone"),
                website=payload.get("website"),
                is_active=True,
            )
            db.add(org)
            await db.flush()
        else:
            org.name = business_name
            org.contact_email = email or org.contact_email
            org.contact_phone = payload.get("phone") or org.contact_phone
            org.website = payload.get("website") or org.website
            org.updated_at = datetime.now(timezone.utc)

        tenant = (await db.execute(select(Tenant).where(Tenant.organization_id == org.id))).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(
                organization_id=org.id,
                name=business_name,
                slug=slug,
                contact_email=email,
                contact_phone=payload.get("phone"),
                current_plan=payload.get("plan") or "standard",
                subscription_status=payload.get("subscription_status") or "active",
                onboarding_status="ghl_pending" if not payload.get("ghl_location_id") else "ghl_connected",
                setup_fee_status=payload.get("setup_fee_status") or "paid",
                enabled_features=["ai_phone", "ghl_saas", "roadside_intake"],
                is_active=True,
            )
            db.add(tenant)
            await db.flush()
        else:
            tenant.name = business_name
            tenant.contact_email = email
            tenant.contact_phone = payload.get("phone") or tenant.contact_phone
            tenant.current_plan = payload.get("plan") or tenant.current_plan
            tenant.subscription_status = payload.get("subscription_status") or tenant.subscription_status
            tenant.onboarding_status = "ghl_connected" if payload.get("ghl_location_id") else tenant.onboarding_status
            tenant.is_active = True

        account = (await db.execute(select(MechanicAccount).where(MechanicAccount.tenant_id == tenant.id))).scalar_one_or_none()
        if account is None:
            account = MechanicAccount(
                tenant_id=tenant.id,
                organization_id=org.id,
                owner_name=payload.get("owner_name"),
                email=email,
                phone=payload.get("phone"),
                dashboard_token=secrets.token_urlsafe(32),
                ghl_location_id=payload.get("ghl_location_id"),
                ghl_company_id=payload.get("ghl_company_id"),
                stripe_customer_id=payload.get("stripe_customer_id"),
                stripe_subscription_id=payload.get("stripe_subscription_id"),
                plan=payload.get("plan") or tenant.current_plan,
                status="active",
            )
            db.add(account)
        else:
            account.owner_name = payload.get("owner_name") or account.owner_name
            account.email = email
            account.phone = payload.get("phone") or account.phone
            account.ghl_location_id = payload.get("ghl_location_id") or account.ghl_location_id
            account.ghl_company_id = payload.get("ghl_company_id") or account.ghl_company_id
            account.stripe_customer_id = payload.get("stripe_customer_id") or account.stripe_customer_id
            account.stripe_subscription_id = payload.get("stripe_subscription_id") or account.stripe_subscription_id
            account.plan = payload.get("plan") or account.plan
            account.status = "active"

        profile = (await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant.id))).scalar_one_or_none()
        if profile is None:
            profile = ShopProfile(
                tenant_id=tenant.id,
                organization_id=org.id,
                business_name=business_name,
                phone=payload.get("phone"),
                email=email,
                website=payload.get("website"),
                ghl_calendar_id=payload.get("ghl_calendar_id"),
                ghl_calendar_url=payload.get("ghl_calendar_url"),
                profile_status="incomplete",
            )
            db.add(profile)
        else:
            profile.business_name = business_name
            profile.phone = payload.get("phone") or profile.phone
            profile.email = email or profile.email
            profile.website = payload.get("website") or profile.website
            profile.ghl_calendar_id = payload.get("ghl_calendar_id") or profile.ghl_calendar_id
            profile.ghl_calendar_url = payload.get("ghl_calendar_url") or profile.ghl_calendar_url

        ghl_connection = await self._upsert_ghl_connection(db, tenant, payload)
        if payload.get("ghl_location_id"):
            await self.ghl.upsert_mapping(
                db,
                organization_id=str(org.id),
                location_id=str(payload["ghl_location_id"]),
                agency_id=payload.get("agency_id"),
                ghl_user_id=payload.get("ghl_user_id"),
                subaccount_name=business_name,
                access_token=payload.get("ghl_access_token"),
                refresh_token=payload.get("ghl_refresh_token"),
                token_expires_at=payload.get("ghl_token_expires_at"),
                scopes=payload.get("ghl_scopes") or [],
                token_source="oauth" if payload.get("ghl_refresh_token") else "manual",
                webhook_secret=payload.get("ghl_webhook_secret"),
                pipeline_id=payload.get("ghl_pipeline_id"),
            )
        await db.flush()
        return {
            "mechanic_account_id": str(account.id),
            "tenant_id": str(tenant.id),
            "organization_id": str(org.id),
            "ghl_location_id": ghl_connection.location_id,
            "onboarding_status": tenant.onboarding_status,
            "default_pipeline_stages": DEFAULT_PIPELINE_STAGES,
            "roadcall_dashboard_role": "ai_operations_only",
            "primary_dashboard": "gohighlevel",
        }

    async def _upsert_ghl_connection(self, db: AsyncSession, tenant: Tenant, payload: dict[str, Any]) -> GHLConnection:
        connection = (await db.execute(select(GHLConnection).where(GHLConnection.tenant_id == tenant.id))).scalar_one_or_none()
        if connection is None:
            connection = GHLConnection(tenant_id=tenant.id, organization_id=tenant.organization_id)
            db.add(connection)
        connection.location_id = payload.get("ghl_location_id") or connection.location_id
        connection.agency_id = payload.get("agency_id") or connection.agency_id
        connection.ghl_user_id = payload.get("ghl_user_id") or connection.ghl_user_id
        connection.subaccount_name = payload.get("subaccount_name") or tenant.name
        connection.snapshot_id = payload.get("snapshot_id") or connection.snapshot_id
        connection.snapshot_status = payload.get("snapshot_status") or connection.snapshot_status or "pending"
        connection.connection_status = "connected" if connection.location_id else "pending_location"
        connection.calendar_id = payload.get("ghl_calendar_id") or connection.calendar_id
        connection.calendar_url = payload.get("ghl_calendar_url") or connection.calendar_url
        connection.pipeline_id = payload.get("ghl_pipeline_id") or connection.pipeline_id
        connection.workflow_status = payload.get("workflow_status") or connection.workflow_status or "not_configured"
        connection.website_status = payload.get("website_status") or connection.website_status or "not_configured"
        if payload.get("ghl_access_token"):
            connection.encrypted_access_token = self.ghl.encrypt_secret(payload.get("ghl_access_token"))
        if payload.get("ghl_refresh_token"):
            connection.encrypted_refresh_token = self.ghl.encrypt_secret(payload.get("ghl_refresh_token"))
        connection.token_expires_at = payload.get("ghl_token_expires_at") or connection.token_expires_at
        connection.scopes = payload.get("ghl_scopes") or connection.scopes or []
        connection.metadata_json = {
            **(connection.metadata_json or {}),
            "primary_dashboard": "gohighlevel",
            "roadcall_role": "ai_operations_and_roadside_intelligence",
            "pipeline_stages": DEFAULT_PIPELINE_STAGES,
        }
        return connection

    async def handle_ghl_event(self, db: AsyncSession, payload: dict[str, Any], *, signature_valid: bool = False) -> dict[str, Any]:
        location_id = self._location_id_from_payload(payload)
        mapping = await self.ghl.get_mapping_by_location(db, location_id)
        event_type = self._event_type(payload)
        await self.ghl.record_webhook(db, mapping, event_type, payload, signature_valid, "received")
        tenant = await self._tenant_for_location(db, location_id)
        service_request = None
        should_trigger_ai = event_type in {"new_contact", "form_submission", "missed_call", "opportunity_created"}
        if tenant and should_trigger_ai:
            service_request = await self._upsert_service_request_from_ghl(db, tenant, payload, event_type)
        await db.flush()
        return {
            "ok": True,
            "event_type": event_type,
            "tenant_id": str(tenant.id) if tenant else None,
            "service_request_id": str(service_request.id) if service_request else None,
            "ai_outreach_recommended": bool(service_request and event_type in {"new_contact", "form_submission", "missed_call"}),
        }

    async def handle_retell_event(self, db: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
        event_type = self._event_type(payload)
        call = payload.get("call") if isinstance(payload.get("call"), dict) else payload
        status = str(call.get("call_status") or call.get("status") or event_type).lower()
        if "completed" not in status and event_type not in {"call_analyzed", "call_completed", "call.ended"}:
            return {"ok": True, "ignored": True, "event_type": event_type}

        tenant = await self._tenant_for_retell(db, call)
        if not tenant:
            return {"ok": True, "queued": False, "warning": "No tenant matched Retell call"}
        summary_payload = self._summary_payload(call, payload)
        shop_call = await self._upsert_call_summary(db, tenant, summary_payload)
        service_request = await self._upsert_service_request_from_retell(db, tenant, summary_payload)
        sync_result = await self._sync_retell_outcome_to_ghl(db, tenant, service_request, summary_payload)
        await db.flush()
        return {
            "ok": True,
            "tenant_id": str(tenant.id),
            "call_id": str(shop_call.id),
            "service_request_id": str(service_request.id),
            "ghl_sync": sync_result,
        }

    async def sync_mechanic_ghl(self, db: AsyncSession, mechanic_account_id: uuid.UUID) -> dict[str, Any]:
        account = await db.get(MechanicAccount, mechanic_account_id)
        if not account:
            raise ValueError("Mechanic account not found")
        mapping = await self.ghl.get_mapping_by_org(db, account.organization_id)
        if not mapping:
            return {"ok": True, "status": "not_connected", "contacts": None, "opportunities": None, "appointments": None}
        calendars = await self.ghl.fetch_calendars(db, mapping)
        connection = (await db.execute(select(GHLConnection).where(GHLConnection.organization_id == account.organization_id))).scalar_one_or_none()
        if connection:
            connection.last_synced_at = datetime.now(timezone.utc)
            connection.connection_status = "connected"
        return {"ok": True, "status": "synced", "calendars": calendars}

    async def mechanic_dashboard(self, db: AsyncSession, mechanic_account_id: uuid.UUID) -> dict[str, Any]:
        account = await db.get(MechanicAccount, mechanic_account_id)
        if not account:
            raise ValueError("Mechanic account not found")
        tenant = await db.get(Tenant, account.tenant_id)
        profile = (await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == account.tenant_id))).scalar_one_or_none()
        connection = (await db.execute(select(GHLConnection).where(GHLConnection.tenant_id == account.tenant_id))).scalar_one_or_none()
        agent = (await db.execute(select(AIAgent).where(AIAgent.tenant_id == account.tenant_id))).scalar_one_or_none()
        requests = (await db.execute(
            select(ServiceRequest)
            .where(ServiceRequest.mechanic_account_id == account.id)
            .order_by(ServiceRequest.created_at.desc())
            .limit(25)
        )).scalars().all()
        metrics = await self._dashboard_metrics(db, account.id)
        return {
            "mechanic_account_id": str(account.id),
            "tenant_id": str(account.tenant_id),
            "business_name": tenant.name if tenant else profile.business_name if profile else account.email,
            "primary_dashboard": "gohighlevel",
            "roadcall_dashboard_role": "ai_operations_and_roadside_intelligence",
            "metrics": metrics,
            "recent_service_requests": [self._service_request_view(item) for item in requests],
            "ai_receptionist": {
                "connected_phone_number": profile.phone if profile else account.phone,
                "retell_agent_status": agent.activation_status if agent else "not_configured",
                "retell_agent_id": agent.retell_agent_id if agent else None,
                "enabled": bool(agent and agent.activation_status in {"active", "retell_agent_created", "ghl_managed"}),
            },
            "ghl_status": {
                "sub_account_connected": bool(connection and connection.location_id),
                "location_id": connection.location_id if connection else account.ghl_location_id,
                "website_funnel_status": connection.website_status if connection else "not_configured",
                "calendar_status": "connected" if (connection and connection.calendar_id) or (profile and profile.ghl_calendar_url) else "not_configured",
                "crm_pipeline_status": "connected" if connection and connection.pipeline_id else "not_configured",
                "workflow_status": connection.workflow_status if connection else "not_configured",
                "last_synced_at": connection.last_synced_at.isoformat() if connection and connection.last_synced_at else None,
            },
            "actions": {
                "sync_ghl_data": f"/api/mechanics/{account.id}/sync-ghl",
                "view_ghl_sub_account": None if not connection or not connection.location_id else f"https://app.gohighlevel.com/v2/location/{connection.location_id}/dashboard",
                "configure_ai_agent": "/agents/dashboard?agent=mechanic",
            },
        }

    async def _dashboard_metrics(self, db: AsyncSession, mechanic_account_id: uuid.UUID) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        result = await db.execute(select(ServiceRequest).where(ServiceRequest.mechanic_account_id == mechanic_account_id))
        requests = list(result.scalars().all())
        return {
            "new_leads": sum(1 for item in requests if item.status in {"new", "open"}),
            "ai_calls_completed": sum(1 for item in requests if item.ai_status == "completed"),
            "missed_calls_recovered": sum(1 for item in requests if (item.metadata_json or {}).get("source_event") == "missed_call" and item.ai_status == "completed"),
            "appointments_booked": sum(1 for item in requests if item.status == "booked"),
            "open_roadside_requests": sum(1 for item in requests if item.status not in {"completed", "lost", "cancelled"}),
            "urgent_roadside_requests": sum(1 for item in requests if item.urgency in {"urgent", "high", "emergency"}),
            "estimated_revenue_opportunities": sum(int((item.metadata_json or {}).get("estimated_value_cents") or 0) for item in requests),
        }

    def _service_request_view(self, item: ServiceRequest) -> dict[str, Any]:
        return {
            "id": str(item.id),
            "customer_name": item.caller_name,
            "phone": item.caller_phone,
            "service_type": item.service_type,
            "urgency": item.urgency,
            "ai_status": item.ai_status,
            "ghl_pipeline_stage": item.ghl_pipeline_stage,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
        }

    async def _tenant_for_location(self, db: AsyncSession, location_id: str | None) -> Tenant | None:
        if not location_id:
            return None
        connection = (await db.execute(select(GHLConnection).where(GHLConnection.location_id == location_id))).scalar_one_or_none()
        if connection:
            return await db.get(Tenant, connection.tenant_id)
        account = (await db.execute(select(MechanicAccount).where(MechanicAccount.ghl_location_id == location_id))).scalar_one_or_none()
        return await db.get(Tenant, account.tenant_id) if account else None

    async def _tenant_for_retell(self, db: AsyncSession, call: dict[str, Any]) -> Tenant | None:
        tenant_id = call.get("tenant_id") or (call.get("metadata") or {}).get("tenant_id")
        if tenant_id:
            try:
                return await db.get(Tenant, uuid.UUID(str(tenant_id)))
            except ValueError:
                pass
        agent_id = call.get("agent_id") or call.get("retell_agent_id")
        if agent_id:
            connection = (await db.execute(select(RetellConnection).where(RetellConnection.agent_id == str(agent_id)))).scalar_one_or_none()
            if connection:
                return await db.get(Tenant, connection.tenant_id)
        return None

    async def _upsert_service_request_from_ghl(self, db: AsyncSession, tenant: Tenant, payload: dict[str, Any], event_type: str) -> ServiceRequest:
        account = (await db.execute(select(MechanicAccount).where(MechanicAccount.tenant_id == tenant.id))).scalar_one_or_none()
        contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else payload
        phone = contact.get("phone") or payload.get("phone")
        contact_id = contact.get("id") or payload.get("contactId")
        result = await db.execute(select(ServiceRequest).where(ServiceRequest.tenant_id == tenant.id, ServiceRequest.ghl_contact_id == str(contact_id)) if contact_id else select(ServiceRequest).where(ServiceRequest.tenant_id == tenant.id, ServiceRequest.caller_phone == phone).order_by(ServiceRequest.created_at.desc()))
        service_request = result.scalars().first()
        if service_request is None:
            service_request = ServiceRequest(tenant_id=tenant.id, mechanic_account_id=account.id if account else None)
            db.add(service_request)
        service_request.ghl_contact_id = str(contact_id) if contact_id else service_request.ghl_contact_id
        service_request.ghl_opportunity_id = str(payload.get("opportunityId") or payload.get("opportunity_id") or service_request.ghl_opportunity_id or "") or None
        service_request.caller_name = contact.get("name") or contact.get("firstName") or service_request.caller_name
        service_request.caller_phone = phone or service_request.caller_phone
        service_request.service_type = payload.get("service_type") or payload.get("serviceNeeded") or event_type
        service_request.urgency = payload.get("urgency") or service_request.urgency or "normal"
        service_request.location_text = payload.get("roadside_location") or payload.get("location") or service_request.location_text
        service_request.status = "new"
        service_request.ai_status = "recommended" if event_type in {"new_contact", "form_submission", "missed_call"} else service_request.ai_status
        service_request.ghl_pipeline_stage = payload.get("pipelineStage") or payload.get("stage") or service_request.ghl_pipeline_stage
        service_request.metadata_json = {**(service_request.metadata_json or {}), "source": "ghl", "source_event": event_type, "ghl_payload": payload}
        return service_request

    async def _upsert_service_request_from_retell(self, db: AsyncSession, tenant: Tenant, summary: dict[str, Any]) -> ServiceRequest:
        account = (await db.execute(select(MechanicAccount).where(MechanicAccount.tenant_id == tenant.id))).scalar_one_or_none()
        result = await db.execute(
            select(ServiceRequest)
            .where(ServiceRequest.tenant_id == tenant.id, ServiceRequest.caller_phone == summary.get("caller_phone"))
            .order_by(ServiceRequest.created_at.desc())
            .limit(1)
        )
        service_request = result.scalar_one_or_none()
        if service_request is None:
            service_request = ServiceRequest(tenant_id=tenant.id, mechanic_account_id=account.id if account else None)
            db.add(service_request)
        service_request.caller_name = summary.get("caller_name") or service_request.caller_name
        service_request.caller_phone = summary.get("caller_phone") or service_request.caller_phone
        service_request.vehicle_type = summary.get("vehicle_type") or service_request.vehicle_type
        service_request.service_type = summary.get("service_type") or summary.get("problem_type") or service_request.service_type
        service_request.urgency = summary.get("urgency") or service_request.urgency
        service_request.location_text = summary.get("location_text") or service_request.location_text
        service_request.call_summary = summary.get("summary") or service_request.call_summary
        service_request.transcript_url = summary.get("transcript_url") or service_request.transcript_url
        service_request.ai_status = "completed"
        service_request.status = self._status_from_summary(summary)
        service_request.metadata_json = {**(service_request.metadata_json or {}), "source": "retell", "retell_call_id": summary.get("retell_call_id"), "summary_payload": summary}
        return service_request

    async def _upsert_call_summary(self, db: AsyncSession, tenant: Tenant, payload: dict[str, Any]) -> ShopCall:
        retell_call_id = payload.get("retell_call_id") or uuid.uuid4().hex
        call = (await db.execute(select(ShopCall).where(ShopCall.tenant_id == tenant.id, ShopCall.retell_call_id == retell_call_id))).scalar_one_or_none()
        if call is None:
            call = ShopCall(tenant_id=tenant.id, retell_call_id=retell_call_id)
            db.add(call)
        call.caller_phone = payload.get("caller_phone") or call.caller_phone
        call.call_status = "completed"
        call.lead_status = "qualified" if payload.get("urgency") in {"urgent", "high", "emergency"} else "captured"
        call.duration_seconds = payload.get("duration_seconds") or call.duration_seconds
        call.metadata_json = {**(call.metadata_json or {}), **payload, "source": "retell_webhook"}
        await db.flush()
        summary = (await db.execute(select(ShopCallSummary).where(ShopCallSummary.tenant_id == tenant.id, ShopCallSummary.call_id == call.id))).scalar_one_or_none()
        if summary is None:
            summary = ShopCallSummary(tenant_id=tenant.id, call_id=call.id)
            db.add(summary)
        summary.summary = payload.get("summary")
        summary.problem_type = payload.get("problem_type") or payload.get("service_type")
        summary.vehicle_type = payload.get("vehicle_type")
        summary.urgency = payload.get("urgency")
        return call

    async def _sync_retell_outcome_to_ghl(self, db: AsyncSession, tenant: Tenant, service_request: ServiceRequest, summary: dict[str, Any]) -> dict[str, Any]:
        mapping = await self.ghl.get_mapping_by_org(db, tenant.organization_id)
        if not mapping:
            return {"status": "skipped_no_mapping"}
        tags = [ROADCALL_AI_TAGS["completed"]]
        if service_request.status == "roadside_request":
            tags.append(ROADCALL_AI_TAGS["roadside"])
        if service_request.status == "needs_follow_up":
            tags.append(ROADCALL_AI_TAGS["follow_up"])
        if service_request.status == "booked":
            tags.append(ROADCALL_AI_TAGS["booked"])
        if service_request.urgency in {"urgent", "high", "emergency"}:
            tags.append(ROADCALL_AI_TAGS["urgent"])
        return await self.ghl.sync_ai_call_outcome(
            db,
            mapping,
            {
                "ghl_contact_id": service_request.ghl_contact_id or summary.get("ghl_contact_id"),
                "ghl_opportunity_id": service_request.ghl_opportunity_id or summary.get("ghl_opportunity_id"),
                "summary": summary.get("summary"),
                "tags": tags,
                "status": service_request.status,
                "service_request_id": str(service_request.id),
                "retell_call_id": summary.get("retell_call_id"),
            },
        )

    def _summary_payload(self, call: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
        analysis = call.get("call_analysis") if isinstance(call.get("call_analysis"), dict) else {}
        metadata = call.get("metadata") if isinstance(call.get("metadata"), dict) else {}
        custom = call.get("custom_analysis_data") if isinstance(call.get("custom_analysis_data"), dict) else {}
        return {
            "tenant_id": metadata.get("tenant_id") or call.get("tenant_id"),
            "retell_call_id": call.get("call_id") or call.get("retell_call_id") or envelope.get("call_id"),
            "caller_phone": call.get("from_number") or call.get("caller_phone") or metadata.get("caller_phone"),
            "caller_name": custom.get("caller_name") or metadata.get("caller_name"),
            "summary": analysis.get("call_summary") or call.get("summary") or envelope.get("summary") or "Retell call completed.",
            "problem_type": custom.get("problem_type") or custom.get("service_type") or metadata.get("problem_type"),
            "service_type": custom.get("service_type") or metadata.get("service_type"),
            "vehicle_type": custom.get("vehicle_type") or metadata.get("vehicle_type"),
            "urgency": custom.get("urgency") or metadata.get("urgency") or "normal",
            "location_text": custom.get("location") or custom.get("roadside_location") or metadata.get("location"),
            "duration_seconds": call.get("duration_ms") // 1000 if isinstance(call.get("duration_ms"), int) else call.get("duration_seconds"),
            "transcript_url": call.get("transcript_url"),
            "ghl_contact_id": metadata.get("ghl_contact_id") or custom.get("ghl_contact_id"),
            "ghl_opportunity_id": metadata.get("ghl_opportunity_id") or custom.get("ghl_opportunity_id"),
        }

    def _status_from_summary(self, summary: dict[str, Any]) -> str:
        outcome = str(summary.get("outcome") or summary.get("status") or "").lower()
        if "book" in outcome:
            return "booked"
        if summary.get("urgency") in {"urgent", "high", "emergency"} or summary.get("location_text"):
            return "roadside_request"
        if "no" in outcome and "answer" in outcome:
            return "no_answer"
        return "needs_follow_up" if summary.get("handoff_requested") else "open"

    def _event_type(self, payload: dict[str, Any]) -> str:
        raw = payload.get("type") or payload.get("event") or payload.get("eventType") or payload.get("trigger") or payload.get("name") or "unknown"
        normalized = str(raw).strip().lower().replace(" ", "_").replace(".", "_")
        if "missed" in normalized and "call" in normalized:
            return "missed_call"
        if "form" in normalized:
            return "form_submission"
        if "contact" in normalized and ("create" in normalized or "new" in normalized):
            return "new_contact"
        if "opportunity" in normalized and ("create" in normalized or "new" in normalized):
            return "opportunity_created"
        if "appointment" in normalized:
            return "appointment_booked"
        return normalized

    def _location_id_from_payload(self, payload: dict[str, Any]) -> str | None:
        location = payload.get("location") if isinstance(payload.get("location"), dict) else {}
        return payload.get("locationId") or payload.get("location_id") or location.get("id")
