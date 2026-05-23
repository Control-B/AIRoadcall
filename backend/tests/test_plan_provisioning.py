import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

os.environ["ADMIN_API_KEY"] = "test-admin-key"

from app.api.plan_deps import require_tenant_feature  # noqa: E402
from app.api.routes import provisioning  # noqa: E402
from app.core.plan_config import PlanFeature, get_plan_config, get_plan_configs  # noqa: E402
from app.main import app  # noqa: E402
from app.services.ghl_service import GHLService  # noqa: E402
from app.services.provisioning_service import locked_features_for  # noqa: E402


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


class FakeDB:
    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def refresh(self, _obj):
        return None

    async def execute(self, _statement):
        return SimpleNamespace(scalar_one_or_none=lambda: None)

    def add(self, _obj):
        return None


async def _override_db():
    yield FakeDB()


def _fake_tenant(plan_id: str):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name=f"Roadcall {plan_id.title()} Tenant",
        slug=f"roadcall-{plan_id}",
        current_plan=plan_id,
        subscription_status="active",
        onboarding_status="not_started",
        setup_fee_status="paid",
        enabled_features=[feature.value for feature in get_plan_config(plan_id).features],
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_plan_configs_cover_required_tiers_and_permissions():
    configs = get_plan_configs()

    assert set(configs) == {"widget_only", "ai_telephony", "widget_voice", "enterprise", "standard", "professional", "advanced"}
    assert PlanFeature.ai_widget in configs["widget_only"].features
    assert PlanFeature.ai_answering in configs["ai_telephony"].features
    assert PlanFeature.ai_answering in configs["widget_voice"].features
    assert PlanFeature.map_view in configs["enterprise"].features
    assert PlanFeature.ghl_saas_mode in configs["standard"].features
    assert PlanFeature.mobile_app in configs["professional"].features
    assert PlanFeature.social_media_marketing in configs["advanced"].features
    assert configs["widget_only"].uses_saas_mode is False
    assert configs["standard"].automatic_subaccount_provisioning is True


def test_locked_features_show_upgrade_behavior():
    widget_only = get_plan_config("widget_only")
    locked = locked_features_for("widget_only", [feature.value for feature in widget_only.features])

    assert "ai_answering" in locked
    assert "social_media_marketing" in locked
    assert "ai_widget" not in locked


@pytest.mark.asyncio
async def test_plan_gating_allows_enabled_feature(monkeypatch):
    tenant = SimpleNamespace(id=uuid.uuid4(), current_plan="advanced")

    async def fake_has_feature(_db, tenant_id, feature):
        assert tenant_id == tenant.id
        assert feature == "social_media_marketing"
        return True, tenant

    monkeypatch.setattr("app.api.plan_deps.service.tenant_has_feature", fake_has_feature)
    dependency = require_tenant_feature(PlanFeature.social_media_marketing)

    assert await dependency(x_roadcall_tenant_id=str(tenant.id), db=None) is tenant


@pytest.mark.asyncio
async def test_plan_gating_blocks_locked_feature(monkeypatch):
    tenant = SimpleNamespace(id=uuid.uuid4(), current_plan="widget_only")

    async def fake_has_feature(_db, _tenant_id, feature):
        assert feature == "social_media_marketing"
        return False, tenant

    monkeypatch.setattr("app.api.plan_deps.service.tenant_has_feature", fake_has_feature)
    dependency = require_tenant_feature(PlanFeature.social_media_marketing)

    with pytest.raises(HTTPException) as exc:
        await dependency(x_roadcall_tenant_id=str(tenant.id), db=None)
    assert exc.value.status_code == 403
    assert "Upgrade is required" in exc.value.detail


@pytest.mark.asyncio
async def test_provisioning_endpoint_accepts_all_plans(monkeypatch):
    app.dependency_overrides[provisioning.get_db] = _override_db
    app.dependency_overrides[provisioning.require_admin_api_key] = lambda: None

    async def fake_provision_tenant(_db, payload):
        tenant = _fake_tenant(payload.plan_id)
        event = SimpleNamespace(id=uuid.uuid4())
        return tenant, {
            "id": payload.plan_id,
            "name": payload.plan_id.title(),
            "price_monthly": get_plan_config(payload.plan_id).price_monthly,
            "setup_fee": get_plan_config(payload.plan_id).setup_fee,
            "ecosystem": get_plan_config(payload.plan_id).ecosystem,
            "billing_system": get_plan_config(payload.plan_id).billing_system,
            "onboarding_mode": get_plan_config(payload.plan_id).onboarding_mode,
            "uses_saas_mode": get_plan_config(payload.plan_id).uses_saas_mode,
            "automatic_subaccount_provisioning": get_plan_config(payload.plan_id).automatic_subaccount_provisioning,
            "enabled_features": tenant.enabled_features,
            "ghl_snapshot_id": "snap_test",
            "allowed_modules": [],
            "webhook_permissions": [],
            "dashboard_permissions": [],
            "dispatch_permissions": [],
            "ai_feature_permissions": [],
        }, event, {"status": "skipped"}, []

    monkeypatch.setattr(provisioning.service, "provision_tenant", fake_provision_tenant)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        for plan_id in ("widget_only", "ai_telephony", "widget_voice", "enterprise", "standard", "professional", "advanced"):
            resp = await ac.post(
                "/api/provisioning/tenants",
                headers={"x-admin-key": "test-admin-key"},
                json={"plan_id": plan_id, "organization_name": f"{plan_id} Co", "setup_fee_status": "paid"},
            )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert body["tenant"]["current_plan"] == plan_id
            assert body["plan"]["id"] == plan_id


@pytest.mark.asyncio
async def test_ghl_snapshot_assignment_placeholder_is_safe_without_webhook(monkeypatch):
    service = GHLService()
    monkeypatch.setattr(service.settings, "GHL_PROVISIONING_WEBHOOK_URL", "")
    db = FakeDB()

    result = await service.trigger_snapshot_assignment_placeholder(
        db,
        organization_id=str(uuid.uuid4()),
        location_id="loc_123",
        snapshot_id="snap_123",
        plan_id="professional",
        tenant_id=str(uuid.uuid4()),
    )

    assert result["status"] == "skipped"
    assert "not configured" in result["message"]