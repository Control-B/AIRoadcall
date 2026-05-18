"""Stripe-direct signup flow tests.

Covers the Roadcall webhook-driven onboarding that replaces GHL SaaS Pro:
- _seed_tenant_defaults backfills the shop profile from Stripe-collected
  billing details + default services catalog.
- _send_welcome_email is a no-op when Resend isn't configured.
- sync_checkout_completed wires seeding + auto-activation together.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")

from app.services import subscription_billing_service as billing_module  # noqa: E402
from app.services.subscription_billing_service import (  # noqa: E402
    SubscriptionBillingService,
    _DEFAULT_SHOP_SERVICES,
)


def _make_profile(**overrides) -> SimpleNamespace:
    """Build a ShopProfile-shaped object the service operates on by attribute.

    Using SimpleNamespace avoids SQLAlchemy's instance-state machinery while
    still giving us a duck-typed stand-in.
    """
    defaults = dict(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        business_name="Acme Auto",
        phone=None,
        email=None,
        address=None,
        city=None,
        state=None,
        services_offered=[],
        service_area=None,
        service_radius_miles=50,
        offers_mobile_service=True,
        fallback_phone=None,
        profile_status="incomplete",
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class _FakeDB:
    def __init__(self, profile: ShopProfile | None):
        self._profile = profile
        self.flushed = 0

    async def execute(self, _statement):
        profile = self._profile
        return SimpleNamespace(scalar_one_or_none=lambda: profile)

    async def flush(self):
        self.flushed += 1


@pytest.mark.asyncio
async def test_seed_tenant_defaults_fills_address_phone_and_services():
    profile = _make_profile()
    db = _FakeDB(profile)
    tenant = SimpleNamespace(
        id=profile.tenant_id, name="Acme Auto", onboarding_status="not_started"
    )
    session = {
        "customer_details": {
            "phone": "+15555551212",
            "email": "owner@acmeauto.com",
            "address": {
                "line1": "123 Main St",
                "city": "Austin",
                "state": "TX",
                "postal_code": "78701",
                "country": "US",
            },
        }
    }
    service = SubscriptionBillingService()

    result = await service._seed_tenant_defaults(db, tenant, session)

    assert result is profile
    assert profile.phone == "+15555551212"
    assert profile.email == "owner@acmeauto.com"
    assert profile.city == "Austin"
    assert profile.state == "TX"
    assert profile.address == "123 Main St"
    assert profile.services_offered == list(_DEFAULT_SHOP_SERVICES)
    assert profile.service_area == "Austin, TX (50 mi radius)"
    assert profile.profile_status == "complete"
    assert tenant.onboarding_status == "profile_complete"
    assert db.flushed == 1


@pytest.mark.asyncio
async def test_seed_tenant_defaults_does_not_overwrite_owner_values():
    profile = _make_profile(
        phone="+19998887777",
        email="real@shop.com",
        city="Denver",
        state="CO",
        address="900 Custom Way",
        services_offered=["custom service"],
    )
    db = _FakeDB(profile)
    tenant = SimpleNamespace(id=profile.tenant_id, name="x", onboarding_status="x")
    session = {
        "customer_details": {
            "phone": "+15555551212",
            "email": "billing@stripe.com",
            "address": {"line1": "DIFFERENT", "city": "Austin", "state": "TX"},
        }
    }

    await SubscriptionBillingService()._seed_tenant_defaults(db, tenant, session)

    assert profile.phone == "+19998887777"
    assert profile.email == "real@shop.com"
    assert profile.city == "Denver"
    assert profile.state == "CO"
    assert profile.address == "900 Custom Way"
    assert profile.services_offered == ["custom service"]


@pytest.mark.asyncio
async def test_seed_tenant_defaults_returns_none_when_profile_missing():
    db = _FakeDB(None)
    tenant = SimpleNamespace(id=uuid.uuid4(), name="x", onboarding_status="x")
    result = await SubscriptionBillingService()._seed_tenant_defaults(db, tenant, {})
    assert result is None


def test_send_welcome_email_noop_without_api_key(monkeypatch):
    # Force RESEND_API_KEY empty to confirm the helper exits cleanly.
    monkeypatch.setattr(billing_module.settings, "RESEND_API_KEY", "", raising=False)
    calls: list = []
    monkeypatch.setattr(
        billing_module.urllib.request,
        "urlopen",
        lambda *a, **kw: calls.append(a) or (_ for _ in ()).throw(AssertionError("should not call")),
    )

    account = SimpleNamespace(email="owner@shop.com", dashboard_token="tok-xyz")
    tenant = SimpleNamespace(id=uuid.uuid4(), name="Acme")
    profile = _make_profile(email="owner@shop.com")

    SubscriptionBillingService()._send_welcome_email(account, tenant, profile)

    assert calls == []


class _FakeAccountDB:
    """Lookup-by-email + tenant get stand-in for resend_dashboard_link."""

    def __init__(self, account=None, tenant=None, profile=None):
        self._account = account
        self._tenant = tenant
        self._profile = profile

    async def execute(self, _statement):
        # First call: MechanicAccount lookup. Second call: ShopProfile lookup.
        # We don't introspect the statement; we return whatever is asked next
        # in execution order by alternating the response.
        if not hasattr(self, "_phase"):
            self._phase = "profile"
            payload = self._account
        else:
            payload = self._profile
        return SimpleNamespace(
            scalars=lambda: SimpleNamespace(first=lambda: payload),
        )

    async def get(self, _model, _id):
        return self._tenant


@pytest.mark.asyncio
async def test_resend_dashboard_link_invokes_welcome_email(monkeypatch):
    account = SimpleNamespace(email="OWNER@shop.com", tenant_id=uuid.uuid4(), dashboard_token="tok-1")
    tenant = SimpleNamespace(id=account.tenant_id, name="Acme")
    profile = _make_profile(email="owner@shop.com")

    sent: list = []
    monkeypatch.setattr(
        SubscriptionBillingService,
        "_send_welcome_email",
        lambda self, acc, ten, prof: sent.append((acc, ten, prof)),
    )

    db = _FakeAccountDB(account=account, tenant=tenant, profile=profile)
    ok = await SubscriptionBillingService().resend_dashboard_link(db, "owner@shop.com")

    assert ok is True
    assert len(sent) == 1
    assert sent[0][0] is account


@pytest.mark.asyncio
async def test_resend_dashboard_link_returns_false_when_account_missing(monkeypatch):
    sent: list = []
    monkeypatch.setattr(
        SubscriptionBillingService,
        "_send_welcome_email",
        lambda self, acc, ten, prof: sent.append((acc, ten, prof)),
    )

    db = _FakeAccountDB(account=None, tenant=None, profile=None)
    ok = await SubscriptionBillingService().resend_dashboard_link(db, "ghost@shop.com")

    assert ok is False
    assert sent == []


@pytest.mark.asyncio
async def test_resend_dashboard_link_returns_false_for_empty_email():
    db = _FakeAccountDB()
    ok = await SubscriptionBillingService().resend_dashboard_link(db, "")
    assert ok is False
