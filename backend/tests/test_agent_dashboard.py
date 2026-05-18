import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.routes import agent_dashboard
from app.services.retell_provisioning_service import RetellProvisioningService


class FakeAgentDashboardService:
    def __init__(self):
        self.phone_payload = None
        self.web_payload = None

    async def create_shop_test_call(self, **kwargs):
        self.phone_payload = kwargs
        return {"call_id": "phone-call-1", "call_status": "started"}

    async def create_agent_web_call(self, **kwargs):
        self.web_payload = kwargs
        return {"call_id": "web-call-1", "access_token": "retell-access-token"}


class FakeRetellSettings:
    RETELL_API_KEY = "retell-key"
    RETELL_AGENT_ID = "roadside-agent"
    RETELL_SHOP_AGENT_ID = "shop-agent"
    RETELL_FLEET_AGENT_ID = "fleet-agent"
    RETELL_TEST_OUTBOUND_AGENT_ID = "fleet-test-agent"
    RETELL_TEST_FROM_NUMBER = "+17275550000"
    DEMO_PHONE_NUMBER = ""
    RETELL_FEMALE_VOICE_ID = "11labs-Lily"
    RETELL_MALE_VOICE_ID = "retell-Cimo"
    RETELL_CLONED_VOICE_ID = ""


@pytest.mark.asyncio
async def test_phone_test_call_is_fleet_only(monkeypatch):
    service = FakeAgentDashboardService()
    monkeypatch.setattr(agent_dashboard, "service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/agent-dashboard/test-call", json={"to_number": "+17272728156", "agent_type": "mechanic"})

    assert response.status_code == 403
    assert service.phone_payload is None


@pytest.mark.asyncio
async def test_fleet_phone_test_call_uses_retell_service(monkeypatch):
    service = FakeAgentDashboardService()
    monkeypatch.setattr(agent_dashboard, "service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/agent-dashboard/test-call",
            json={
                "to_number": "7272728156",
                "agent_type": "fleet",
                "voice": "male",
                "agent_name": "Roadcall Fleet Dispatcher",
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Roadcall test call started. Answer your phone to speak with the fleet dispatcher."
    assert service.phone_payload["to_number"] == "+17272728156"
    assert service.phone_payload["agent_type"] == "fleet"
    assert service.phone_payload["voice"] == "male"


@pytest.mark.asyncio
async def test_web_call_returns_retell_access_token(monkeypatch):
    service = FakeAgentDashboardService()
    monkeypatch.setattr(agent_dashboard, "service", service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/agent-dashboard/web-call",
            json={
                "agent_type": "mechanic",
                "voice": "male",
                "agent_name": "Roadcall Service Advisor",
                "business_name": "Diesel repair shop",
                "company_phone": "+17272728156",
                "forward_phone": "+17275550100",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] == "retell-access-token"
    assert body["message"] == "Browser preview started. Speak with the mechanic service advisor from this page."
    assert service.web_payload["agent_type"] == "mechanic"
    assert service.web_payload["voice"] == "male"
    assert service.web_payload["company_phone"] == "+17272728156"
    assert service.web_payload["forward_phone"] == "+17275550100"


@pytest.mark.asyncio
async def test_fleet_phone_test_call_uses_test_agent_and_voice_override():
    service = RetellProvisioningService()
    service.settings = FakeRetellSettings()
    captured = {}

    def fake_request(method, path, body):
        captured["method"] = method
        captured["path"] = path
        captured["body"] = body
        return {"call_id": "retell-phone-call", "call_status": "registered"}

    service._request = fake_request

    result = await service.create_shop_test_call(to_number="+17272728156", agent_type="fleet", voice="male")

    assert result["call_id"] == "retell-phone-call"
    assert captured["method"] == "POST"
    assert captured["path"] == "/v2/create-phone-call"
    assert captured["body"]["from_number"] == "+17275550000"
    assert captured["body"]["override_agent_id"] == "fleet-test-agent"
    assert captured["body"]["agent_override"] == {"voice_id": "retell-Cimo"}
    assert captured["body"]["metadata"]["voice"] == "male"


@pytest.mark.asyncio
async def test_web_preview_uses_selected_voice_override():
    service = RetellProvisioningService()
    service.settings = FakeRetellSettings()
    captured = {}

    def fake_request(method, path, body):
        captured["method"] = method
        captured["path"] = path
        captured["body"] = body
        return {"call_id": "retell-web-call", "access_token": "access-token"}

    service._request = fake_request

    result = await service.create_agent_web_call(agent_type="mechanic", voice="male")

    assert result["access_token"] == "access-token"
    assert captured["method"] == "POST"
    assert captured["path"] == "/v2/create-web-call"
    assert captured["body"]["agent_id"] == "shop-agent"
    assert captured["body"]["agent_override"] == {"voice_id": "retell-Cimo"}
    assert captured["body"]["retell_llm_dynamic_variables"]["voice"] == "male"
