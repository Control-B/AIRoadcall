"""Tests for Retell location request flow with Twilio Studio support."""
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

os.environ["RETELL_BACKEND_WEBHOOK_TOKEN"] = "test-token"

from app.main import app  # noqa: E402
from app.api.deps import get_session  # noqa: E402
from app.api.routes import retell_dispatch  # noqa: E402
from app.services.sms_provider import SmsProviderType  # noqa: E402
from app.services.sms_service import SMSService  # noqa: E402


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


async def _override_session():
    yield None


@pytest.mark.asyncio
async def test_request_location_uses_twilio_studio_when_configured(monkeypatch):
    app.dependency_overrides[get_session] = _override_session

    job = SimpleNamespace(
        public_job_id="RC-TEST1234",
        magic_link_token="tok_123",
        magic_link_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        driver_name="Alex",
    )

    async def fake_get_job(service_request_id, db):
        assert service_request_id == "RC-TEST1234"
        return job

    async def fake_start_studio(to_number, parameters, flow_sid=None, status_callback=None):
        assert to_number == "+14075551234"
        assert parameters["service_request_id"] == "RC-TEST1234"
        assert parameters["secure_location_token"] == "tok_123"
        return "FN_EXEC_123"

    monkeypatch.setattr(retell_dispatch, "_get_job_or_404", fake_get_job)
    monkeypatch.setattr(SMSService, "start_twilio_studio_execution", fake_start_studio)
    monkeypatch.setattr(retell_dispatch.settings, "TWILIO_STUDIO_FLOW_SID", "FW123")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/location/request",
            headers={"Authorization": "Bearer test-token"},
            json={
                "service_request_id": "RC-TEST1234",
                "callback_number": "+14075551234",
            },
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["location_status"] == "studio_started"
    assert body["secure_location_token"] == "tok_123"
    assert body["location_url"].endswith("/support/tok_123")


@pytest.mark.asyncio
async def test_request_location_falls_back_to_direct_sms_when_studio_fails(monkeypatch):
    app.dependency_overrides[get_session] = _override_session

    job = SimpleNamespace(
        public_job_id="RC-TEST5678",
        magic_link_token="tok_456",
        magic_link_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        driver_name="Jordan",
    )

    async def fake_get_job(service_request_id, db):
        return job

    async def fake_start_studio(to_number, parameters, flow_sid=None, status_callback=None):
        return None

    async def fake_send_magic_link(phone_number, magic_link_url, driver_name):
        assert phone_number == "+14075550000"
        assert magic_link_url.endswith("/support/tok_456")
        assert driver_name == "Jordan"
        return True

    monkeypatch.setattr(retell_dispatch, "_get_job_or_404", fake_get_job)
    monkeypatch.setattr(SMSService, "start_twilio_studio_execution", fake_start_studio)
    monkeypatch.setattr(SMSService, "send_magic_link", fake_send_magic_link)
    monkeypatch.setattr(retell_dispatch.settings, "TWILIO_STUDIO_FLOW_SID", "FW123")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/location/request",
            headers={"Authorization": "Bearer test-token"},
            json={
                "service_request_id": "RC-TEST5678",
                "callback_number": "+14075550000",
            },
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["location_status"] == "sms_sent"


@pytest.mark.asyncio
async def test_request_location_falls_back_to_ghl_sms_when_direct_sms_fails(monkeypatch):
    app.dependency_overrides[get_session] = _override_session

    job = SimpleNamespace(
        public_job_id="RC-TEST9999",
        magic_link_token="tok_999",
        magic_link_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        driver_name="Riley",
    )

    async def fake_get_job(service_request_id, db):
        return job

    async def fake_send_magic_link(phone_number, magic_link_url, driver_name):
        return False

    class _FakeResult:
        success = True
        provider = SmsProviderType.ghl
        message_id = "ghl-msg-123"
        error = None

    def fake_ghl_send(self, to, body, from_number=None):
        assert to == "+14075559999"
        assert "support/tok_999" in body
        return _FakeResult()

    monkeypatch.setattr(retell_dispatch, "_get_job_or_404", fake_get_job)
    monkeypatch.setattr(SMSService, "send_magic_link", fake_send_magic_link)
    monkeypatch.setattr(retell_dispatch.settings, "GHL_API_KEY", "ghl-key")
    monkeypatch.setattr(retell_dispatch.settings, "GHL_LOCATION_ID", "loc_123")
    monkeypatch.setattr(retell_dispatch.settings, "GHL_FROM_NUMBER", "+18665550101")
    monkeypatch.setattr(retell_dispatch.settings, "TWILIO_STUDIO_FLOW_SID", "")
    monkeypatch.setattr(retell_dispatch.GhlSmsProvider, "send", fake_ghl_send)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/location/request",
            headers={"Authorization": "Bearer test-token"},
            json={
                "service_request_id": "RC-TEST9999",
                "callback_number": "+14075559999",
            },
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["location_status"] == "ghl_sms_sent"


@pytest.mark.asyncio
async def test_location_status_returns_captured_with_coordinates(monkeypatch):
    app.dependency_overrides[get_session] = _override_session

    captured_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    job = SimpleNamespace(
        public_job_id="RC-CAPTURED",
        magic_link_token="tok_cap",
        magic_link_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        driver_lat=28.5383,
        driver_lng=-81.3792,
        driver_city="Orlando",
        driver_state="FL",
        driver_location_captured_at=captured_at,
    )

    async def fake_get_job(service_request_id, db):
        return job

    monkeypatch.setattr(retell_dispatch, "_get_job_or_404", fake_get_job)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/location/status",
            headers={"Authorization": "Bearer test-token"},
            json={"service_request_id": "RC-CAPTURED"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["location_status"] == "captured"
    assert body["location_captured"] is True
    assert body["lat"] == 28.5383
    assert body["lng"] == -81.3792


@pytest.mark.asyncio
async def test_location_status_returns_expired_when_magic_link_expired(monkeypatch):
    app.dependency_overrides[get_session] = _override_session

    job = SimpleNamespace(
        public_job_id="RC-EXPIRED",
        magic_link_token="tok_exp",
        magic_link_expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        driver_lat=None,
        driver_lng=None,
        driver_city=None,
        driver_state=None,
        driver_location_captured_at=None,
    )

    async def fake_get_job(service_request_id, db):
        return job

    monkeypatch.setattr(retell_dispatch, "_get_job_or_404", fake_get_job)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/location/status",
            headers={"Authorization": "Bearer test-token"},
            json={"service_request_id": "RC-EXPIRED"},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["location_status"] == "expired"
    assert body["location_captured"] is False
