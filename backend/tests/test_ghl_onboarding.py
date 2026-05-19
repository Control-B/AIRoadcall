"""Tests for GHL onboarding setup endpoint."""
import os
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["ADMIN_API_KEY"] = "test-admin-key"

from app.main import app  # noqa: E402
from app.api.routes import ghl  # noqa: E402


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


async def _override_db():
    yield None


@pytest.mark.asyncio
async def test_onboarding_setup_uses_api_key_and_upserts_mapping(monkeypatch):
    app.dependency_overrides[ghl.get_db] = _override_db

    async def fake_create_subaccount(api_key, subaccount_payload):
        assert api_key == "ghl-api-key"
        assert subaccount_payload["name"] == "Roadcall Test Subaccount"
        return {
            "location_id": "loc_created_1",
            "subaccount": {"id": "loc_created_1", "name": "Roadcall Test Subaccount"},
            "raw": {"ok": True},
        }

    async def fake_get_location(api_key, location_id):
        assert api_key == "ghl-api-key"
        assert location_id == "loc_created_1"
        return {"id": "loc_created_1", "name": "Roadcall Test Subaccount"}

    async def fake_upsert_mapping(
        db,
        *,
        organization_id,
        location_id,
        subaccount_name=None,
        access_token=None,
        refresh_token=None,
        webhook_secret=None,
        pipeline_id=None,
        default_workflow_id=None,
    ):
        return SimpleNamespace(
            id="11111111-1111-1111-1111-111111111111",
            organization_id=organization_id,
            location_id=location_id,
            subaccount_name=subaccount_name,
            pipeline_id=pipeline_id,
            default_workflow_id=default_workflow_id,
            agency_id=None,
            ghl_user_id=None,
            token_expires_at=None,
            scopes=None,
            token_source=None,
            is_active=True,
        )

    async def fake_commit():
        return None

    async def fake_refresh(_):
        return None

    monkeypatch.setattr(ghl.service, "create_subaccount_via_api_key", fake_create_subaccount)
    monkeypatch.setattr(ghl.service, "get_location_via_api_key", fake_get_location)
    monkeypatch.setattr(ghl.service, "upsert_mapping", fake_upsert_mapping)
    monkeypatch.setattr(ghl.service.settings, "GHL_API_KEY", "")

    fake_db = SimpleNamespace(commit=fake_commit, refresh=fake_refresh)

    async def _override_fake_db():
        yield fake_db

    app.dependency_overrides[ghl.get_db] = _override_fake_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/ghl/admin/onboarding/setup",
            headers={"x-admin-key": "test-admin-key"},
            json={
                "organization_id": "00000000-0000-0000-0000-000000000123",
                "create_subaccount": True,
                "subaccount_name": "Roadcall Test Subaccount",
                "ghl_api_key": "ghl-api-key",
                "subaccount_payload": {
                    "name": "Roadcall Test Subaccount",
                    "companyName": "Roadcall Fleet",
                },
                "pipeline_id": "pipe_1",
                "default_workflow_id": "wf_1",
            },
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["subaccount_created"] is True
    assert body["location_id"] == "loc_created_1"
    assert body["mapping"]["location_id"] == "loc_created_1"
    assert body["mapping"]["default_workflow_id"] == "wf_1"
