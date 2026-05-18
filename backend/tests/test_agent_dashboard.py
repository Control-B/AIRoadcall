import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.api.routes import agent_dashboard


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
                "agent_name": "Roadcall Fleet Dispatcher",
            },
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Roadcall test call started. Answer your phone to speak with the fleet dispatcher."
    assert service.phone_payload["to_number"] == "+17272728156"
    assert service.phone_payload["agent_type"] == "fleet"


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
    assert service.web_payload["company_phone"] == "+17272728156"
    assert service.web_payload["forward_phone"] == "+17275550100"
