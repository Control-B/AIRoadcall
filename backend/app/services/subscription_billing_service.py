from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

import stripe
from sqlalchemy import select

from app.core.config import get_settings
from app.core.plan_config import canonical_plan_id, get_plan_config, included_leads_for, plan_payload
from app.models.mechanic_subscription import AIAgent, MechanicAccount, PlanUsage, ShopProfile, StripeSubscription
from app.models.organization import Organization, VerticalType
from app.models.tenant_provisioning import GHLConnection, Tenant
from app.schemas.billing import CheckoutSessionCreateIn, ShopProfileUpdateIn
from app.services.provisioning_service import ProvisioningService, slugify

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY

ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing"}


def _from_timestamp(value: int | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(value, timezone.utc)


class SubscriptionBillingService:
    def __init__(self) -> None:
        self.provisioning = ProvisioningService()

    def public_dashboard_url(self, tenant_id: uuid.UUID, dashboard_token: str) -> str:
        return f"{settings.public_app_base_url}/mechanic/dashboard?tenant={tenant_id}&token={dashboard_token}"

    def _success_url(self, tenant_id: uuid.UUID, dashboard_token: str) -> str:
        return f"{self.public_dashboard_url(tenant_id, dashboard_token)}&checkout=success&session_id={{CHECKOUT_SESSION_ID}}"

    def _cancel_url(self) -> str:
        return f"{settings.public_app_base_url}/pricing?checkout=cancelled"

    async def _get_or_create_tenant(self, db, payload: CheckoutSessionCreateIn, plan_id: str) -> tuple[Organization, Tenant]:
        slug = slugify(payload.business_name)
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        org = result.scalar_one_or_none()
        if org is None:
            org = Organization(
                name=payload.business_name,
                slug=slug,
                vertical_type=VerticalType.shops,
                contact_email=str(payload.email).lower(),
                contact_phone=payload.phone,
                website=payload.website,
                is_active=True,
            )
            db.add(org)
            await db.flush()
        else:
            org.name = payload.business_name
            org.contact_email = str(payload.email).lower()
            org.contact_phone = payload.phone or org.contact_phone
            org.website = payload.website or org.website
            org.updated_at = datetime.now(timezone.utc)

        tenant_result = await db.execute(select(Tenant).where(Tenant.organization_id == org.id))
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(
                organization_id=org.id,
                name=org.name,
                slug=org.slug,
                contact_email=org.contact_email,
                contact_phone=org.contact_phone,
                current_plan=plan_id,
                subscription_status="pending_checkout",
                onboarding_status="not_started",
                setup_fee_status="unpaid",
                enabled_features=[],
                is_active=False,
            )
            db.add(tenant)
            await db.flush()
        else:
            tenant.name = org.name
            tenant.slug = org.slug
            tenant.contact_email = org.contact_email
            tenant.contact_phone = org.contact_phone
            tenant.current_plan = plan_id
            if tenant.subscription_status not in ACTIVE_SUBSCRIPTION_STATUSES:
                tenant.subscription_status = "pending_checkout"
                tenant.is_active = False
            tenant.updated_at = datetime.now(timezone.utc)
        return org, tenant

    async def _get_or_create_account(self, db, tenant: Tenant, org: Organization, payload: CheckoutSessionCreateIn) -> MechanicAccount:
        result = await db.execute(select(MechanicAccount).where(MechanicAccount.tenant_id == tenant.id))
        account = result.scalar_one_or_none()
        if account is None:
            account = MechanicAccount(
                tenant_id=tenant.id,
                organization_id=org.id,
                owner_name=payload.owner_name,
                email=str(payload.email).lower(),
                phone=payload.phone,
                dashboard_token=secrets.token_urlsafe(32),
                status="pending_checkout",
            )
            db.add(account)
        else:
            account.owner_name = payload.owner_name or account.owner_name
            account.email = str(payload.email).lower()
            account.phone = payload.phone or account.phone
            account.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return account

    async def _get_or_create_profile(self, db, tenant: Tenant, org: Organization, payload: CheckoutSessionCreateIn) -> ShopProfile:
        result = await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant.id))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = ShopProfile(
                tenant_id=tenant.id,
                organization_id=org.id,
                business_name=payload.business_name,
                phone=payload.phone,
                email=str(payload.email).lower(),
                website=payload.website,
                profile_status="incomplete",
            )
            db.add(profile)
        else:
            profile.business_name = payload.business_name
            profile.phone = payload.phone or profile.phone
            profile.email = str(payload.email).lower()
            profile.website = payload.website or profile.website
            profile.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return profile

    async def create_checkout_session(self, db, payload: CheckoutSessionCreateIn) -> dict[str, str]:
        plan_id = canonical_plan_id(payload.plan_id)
        price_id = settings.stripe_price_id_for_plan(plan_id)
        if not price_id:
            raise ValueError(f"Stripe price ID is not configured for {plan_id}")

        org, tenant = await self._get_or_create_tenant(db, payload, plan_id)
        account = await self._get_or_create_account(db, tenant, org, payload)
        await self._get_or_create_profile(db, tenant, org, payload)
        await db.flush()

        checkout_payload = {
            "mode": "subscription",
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": self._success_url(tenant.id, account.dashboard_token),
            "cancel_url": self._cancel_url(),
            "allow_promotion_codes": True,
            "metadata": {
                "tenant_id": str(tenant.id),
                "organization_id": str(org.id),
                "mechanic_account_id": str(account.id),
                "plan_id": plan_id,
            },
            "subscription_data": {
                "metadata": {
                    "tenant_id": str(tenant.id),
                    "organization_id": str(org.id),
                    "mechanic_account_id": str(account.id),
                    "plan_id": plan_id,
                }
            },
        }
        if account.stripe_customer_id:
            checkout_payload["customer"] = account.stripe_customer_id
        else:
            checkout_payload["customer_email"] = account.email
        session = stripe.checkout.Session.create(**checkout_payload)
        return {
            "checkout_url": session.url,
            "checkout_session_id": session.id,
            "tenant_id": str(tenant.id),
            "dashboard_url": self.public_dashboard_url(tenant.id, account.dashboard_token),
        }

    async def create_customer_portal(self, db, tenant_id: uuid.UUID, dashboard_token: str) -> str:
        account = await self.require_account(db, tenant_id, dashboard_token)
        if not account.stripe_customer_id:
            raise ValueError("Stripe customer is not available yet")
        session = stripe.billing_portal.Session.create(
            customer=account.stripe_customer_id,
            return_url=self.public_dashboard_url(tenant_id, dashboard_token),
        )
        return session.url

    async def require_account(self, db, tenant_id: uuid.UUID, dashboard_token: str) -> MechanicAccount:
        result = await db.execute(
            select(MechanicAccount).where(
                MechanicAccount.tenant_id == tenant_id,
                MechanicAccount.dashboard_token == dashboard_token,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise PermissionError("Invalid mechanic dashboard token")
        return account

    async def _latest_subscription(self, db, tenant_id: uuid.UUID) -> StripeSubscription | None:
        result = await db.execute(
            select(StripeSubscription)
            .where(StripeSubscription.tenant_id == tenant_id)
            .order_by(StripeSubscription.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _profile_complete(self, profile: ShopProfile | None) -> bool:
        if not profile:
            return False
        required = [profile.business_name, profile.phone, profile.email, profile.city, profile.state]
        return all(bool(value) for value in required) and bool(profile.services_offered)

    async def dashboard(self, db, tenant_id: uuid.UUID, dashboard_token: str) -> dict[str, Any]:
        account = await self.require_account(db, tenant_id, dashboard_token)
        tenant = await db.get(Tenant, tenant_id)
        profile = (await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant_id))).scalar_one_or_none()
        subscription = await self._latest_subscription(db, tenant_id)
        agent = (await db.execute(select(AIAgent).where(AIAgent.tenant_id == tenant_id))).scalar_one_or_none()
        usage_month = datetime.now(timezone.utc).strftime("%Y-%m")
        usage = (await db.execute(select(PlanUsage).where(PlanUsage.tenant_id == tenant_id, PlanUsage.usage_month == usage_month))).scalar_one_or_none()
        profile_complete = self._profile_complete(profile)
        active_subscription = bool(subscription and subscription.status in ACTIVE_SUBSCRIPTION_STATUSES)
        steps = [
            {"id": "subscribe", "label": "Subscribe", "complete": active_subscription},
            {"id": "profile", "label": "Complete Shop Profile", "complete": profile_complete},
            {"id": "ai", "label": "Create AI Advisor", "complete": bool(agent and agent.activation_status in {"ghl_managed", "retell_agent_created", "sip_pending", "active"})},
            {"id": "number", "label": "Connect Number", "complete": bool(agent and agent.activation_status in {"ghl_managed", "active"})},
            {"id": "live", "label": "Go Live", "complete": bool(agent and agent.activation_status in {"ghl_managed", "active"})},
        ]
        return {
            "tenant_id": str(tenant_id),
            "business_name": tenant.name if tenant else account.email,
            "account_status": account.status,
            "subscription": None if not subscription else {
                "plan_id": subscription.plan_id,
                "status": subscription.status,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
            },
            "profile": None if not profile else {
                "business_name": profile.business_name,
                "phone": profile.phone,
                "email": profile.email,
                "address": profile.address,
                "city": profile.city,
                "state": profile.state,
                "website": profile.website,
                "services_offered": profile.services_offered,
                "service_area": profile.service_area,
                "service_radius_miles": profile.service_radius_miles,
                "offers_mobile_service": profile.offers_mobile_service,
                "offers_247_service": profile.offers_247_service,
                "hourly_rate": profile.hourly_rate,
                "fallback_phone": profile.fallback_phone,
                "calcom_calendar_url": profile.calcom_calendar_url,
                "profile_status": profile.profile_status,
            },
            "profile_complete": profile_complete,
            "ai_agent": None if not agent else {
                "activation_status": agent.activation_status,
                "retell_agent_id": agent.retell_agent_id,
                "retell_conversation_flow_id": agent.retell_conversation_flow_id,
                "agent_name": agent.agent_name,
                "last_error": agent.last_error,
            },
            "usage": None if not usage else {
                "usage_month": usage.usage_month,
                "calls_handled": usage.calls_handled,
                "leads_allocated": usage.leads_allocated,
                "included_leads": usage.included_leads,
                "overage_leads": usage.overage_leads,
            },
            "activation_steps": steps,
        }

    async def update_profile(self, db, tenant_id: uuid.UUID, dashboard_token: str, payload: ShopProfileUpdateIn) -> ShopProfile:
        account = await self.require_account(db, tenant_id, dashboard_token)
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        result = await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant_id))
        profile = result.scalar_one_or_none()
        if profile is None:
            profile = ShopProfile(
                tenant_id=tenant_id,
                organization_id=tenant.organization_id,
                business_name=payload.business_name or tenant.name,
                email=str(payload.email or account.email),
            )
            db.add(profile)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(profile, key, value)
        profile.profile_status = "complete" if self._profile_complete(profile) else "incomplete"
        tenant.onboarding_status = "profile_complete" if profile.profile_status == "complete" else "profile_incomplete"
        tenant.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return profile

    async def activate_ai(self, db, tenant_id: uuid.UUID, dashboard_token: str) -> dict[str, str | None]:
        await self.require_account(db, tenant_id, dashboard_token)
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        subscription = await self._latest_subscription(db, tenant_id)
        if not subscription or subscription.status not in ACTIVE_SUBSCRIPTION_STATUSES:
            agent = await self._upsert_agent_status(db, tenant_id, "not_subscribed", "Active Stripe subscription required")
            return {"activation_status": agent.activation_status, "detail": "Active Stripe subscription required", "retell_agent_id": None, "retell_conversation_flow_id": None}
        profile = (await db.execute(select(ShopProfile).where(ShopProfile.tenant_id == tenant_id))).scalar_one_or_none()
        if not self._profile_complete(profile):
            agent = await self._upsert_agent_status(db, tenant_id, "profile_incomplete", "Complete shop profile first")
            return {"activation_status": agent.activation_status, "detail": "Complete shop profile first", "retell_agent_id": None, "retell_conversation_flow_id": None}
        if tenant.current_plan in {"starter", "growth", "pro"} and settings.GHL_API_KEY:
            config = get_plan_config(tenant.current_plan)
            connection = (await db.execute(select(GHLConnection).where(GHLConnection.tenant_id == tenant_id))).scalar_one_or_none()
            if connection is None:
                connection = GHLConnection(
                    tenant_id=tenant_id,
                    organization_id=tenant.organization_id,
                    subaccount_name=tenant.name,
                    snapshot_id=config.snapshot_id,
                    snapshot_status="pending" if config.snapshot_id else "missing_snapshot_id",
                    connection_status="pending_location",
                    metadata_json={"managed_by": "roadcall_retell", "role": "crm_mirror", "plan_id": config.id.value},
                )
                db.add(connection)
            else:
                connection.subaccount_name = connection.subaccount_name or tenant.name
                connection.snapshot_id = connection.snapshot_id or config.snapshot_id
                connection.metadata_json = {**(connection.metadata_json or {}), "managed_by": "roadcall_retell", "role": "crm_mirror", "plan_id": config.id.value}
            await db.flush()

        metadata = {
            "shop_address": ", ".join(item for item in [profile.address, profile.city, profile.state] if item),
            "hourly_rate": profile.hourly_rate,
            "mobile_service_available": profile.offers_mobile_service,
            "service_radius_miles": profile.service_radius_miles,
            "dispatch_phone": profile.fallback_phone or profile.phone,
            "supported_services": profile.services_offered,
            "calcom_calendar_url": profile.calcom_calendar_url,
        }
        retell_connection, retell_result = await self.provisioning.provision_retell_for_tenant(
            db,
            tenant,
            metadata=metadata,
            vertical="shops",
        )
        agent = await self._upsert_agent_status(db, tenant_id, "retell_agent_created", None)
        agent.retell_connection_id = retell_connection.id
        agent.retell_agent_id = retell_connection.agent_id
        agent.retell_conversation_flow_id = retell_connection.conversation_flow_id
        agent.agent_name = retell_connection.agent_name
        agent.prompt_snapshot = retell_result.get("service_advisor_prompt")
        tenant.onboarding_status = "retell_agent_created"
        await db.flush()
        return {
            "activation_status": agent.activation_status,
            "detail": "Retell AI advisor created. Connect or forward a phone number to go live.",
            "retell_agent_id": agent.retell_agent_id,
            "retell_conversation_flow_id": agent.retell_conversation_flow_id,
        }

    async def _upsert_agent_status(self, db, tenant_id: uuid.UUID, status: str, error: str | None) -> AIAgent:
        result = await db.execute(select(AIAgent).where(AIAgent.tenant_id == tenant_id))
        agent = result.scalar_one_or_none()
        if agent is None:
            agent = AIAgent(tenant_id=tenant_id, activation_status=status)
            db.add(agent)
        agent.activation_status = status
        agent.last_error = error
        agent.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return agent

    async def sync_checkout_completed(self, db, session: dict[str, Any]) -> None:
        metadata = session.get("metadata") or {}
        tenant_id = uuid.UUID(metadata["tenant_id"])
        account = await db.get(MechanicAccount, uuid.UUID(metadata["mechanic_account_id"]))
        if account:
            account.stripe_customer_id = str(session.get("customer") or account.stripe_customer_id or "") or None
            account.status = "payment_active"
            account.updated_at = datetime.now(timezone.utc)
        tenant = await db.get(Tenant, tenant_id)
        if tenant:
            tenant.subscription_status = "active"
            tenant.setup_fee_status = "paid"
            tenant.is_active = True
            tenant.current_plan = canonical_plan_id(metadata.get("plan_id") or tenant.current_plan)
            await self._apply_plan_to_tenant(db, tenant)

    async def sync_subscription(self, db, subscription: dict[str, Any]) -> None:
        metadata = subscription.get("metadata") or {}
        tenant_id_value = metadata.get("tenant_id")
        if not tenant_id_value:
            return
        tenant_id = uuid.UUID(str(tenant_id_value))
        plan_id = canonical_plan_id(metadata.get("plan_id") or "starter")
        customer_id = str(subscription.get("customer") or "")
        stripe_subscription_id = str(subscription.get("id") or "")
        items = subscription.get("items", {}).get("data", []) if isinstance(subscription.get("items"), dict) else []
        stripe_price_id = None
        if items:
            stripe_price_id = ((items[0].get("price") or {}).get("id"))
        account = None
        account_id = metadata.get("mechanic_account_id")
        if account_id:
            account = await db.get(MechanicAccount, uuid.UUID(str(account_id)))
        if account is None and customer_id:
            account = (await db.execute(select(MechanicAccount).where(MechanicAccount.stripe_customer_id == customer_id))).scalar_one_or_none()

        result = await db.execute(select(StripeSubscription).where(StripeSubscription.stripe_subscription_id == stripe_subscription_id))
        record = result.scalar_one_or_none()
        if record is None:
            record = StripeSubscription(
                tenant_id=tenant_id,
                mechanic_account_id=account.id if account else None,
                plan_id=plan_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=stripe_subscription_id,
                status=str(subscription.get("status") or "incomplete"),
            )
            db.add(record)
        record.plan_id = plan_id
        record.stripe_customer_id = customer_id
        record.stripe_price_id = stripe_price_id
        record.status = str(subscription.get("status") or "incomplete")
        record.current_period_start = _from_timestamp(subscription.get("current_period_start"))
        record.current_period_end = _from_timestamp(subscription.get("current_period_end"))
        record.cancel_at_period_end = bool(subscription.get("cancel_at_period_end"))
        record.trial_end = _from_timestamp(subscription.get("trial_end"))
        record.metadata_json = metadata
        record.updated_at = datetime.now(timezone.utc)

        tenant = await db.get(Tenant, tenant_id)
        if tenant:
            tenant.current_plan = plan_id
            tenant.subscription_status = record.status
            tenant.is_active = record.status in ACTIVE_SUBSCRIPTION_STATUSES
            tenant.updated_at = datetime.now(timezone.utc)
            if tenant.is_active:
                await self._apply_plan_to_tenant(db, tenant)
        if account:
            account.stripe_customer_id = customer_id or account.stripe_customer_id
            account.status = "payment_active" if record.status in ACTIVE_SUBSCRIPTION_STATUSES else record.status
            account.updated_at = datetime.now(timezone.utc)
        await self._ensure_usage_row(db, tenant_id, plan_id)
        await db.flush()

    async def _apply_plan_to_tenant(self, db, tenant: Tenant) -> None:
        config = get_plan_config(tenant.current_plan)
        tenant.current_plan = config.id.value
        tenant.enabled_features = [feature.value for feature in config.features]
        for feature in config.features:
            await self.provisioning.set_feature_flag(db, tenant.id, feature.value, True, "stripe_billing")

    async def _ensure_usage_row(self, db, tenant_id: uuid.UUID, plan_id: str) -> PlanUsage:
        usage_month = datetime.now(timezone.utc).strftime("%Y-%m")
        result = await db.execute(select(PlanUsage).where(PlanUsage.tenant_id == tenant_id, PlanUsage.usage_month == usage_month))
        usage = result.scalar_one_or_none()
        if usage is None:
            usage = PlanUsage(
                tenant_id=tenant_id,
                usage_month=usage_month,
                included_leads=included_leads_for(plan_id),
            )
            db.add(usage)
        else:
            usage.included_leads = included_leads_for(plan_id)
        await db.flush()
        return usage

    async def enforce_lead_quota(self, db, tenant_id: uuid.UUID) -> tuple[bool, PlanUsage]:
        tenant = await db.get(Tenant, tenant_id)
        plan_id = tenant.current_plan if tenant else "starter"
        usage = await self._ensure_usage_row(db, tenant_id, plan_id)
        return usage.leads_allocated < usage.included_leads, usage

    def billing_plan_views(self) -> list[dict[str, Any]]:
        views = []
        for config in (get_plan_config("starter"), get_plan_config("growth"), get_plan_config("pro")):
            payload = plan_payload(config)
            views.append(
                {
                    "id": payload["id"],
                    "name": payload["name"],
                    "price_monthly": payload["price_monthly"],
                    "setup_fee": payload["setup_fee"],
                    "included_leads": included_leads_for(config.id),
                    "stripe_price_id_configured": bool(settings.stripe_price_id_for_plan(config.id.value)),
                    "features": payload["enabled_features"],
                }
            )
        return views
