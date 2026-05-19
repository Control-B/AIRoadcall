from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.core.plan_config import canonical_plan_id, get_plan_config
from app.models.mechanic_subscription import AIAgent, LeadAllocation, MechanicAccount, RetellNumber, ShopProfile, SipTrunk, StripeSubscription
from app.models.organization import Organization, VerticalType
from app.models.tenant_provisioning import (
    RetellConnection,
    ShopAutomationWorkflow,
    ShopMessagingConfig,
    ShopOnboardingTask,
    ShopProvisioningSnapshot,
    Tenant,
)
from app.schemas.provisioning import ShopSnapshotProvisionIn
from app.services.provisioning_service import ProvisioningService, slugify

DEFAULT_SHOP_SERVICES = [
    "diesel diagnostics",
    "mobile roadside repair",
    "tire repair / replacement",
    "battery / electrical",
    "air leak / brake issue",
    "DPF / derate diagnostics",
    "trailer repair",
    "preventive maintenance",
]

DEFAULT_BUSINESS_HOURS = {
    "monday": {"open": "08:00", "close": "17:00"},
    "tuesday": {"open": "08:00", "close": "17:00"},
    "wednesday": {"open": "08:00", "close": "17:00"},
    "thursday": {"open": "08:00", "close": "17:00"},
    "friday": {"open": "08:00", "close": "17:00"},
    "saturday": {"closed": True},
    "sunday": {"closed": True},
}

DEFAULT_INTAKE_QUALIFICATION = {
    "goal": "AI intake and lead qualification for heavy-duty and roadside service calls.",
    "required_fields": [
        "caller_name",
        "caller_phone",
        "company_name",
        "unit_number",
        "vehicle_year_make_model",
        "engine_make",
        "problem_summary",
        "urgency",
        "service_location",
        "safe_to_drive",
        "loaded_status",
    ],
    "qualification_paths": [
        "roadside_emergency",
        "mobile_repair_candidate",
        "shop_visit",
        "scheduled_service",
        "not_a_fit",
    ],
    "hot_lead_rules": [
        "critical_oos",
        "unsafe_to_drive",
        "roadside_emergency",
        "fleet_account",
        "same_day_service_requested",
    ],
}

DEFAULT_SMS_TEMPLATES = {
    "lead_acknowledgement": "{shop_name}: Thanks for calling. We captured your service request and will follow up shortly. Reply STOP to opt out, HELP for help.",
    "hot_lead_owner_alert": "Roadcall: New qualified service lead for {shop_name}: {caller_name} / {caller_phone}. Issue: {problem_summary}.",
    "booking_link": "{shop_name}: You can pick a service time here: {booking_url}. Reply STOP to opt out, HELP for help.",
    "missed_call_text_back": "{shop_name}: Sorry we missed you. Tell us what you need, or book here: {booking_url}. Reply STOP to opt out, HELP for help.",
    "review_request": "{shop_name}: Thanks for trusting us with your truck. Would you leave a quick review? {review_url}. Reply STOP to opt out, HELP for help.",
}

DEFAULT_WORKFLOWS = [
    {
        "workflow_key": "retell_intake_qualification",
        "name": "Retell intake and lead qualification",
        "trigger_event": "retell.call.completed",
        "channel": "voice",
        "config": {
            "creates_call_record": True,
            "creates_lead_summary": True,
            "qualifies_lead": True,
            "missed_call_recovery": True,
        },
    },
    {
        "workflow_key": "missed_call_recovery",
        "name": "Missed-call text-back recovery",
        "trigger_event": "call.missed",
        "channel": "sms",
        "config": {"provider": "twilio", "template_key": "missed_call_text_back", "creates_recovery_lead": True},
    },
    {
        "workflow_key": "sms_lead_acknowledgement",
        "name": "SMS lead acknowledgement",
        "trigger_event": "lead.qualified",
        "channel": "sms",
        "config": {"provider": "twilio", "template_key": "lead_acknowledgement"},
    },
    {
        "workflow_key": "owner_hot_lead_alert",
        "name": "Owner hot lead alert",
        "trigger_event": "lead.hot",
        "channel": "sms",
        "config": {"provider": "twilio", "template_key": "hot_lead_owner_alert"},
    },
    {
        "workflow_key": "calendar_booking_link",
        "name": "Calendar booking link",
        "trigger_event": "appointment.requested",
        "channel": "sms",
        "config": {"provider": "twilio", "template_key": "booking_link", "requires_calendar": True},
    },
    {
        "workflow_key": "review_request",
        "name": "Review request",
        "trigger_event": "service.completed",
        "channel": "sms",
        "config": {"provider": "twilio", "template_key": "review_request", "delay_hours": 2},
    },
    {
        "workflow_key": "owner_email_summary",
        "name": "Owner email call summary",
        "trigger_event": "retell.call.completed",
        "channel": "email",
        "config": {"provider": "resend", "optional": True},
    },
]


class ShopSnapshotService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.provisioning = ProvisioningService()

    async def provision_shop_snapshot(self, db, payload: ShopSnapshotProvisionIn) -> dict[str, Any]:
        plan_id = canonical_plan_id(payload.plan_id)
        org = await self._upsert_organization(db, payload)
        tenant = await self._upsert_tenant(db, org, payload, plan_id)
        account = await self._upsert_owner_account(db, tenant, org, payload)
        profile = await self._upsert_shop_profile(db, tenant, org, payload)
        subscription = await self._upsert_stripe_subscription(db, tenant, account, payload, plan_id)
        messaging = await self._upsert_twilio_messaging(db, tenant, org, payload)
        retell_connection = await self._upsert_retell_template(db, tenant, org, payload, profile)
        ai_agent = await self._upsert_ai_agent(db, tenant, retell_connection)
        retell_number, sip_trunk = await self._upsert_call_routing(db, tenant, payload, profile, retell_connection)
        workflows = await self._upsert_workflows(db, tenant, org, payload)
        lead_manifest = await self._upsert_lead_manifest(db, tenant, payload, plan_id)
        readiness = self.build_readiness(
            tenant=tenant,
            account=account,
            profile=profile,
            messaging=messaging,
            retell_connection=retell_connection,
            retell_number=retell_number,
            subscription=subscription,
            workflows=workflows,
        )
        tasks = await self._upsert_tasks(db, tenant, org, readiness)
        snapshot = await self._upsert_snapshot(
            db,
            tenant=tenant,
            org=org,
            payload=payload,
            profile=profile,
            messaging=messaging,
            retell_connection=retell_connection,
            retell_number=retell_number,
            sip_trunk=sip_trunk,
            lead_manifest=lead_manifest,
            readiness=readiness,
        )
        await self.provisioning.record_event(
            db,
            event_type="shop.snapshot.provisioned",
            tenant_id=tenant.id,
            organization_id=org.id,
            status=snapshot.status,
            payload={"snapshot_key": snapshot.snapshot_key, "ready": readiness["ready"]},
        )
        return {
            "tenant": tenant,
            "organization": org,
            "account": account,
            "profile": profile,
            "subscription": subscription,
            "messaging": messaging,
            "retell_connection": retell_connection,
            "ai_agent": ai_agent,
            "retell_number": retell_number,
            "sip_trunk": sip_trunk,
            "lead_manifest": lead_manifest,
            "workflows": workflows,
            "tasks": tasks,
            "snapshot": snapshot,
            "readiness": readiness,
        }

    async def get_shop_snapshot(self, db, tenant_id: uuid.UUID) -> dict[str, Any] | None:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            return None
        snapshot = (await db.execute(select(ShopProvisioningSnapshot).where(ShopProvisioningSnapshot.tenant_id == tenant_id))).scalar_one_or_none()
        messaging = (await db.execute(select(ShopMessagingConfig).where(ShopMessagingConfig.tenant_id == tenant_id))).scalar_one_or_none()
        retell_connection = (await db.execute(select(RetellConnection).where(RetellConnection.tenant_id == tenant_id))).scalar_one_or_none()
        profile = (await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant_id))).scalar_one_or_none()
        tasks = (await db.execute(select(ShopOnboardingTask).where(ShopOnboardingTask.tenant_id == tenant_id).order_by(ShopOnboardingTask.created_at))).scalars().all()
        workflows = (await db.execute(select(ShopAutomationWorkflow).where(ShopAutomationWorkflow.tenant_id == tenant_id).order_by(ShopAutomationWorkflow.workflow_key))).scalars().all()
        return {
            "tenant": tenant,
            "snapshot": snapshot,
            "messaging": messaging,
            "retell_connection": retell_connection,
            "profile": profile,
            "tasks": list(tasks),
            "workflows": list(workflows),
            "readiness": snapshot.readiness_json if snapshot else {},
        }

    async def refresh_readiness(self, db, tenant_id: uuid.UUID) -> dict[str, Any]:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        account = (await db.execute(select(MechanicAccount).where(MechanicAccount.tenant_id == tenant_id))).scalar_one_or_none()
        profile = (await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant_id))).scalar_one_or_none()
        messaging = (await db.execute(select(ShopMessagingConfig).where(ShopMessagingConfig.tenant_id == tenant_id))).scalar_one_or_none()
        retell_connection = (await db.execute(select(RetellConnection).where(RetellConnection.tenant_id == tenant_id))).scalar_one_or_none()
        retell_number = (await db.execute(select(RetellNumber).where(RetellNumber.tenant_id == tenant_id))).scalar_one_or_none()
        subscription = (await db.execute(select(StripeSubscription).where(StripeSubscription.tenant_id == tenant_id))).scalar_one_or_none()
        workflows = list((await db.execute(select(ShopAutomationWorkflow).where(ShopAutomationWorkflow.tenant_id == tenant_id))).scalars().all())
        readiness = self.build_readiness(
            tenant=tenant,
            account=account,
            profile=profile,
            messaging=messaging,
            retell_connection=retell_connection,
            retell_number=retell_number,
            subscription=subscription,
            workflows=workflows,
        )
        snapshot = (await db.execute(select(ShopProvisioningSnapshot).where(ShopProvisioningSnapshot.tenant_id == tenant_id))).scalar_one_or_none()
        if snapshot:
            snapshot.readiness_json = readiness
            snapshot.status = "ready" if readiness["ready"] else "needs_setup"
            snapshot.updated_at = datetime.now(timezone.utc)
        await self._upsert_tasks(db, tenant, await db.get(Organization, tenant.organization_id), readiness)
        return readiness

    async def _upsert_organization(self, db, payload: ShopSnapshotProvisionIn) -> Organization:
        slug = slugify(payload.organization_slug or payload.business_name)
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        org = result.scalar_one_or_none()
        if org is None:
            org = Organization(
                name=payload.business_name,
                slug=slug,
                vertical_type=VerticalType.shops,
                contact_email=str(payload.owner_email).lower() if payload.owner_email else None,
                contact_phone=payload.shop_phone,
                website=payload.website,
                is_active=True,
            )
            db.add(org)
            await db.flush()
        else:
            org.name = payload.business_name
            org.vertical_type = VerticalType.shops
            org.contact_email = str(payload.owner_email).lower() if payload.owner_email else org.contact_email
            org.contact_phone = payload.shop_phone or org.contact_phone
            org.website = payload.website or org.website
            org.updated_at = datetime.now(timezone.utc)
        return org

    async def _upsert_tenant(self, db, org: Organization, payload: ShopSnapshotProvisionIn, plan_id: str) -> Tenant:
        result = await db.execute(select(Tenant).where(Tenant.organization_id == org.id))
        tenant = result.scalar_one_or_none()
        config = get_plan_config(plan_id)
        if tenant is None:
            tenant = Tenant(
                organization_id=org.id,
                name=org.name,
                slug=org.slug,
                contact_email=org.contact_email,
                contact_phone=org.contact_phone,
                current_plan=plan_id,
                subscription_status=payload.subscription_status,
                onboarding_status="snapshot_created",
                setup_fee_status=payload.setup_fee_status,
                enabled_features=[feature.value for feature in config.features],
                is_active=payload.subscription_status in {"active", "trialing"},
            )
            db.add(tenant)
            await db.flush()
        else:
            tenant.name = org.name
            tenant.slug = org.slug
            tenant.contact_email = org.contact_email
            tenant.contact_phone = org.contact_phone
            tenant.current_plan = plan_id
            tenant.subscription_status = payload.subscription_status
            tenant.setup_fee_status = payload.setup_fee_status
            tenant.enabled_features = [feature.value for feature in config.features]
            tenant.onboarding_status = "snapshot_created"
            tenant.is_active = payload.subscription_status in {"active", "trialing"}
            tenant.updated_at = datetime.now(timezone.utc)
        return tenant

    async def _upsert_owner_account(self, db, tenant: Tenant, org: Organization, payload: ShopSnapshotProvisionIn) -> MechanicAccount:
        result = await db.execute(select(MechanicAccount).where(MechanicAccount.tenant_id == tenant.id))
        account = result.scalar_one_or_none()
        if account is None:
            account = MechanicAccount(
                tenant_id=tenant.id,
                organization_id=org.id,
                owner_name=payload.owner_name,
                email=str(payload.owner_email).lower(),
                phone=payload.owner_phone or payload.shop_phone,
                dashboard_token=secrets.token_urlsafe(32),
                stripe_customer_id=payload.stripe_customer_id,
                status="active" if tenant.is_active else "pending_checkout",
            )
            db.add(account)
        else:
            account.owner_name = payload.owner_name or account.owner_name
            account.email = str(payload.owner_email).lower()
            account.phone = payload.owner_phone or payload.shop_phone or account.phone
            account.stripe_customer_id = payload.stripe_customer_id or account.stripe_customer_id
            account.status = "active" if tenant.is_active else account.status
            account.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return account

    async def _upsert_shop_profile(self, db, tenant: Tenant, org: Organization, payload: ShopSnapshotProvisionIn) -> ShopProfile:
        result = await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant.id))
        profile = result.scalar_one_or_none()
        disabled_services = {item.strip().lower() for item in payload.disabled_services if item.strip()}
        services = [service for service in (payload.services_offered or DEFAULT_SHOP_SERVICES) if service.strip().lower() not in disabled_services]
        if profile is None:
            profile = ShopProfile(
                tenant_id=tenant.id,
                organization_id=org.id,
                business_name=payload.business_name,
                phone=payload.shop_phone,
                email=str(payload.owner_email).lower(),
                website=payload.website,
            )
            db.add(profile)
        profile.business_name = payload.business_name
        profile.phone = payload.shop_phone or profile.phone
        profile.email = str(payload.owner_email).lower()
        profile.address = payload.address or profile.address
        profile.city = payload.city or profile.city
        profile.state = payload.state or profile.state
        profile.website = payload.website or profile.website
        profile.services_offered = services
        profile.service_area = payload.service_area or profile.service_area
        profile.service_radius_miles = payload.service_radius_miles
        profile.business_hours = payload.business_hours or DEFAULT_BUSINESS_HOURS
        profile.intake_qualification = {**DEFAULT_INTAKE_QUALIFICATION, **payload.intake_qualification}
        profile.offers_mobile_service = payload.offers_mobile_service
        profile.offers_247_service = payload.offers_247_service
        profile.hourly_rate = payload.hourly_rate or profile.hourly_rate
        profile.fallback_phone = payload.fallback_phone or payload.shop_phone or profile.fallback_phone
        profile.calcom_calendar_url = payload.calcom_calendar_url or self._generated_calcom_url(payload, org) or profile.calcom_calendar_url
        profile.calcom_event_type_id = payload.calcom_event_type_id or profile.calcom_event_type_id
        profile.calcom_api_key = payload.calcom_api_key or profile.calcom_api_key
        profile.calcom_base_url = payload.calcom_base_url or profile.calcom_base_url
        profile.calcom_default_timezone = payload.timezone or profile.calcom_default_timezone
        profile.profile_status = "complete" if self._profile_complete(profile) else "incomplete"
        profile.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return profile

    async def _upsert_stripe_subscription(self, db, tenant: Tenant, account: MechanicAccount, payload: ShopSnapshotProvisionIn, plan_id: str) -> StripeSubscription | None:
        if not payload.stripe_subscription_id or not payload.stripe_customer_id:
            return None
        result = await db.execute(select(StripeSubscription).where(StripeSubscription.stripe_subscription_id == payload.stripe_subscription_id))
        subscription = result.scalar_one_or_none()
        if subscription is None:
            subscription = StripeSubscription(
                tenant_id=tenant.id,
                mechanic_account_id=account.id,
                plan_id=plan_id,
                stripe_customer_id=payload.stripe_customer_id,
                stripe_subscription_id=payload.stripe_subscription_id,
                stripe_price_id=payload.stripe_price_id,
                status=payload.subscription_status,
                metadata_json=payload.metadata,
            )
            db.add(subscription)
        else:
            subscription.tenant_id = tenant.id
            subscription.mechanic_account_id = account.id
            subscription.plan_id = plan_id
            subscription.stripe_customer_id = payload.stripe_customer_id
            subscription.stripe_price_id = payload.stripe_price_id or subscription.stripe_price_id
            subscription.status = payload.subscription_status
            subscription.metadata_json = {**(subscription.metadata_json or {}), **payload.metadata}
            subscription.updated_at = datetime.now(timezone.utc)
        account.stripe_customer_id = payload.stripe_customer_id
        await db.flush()
        return subscription

    async def _upsert_twilio_messaging(self, db, tenant: Tenant, org: Organization, payload: ShopSnapshotProvisionIn) -> ShopMessagingConfig:
        result = await db.execute(select(ShopMessagingConfig).where(ShopMessagingConfig.tenant_id == tenant.id))
        messaging = result.scalar_one_or_none()
        if messaging is None:
            messaging = ShopMessagingConfig(tenant_id=tenant.id, organization_id=org.id)
            db.add(messaging)
        from_number = payload.twilio_from_number or self.settings.TWILIO_FROM_NUMBER or None
        service_sid = payload.twilio_messaging_service_sid or self.settings.TWILIO_MESSAGING_SERVICE_SID or None
        messaging.provider = "twilio"
        messaging.from_number = from_number
        messaging.messaging_service_sid = service_sid
        messaging.status = "ready" if from_number or service_sid else "needs_twilio_number"
        messaging.templates_json = {**DEFAULT_SMS_TEMPLATES, **payload.sms_templates}
        messaging.metadata_json = {
            **(messaging.metadata_json or {}),
            "uses_global_twilio_defaults": not bool(payload.twilio_from_number or payload.twilio_messaging_service_sid),
            "owner_alert_phone": payload.owner_phone or payload.shop_phone,
        }
        messaging.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return messaging

    async def _upsert_retell_template(self, db, tenant: Tenant, org: Organization, payload: ShopSnapshotProvisionIn, profile: ShopProfile) -> RetellConnection:
        result = await db.execute(select(RetellConnection).where(RetellConnection.tenant_id == tenant.id))
        connection = result.scalar_one_or_none()
        if connection is None:
            connection = RetellConnection(tenant_id=tenant.id, organization_id=org.id)
            db.add(connection)
        flow_id = payload.retell_conversation_flow_id or self.settings.RETELL_SHOP_CONVERSATION_FLOW_ID or connection.conversation_flow_id
        connection.agent_id = payload.retell_agent_id or connection.agent_id
        connection.conversation_flow_id = flow_id
        connection.phone_number_id = payload.retell_phone_number_id or connection.phone_number_id
        connection.agent_name = connection.agent_name or f"Roadcall - {tenant.name} Shop Intake"
        connection.provisioning_status = "template_assigned" if flow_id or connection.agent_id else "needs_retell_template"
        dynamic_variables = self.provisioning.retell.build_dynamic_variables(
            tenant,
            {
                "shop_address": ", ".join(part for part in (profile.address, profile.city, profile.state) if part),
                "hourly_rate": profile.hourly_rate,
                "mobile_service_available": profile.offers_mobile_service,
                "service_radius_miles": profile.service_radius_miles,
                "dispatch_phone": profile.fallback_phone or profile.phone,
                "supported_services": profile.services_offered,
                "calcom_calendar_url": profile.calcom_calendar_url,
                "disabled_services": payload.disabled_services,
            },
        )
        connection.metadata_json = {
            **(connection.metadata_json or {}),
            "agent_role": "shop_intake_lead_qualification",
            "missed_call_recovery": True,
            "dynamic_variables": dynamic_variables,
            "prompt_template": "SERVICE_ADVISOR_PROMPT_TEMPLATE",
            "call_routing": self._call_routing_payload(payload, profile),
        }
        connection.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return connection

    async def _upsert_ai_agent(self, db, tenant: Tenant, retell_connection: RetellConnection) -> AIAgent:
        result = await db.execute(select(AIAgent).where(AIAgent.tenant_id == tenant.id))
        agent = result.scalar_one_or_none()
        if agent is None:
            agent = AIAgent(tenant_id=tenant.id)
            db.add(agent)
        agent.retell_connection_id = retell_connection.id
        agent.retell_agent_id = retell_connection.agent_id
        agent.retell_conversation_flow_id = retell_connection.conversation_flow_id
        agent.agent_name = retell_connection.agent_name
        agent.activation_status = "template_assigned" if retell_connection.conversation_flow_id or retell_connection.agent_id else "needs_retell_template"
        agent.prompt_snapshot = (retell_connection.metadata_json or {}).get("service_advisor_prompt")
        agent.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return agent

    async def _upsert_call_routing(
        self,
        db,
        tenant: Tenant,
        payload: ShopSnapshotProvisionIn,
        profile: ShopProfile,
        retell_connection: RetellConnection,
    ) -> tuple[RetellNumber, SipTrunk]:
        number_result = await db.execute(select(RetellNumber).where(RetellNumber.tenant_id == tenant.id))
        retell_number = number_result.scalar_one_or_none()
        if retell_number is None:
            retell_number = RetellNumber(tenant_id=tenant.id)
            db.add(retell_number)
        retell_number.retell_phone_number_id = payload.retell_phone_number_id or retell_connection.phone_number_id or retell_number.retell_phone_number_id
        retell_number.phone_number = payload.retell_phone_number or payload.shop_phone or retell_number.phone_number
        retell_number.routing_status = "ready" if retell_number.phone_number or retell_number.retell_phone_number_id else "needs_number"
        retell_number.metadata_json = {**(retell_number.metadata_json or {}), **self._call_routing_payload(payload, profile)}
        retell_number.updated_at = datetime.now(timezone.utc)

        trunk_result = await db.execute(select(SipTrunk).where(SipTrunk.tenant_id == tenant.id, SipTrunk.provider == "retell"))
        sip_trunk = trunk_result.scalar_one_or_none()
        if sip_trunk is None:
            sip_trunk = SipTrunk(tenant_id=tenant.id, provider="retell")
            db.add(sip_trunk)
        sip_trunk.trunk_id = payload.sip_trunk_id or sip_trunk.trunk_id
        sip_trunk.forwarding_number = payload.call_forwarding_phone or payload.fallback_phone or payload.shop_phone or sip_trunk.forwarding_number
        sip_trunk.status = "ready" if sip_trunk.forwarding_number or sip_trunk.trunk_id else "pending"
        sip_trunk.metadata_json = {**(sip_trunk.metadata_json or {}), **self._call_routing_payload(payload, profile)}
        sip_trunk.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return retell_number, sip_trunk

    async def _upsert_lead_manifest(self, db, tenant: Tenant, payload: ShopSnapshotProvisionIn, plan_id: str) -> LeadAllocation | None:
        if not payload.attach_existing_leads and not payload.imported_leads:
            return None
        allocation_month = datetime.now(timezone.utc).strftime("%Y-%m")
        result = await db.execute(
            select(LeadAllocation).where(
                LeadAllocation.tenant_id == tenant.id,
                LeadAllocation.lead_type == "shop_snapshot_import",
                LeadAllocation.status == "snapshot_attached",
            )
        )
        manifest = result.scalar_one_or_none()
        if manifest is None:
            manifest = LeadAllocation(
                tenant_id=tenant.id,
                plan_id=plan_id,
                allocation_month=allocation_month,
                lead_type="shop_snapshot_import",
                status="snapshot_attached",
            )
            db.add(manifest)
        manifest.plan_id = plan_id
        manifest.allocation_month = allocation_month
        manifest.metadata_json = {
            "attach_existing_leads": payload.attach_existing_leads,
            "lead_source_id": payload.lead_source_id,
            "estimated_lead_count": payload.estimated_lead_count or len(payload.imported_leads),
            "imported_leads": payload.imported_leads,
        }
        await db.flush()
        return manifest

    async def _upsert_workflows(self, db, tenant: Tenant, org: Organization, payload: ShopSnapshotProvisionIn) -> list[ShopAutomationWorkflow]:
        workflows: list[ShopAutomationWorkflow] = []
        disabled = set(payload.disabled_workflows)
        for definition in DEFAULT_WORKFLOWS:
            result = await db.execute(
                select(ShopAutomationWorkflow).where(
                    ShopAutomationWorkflow.tenant_id == tenant.id,
                    ShopAutomationWorkflow.workflow_key == definition["workflow_key"],
                )
            )
            workflow = result.scalar_one_or_none()
            if workflow is None:
                workflow = ShopAutomationWorkflow(
                    tenant_id=tenant.id,
                    organization_id=org.id,
                    workflow_key=definition["workflow_key"],
                    name=definition["name"],
                    trigger_event=definition["trigger_event"],
                    channel=definition["channel"],
                )
                db.add(workflow)
            workflow.name = definition["name"]
            workflow.trigger_event = definition["trigger_event"]
            workflow.channel = definition["channel"]
            workflow.enabled = definition["workflow_key"] not in disabled
            workflow.status = "configured" if workflow.enabled else "disabled"
            workflow.config_json = {**definition["config"], **payload.workflow_overrides.get(definition["workflow_key"], {})}
            workflow.updated_at = datetime.now(timezone.utc)
            workflows.append(workflow)
        await db.flush()
        return workflows

    async def _upsert_snapshot(
        self,
        db,
        *,
        tenant: Tenant,
        org: Organization,
        payload: ShopSnapshotProvisionIn,
        profile: ShopProfile,
        messaging: ShopMessagingConfig,
        retell_connection: RetellConnection,
        retell_number: RetellNumber | None,
        sip_trunk: SipTrunk | None,
        lead_manifest: LeadAllocation | None,
        readiness: dict[str, Any],
    ) -> ShopProvisioningSnapshot:
        result = await db.execute(select(ShopProvisioningSnapshot).where(ShopProvisioningSnapshot.tenant_id == tenant.id))
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            snapshot = ShopProvisioningSnapshot(tenant_id=tenant.id, organization_id=org.id)
            db.add(snapshot)
        snapshot.snapshot_key = payload.snapshot_key
        snapshot.snapshot_version = 1
        snapshot.status = "ready" if readiness["ready"] else "needs_setup"
        snapshot.snapshot_json = {
            "business": {
                "name": profile.business_name,
                "phone": profile.phone,
                "email": profile.email,
                "website": profile.website,
                "address": profile.address,
                "city": profile.city,
                "state": profile.state,
                "timezone": profile.calcom_default_timezone,
            },
            "shop_profile": {
                "services_offered": profile.services_offered,
                "service_area": profile.service_area,
                "service_radius_miles": profile.service_radius_miles,
                "business_hours": profile.business_hours,
                "intake_qualification": profile.intake_qualification,
                "offers_mobile_service": profile.offers_mobile_service,
                "offers_247_service": profile.offers_247_service,
            },
            "retell": {
                "agent_id": retell_connection.agent_id,
                "conversation_flow_id": retell_connection.conversation_flow_id,
                "phone_number_id": retell_connection.phone_number_id,
                "phone_number": retell_number.phone_number if retell_number else None,
                "role": "ai_intake_lead_qualification",
            },
            "call_routing": {
                "retell_number_status": retell_number.routing_status if retell_number else "needs_number",
                "sip_trunk_status": sip_trunk.status if sip_trunk else "pending",
                "forwarding_number": sip_trunk.forwarding_number if sip_trunk else None,
                "routing": self._call_routing_payload(payload, profile),
            },
            "twilio": {
                "from_number": messaging.from_number,
                "messaging_service_sid": messaging.messaging_service_sid,
                "templates": messaging.templates_json,
            },
            "calcom": {
                "calendar_url": profile.calcom_calendar_url,
                "event_type_id": profile.calcom_event_type_id,
                "base_url": profile.calcom_base_url,
                "manual_setup_allowed": True,
            },
            "lead_source": {
                "attach_existing_leads": payload.attach_existing_leads,
                "lead_source_id": payload.lead_source_id,
                "estimated_lead_count": payload.estimated_lead_count,
                "manifest_id": str(lead_manifest.id) if lead_manifest else None,
                "imported_count": len(payload.imported_leads),
            },
            "metadata": payload.metadata,
        }
        snapshot.readiness_json = readiness
        snapshot.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return snapshot

    async def _upsert_tasks(self, db, tenant: Tenant, org: Organization | None, readiness: dict[str, Any]) -> list[ShopOnboardingTask]:
        if org is None:
            raise ValueError("Tenant organization not found")
        definitions = self._task_definitions(readiness)
        tasks: list[ShopOnboardingTask] = []
        now = datetime.now(timezone.utc)
        for definition in definitions:
            result = await db.execute(
                select(ShopOnboardingTask).where(
                    ShopOnboardingTask.tenant_id == tenant.id,
                    ShopOnboardingTask.task_key == definition["task_key"],
                )
            )
            task = result.scalar_one_or_none()
            if task is None:
                task = ShopOnboardingTask(
                    tenant_id=tenant.id,
                    organization_id=org.id,
                    task_key=definition["task_key"],
                    title=definition["title"],
                )
                db.add(task)
            task.title = definition["title"]
            task.category = definition["category"]
            task.status = definition["status"]
            task.manual_required = definition["manual_required"]
            task.instructions = definition["instructions"]
            task.metadata_json = definition.get("metadata", {})
            task.completed_at = task.completed_at or (now if task.status == "complete" else None)
            if task.status != "complete":
                task.completed_at = None
            task.updated_at = now
            tasks.append(task)
        await db.flush()
        return tasks

    def build_readiness(
        self,
        *,
        tenant: Tenant,
        account: MechanicAccount | None,
        profile: ShopProfile | None,
        messaging: ShopMessagingConfig | None,
        retell_connection: RetellConnection | None,
        subscription: StripeSubscription | None,
        workflows: list[ShopAutomationWorkflow],
        retell_number: RetellNumber | None = None,
    ) -> dict[str, Any]:
        checks = {
            "owner_account": bool(account and account.email),
            "stripe_subscription": tenant.subscription_status in {"active", "trialing"} or bool(subscription),
            "shop_profile": self._profile_complete(profile),
            "business_hours": bool(profile and profile.business_hours),
            "twilio_sms": bool(messaging and messaging.status == "ready"),
            "retell_template": bool(retell_connection and (retell_connection.conversation_flow_id or retell_connection.agent_id)),
            "phone_routing": bool(profile and profile.phone and (retell_number is None or retell_number.routing_status in {"ready", "needs_number"})),
            "calendar": bool(profile and (getattr(profile, "calcom_event_type_id", None) or getattr(profile, "calcom_calendar_url", None))),
            "workflows": len([item for item in workflows if item.enabled]) >= 5,
        }
        blockers = [key for key in ("owner_account", "shop_profile", "twilio_sms", "retell_template", "phone_routing", "workflows") if not checks[key]]
        manual = [key for key in ("calendar", "stripe_subscription") if not checks[key]]
        return {
            "ready": not blockers,
            "blockers": blockers,
            "manual_setup": manual,
            "checks": checks,
            "summary": "ready_for_test_calls" if not blockers else "needs_setup",
        }

    def _profile_complete(self, profile: ShopProfile | None) -> bool:
        if not profile:
            return False
        return bool(
            profile.business_name
            and profile.phone
            and profile.email
            and profile.address
            and profile.city
            and profile.state
            and profile.services_offered
            and profile.business_hours
        )

    def _task_definitions(self, readiness: dict[str, Any]) -> list[dict[str, Any]]:
        checks = readiness["checks"]
        return [
            {
                "task_key": "owner_account",
                "title": "Create owner/admin dashboard account",
                "category": "account",
                "status": "complete" if checks["owner_account"] else "pending",
                "manual_required": False,
                "instructions": "Owner account is generated with a dashboard token.",
            },
            {
                "task_key": "shop_profile",
                "title": "Complete shop profile, services, radius, and business hours",
                "category": "profile",
                "status": "complete" if checks["shop_profile"] else "pending",
                "manual_required": not checks["shop_profile"],
                "instructions": "Fill address, city/state, service list, service radius, and weekly hours.",
            },
            {
                "task_key": "twilio_sms",
                "title": "Configure Twilio SMS sender",
                "category": "messaging",
                "status": "complete" if checks["twilio_sms"] else "pending",
                "manual_required": not checks["twilio_sms"],
                "instructions": "Set a Twilio Messaging Service SID or from-number for this shop or globally.",
            },
            {
                "task_key": "retell_template",
                "title": "Assign Retell intake and qualification agent template",
                "category": "voice",
                "status": "complete" if checks["retell_template"] else "pending",
                "manual_required": not checks["retell_template"],
                "instructions": "Configure RETELL_SHOP_CONVERSATION_FLOW_ID or pass a shop-specific Retell flow/agent ID.",
            },
            {
                "task_key": "phone_routing",
                "title": "Store shop phone number and call routing",
                "category": "voice",
                "status": "complete" if checks["phone_routing"] else "pending",
                "manual_required": not checks["phone_routing"],
                "instructions": "Confirm the Retell number, SIP trunk, forwarding phone, and after-hours route before launch.",
            },
            {
                "task_key": "calendar",
                "title": "Connect Cal.com booking event",
                "category": "calendar",
                "status": "complete" if checks["calendar"] else "pending",
                "manual_required": not checks["calendar"],
                "instructions": "Calendar can stay manual: create or verify the Cal.com event, then paste the event type ID or booking URL.",
            },
            {
                "task_key": "workflows",
                "title": "Seed intake, SMS, booking, and review workflows",
                "category": "automation",
                "status": "complete" if checks["workflows"] else "pending",
                "manual_required": False,
                "instructions": "Default workflows are seeded from the Roadcall shop snapshot.",
            },
            {
                "task_key": "test_sms_and_call",
                "title": "Run SMS and Retell test call",
                "category": "qa",
                "status": "pending",
                "manual_required": True,
                "instructions": "Send a test SMS and place a Retell test call before go-live.",
                "metadata": {"requires": ["twilio_sms", "retell_template"]},
            },
            {
                "task_key": "go_live",
                "title": "Mark shop ready for go-live",
                "category": "launch",
                "status": "pending" if readiness["manual_setup"] else "ready",
                "manual_required": True,
                "instructions": "Confirm phone routing, calendar behavior, and owner notification preferences.",
            },
        ]

    def _generated_calcom_url(self, payload: ShopSnapshotProvisionIn, org: Organization) -> str | None:
        if not payload.calcom_username:
            return None
        base_url = (payload.calcom_base_url or "https://cal.com").rstrip("/")
        if base_url.endswith("/api"):
            base_url = base_url[:-4]
        username = payload.calcom_username.strip("/")
        event_slug = (payload.calcom_event_slug or slugify(org.name)).strip("/")
        return f"{base_url}/{username}/{event_slug}"

    def _call_routing_payload(self, payload: ShopSnapshotProvisionIn, profile: ShopProfile) -> dict[str, Any]:
        return {
            "business_phone": payload.shop_phone or profile.phone,
            "retell_phone_number": payload.retell_phone_number,
            "retell_phone_number_id": payload.retell_phone_number_id,
            "fallback_phone": payload.fallback_phone or profile.fallback_phone,
            "forwarding_phone": payload.call_forwarding_phone or payload.fallback_phone or profile.fallback_phone,
            "sip_trunk_id": payload.sip_trunk_id,
            "after_hours_mode": "answer_24_7" if payload.offers_247_service else "capture_and_escalate",
            **payload.call_routing,
        }
