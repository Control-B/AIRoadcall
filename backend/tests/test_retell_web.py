import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("RETELL_BACKEND_WEBHOOK_TOKEN", "test-token")

from app.api.deps import get_session  # noqa: E402
from app.api.routes import retell_web  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.dispatch_session import DispatchCreateSessionResponse  # noqa: E402
from app.services.dispatch_session_service import DispatchSessionService  # noqa: E402
from app.services.geocoding_service import GeocodingService  # noqa: E402


@pytest.fixture(autouse=True)
def configure_settings():
    get_settings.cache_clear()
    settings = get_settings()
    settings.RETELL_API_KEY = "test-retell-key"
    settings.RETELL_AGENT_ID = "canonical-sandy-agent"
    settings.RETELL_ROADSIDE_WEB_AGENT_ID = "stale-web-agent"
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


async def _empty_session():
    yield None


@pytest.mark.asyncio
async def test_roadside_web_call_sends_locked_gps_context(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    session_id = uuid.uuid4()
    captured = {}

    async def fake_reverse_geocode(latitude, longitude):
        return {
            "place_name": "I-4 Exit 32, Lakeland, Florida, United States",
            "city": "Lakeland",
            "state": "FL",
        }

    async def fake_create_session(db, payload):
        assert payload.source == "retell_web_gps"
        assert payload.latitude == 28.0395
        assert payload.longitude == -81.9498
        assert payload.location_source == "browser_gps"
        return DispatchCreateSessionResponse(
            dispatch_session_id=session_id,
            public_code="RC-1234",
            status="matching",
            location_url="https://roadcall.ai/go?t=token",
            location_token="token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            latitude=payload.latitude,
            longitude=payload.longitude,
            city=payload.city,
            state=payload.state,
            address=payload.address,
        )

    def fake_create_web_call(api_key, body):
        captured["api_key"] = api_key
        captured["body"] = body
        return {"call_id": "retell-call", "access_token": "web-token"}

    monkeypatch.setattr(GeocodingService, "reverse_geocode", fake_reverse_geocode)
    monkeypatch.setattr(DispatchSessionService, "create_session", fake_create_session)
    monkeypatch.setattr(retell_web, "_retell_create_web_call", fake_create_web_call)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/retell/roadside-web-call",
            json={"latitude": 28.0395, "longitude": -81.9498, "accuracy_meters": 15},
        )

    assert response.status_code == 200, response.text
    assert captured["api_key"] == "test-retell-key"
    assert captured["body"]["agent_id"] == "canonical-sandy-agent"
    assert captured["body"]["current_node_id"] == "start-node"

    dynamic_vars = captured["body"]["retell_llm_dynamic_variables"]
    assert dynamic_vars["has_shared_gps"] == "true"
    assert dynamic_vars["dispatch_session_id"] == str(session_id)
    assert dynamic_vars["gps_latitude"] == "28.039500"
    assert dynamic_vars["gps_longitude"] == "-81.949800"
    assert dynamic_vars["caller_location_phrase"] == (
        "near I-4 Exit 32, Lakeland, Florida, United States in Lakeland, FL"
    )
    assert "Do not ask for city" in dynamic_vars["web_call_opening_instruction"]
    assert captured["body"]["metadata"]["caller_city"] == "Lakeland"


@pytest.mark.asyncio
async def test_roadside_web_call_location_phrase_falls_back_to_coordinates(monkeypatch):
    app.dependency_overrides[get_session] = _empty_session
    session_id = uuid.uuid4()
    captured = {}

    async def fake_reverse_geocode(latitude, longitude):
        return None

    async def fake_create_session(db, payload):
        return DispatchCreateSessionResponse(
            dispatch_session_id=session_id,
            public_code="RC-1234",
            status="matching",
            location_url="https://roadcall.ai/go?t=token",
            location_token="token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            latitude=payload.latitude,
            longitude=payload.longitude,
            city=payload.city,
            state=payload.state,
            address=payload.address,
        )

    def fake_create_web_call(api_key, body):
        captured["body"] = body
        return {"call_id": "retell-call", "access_token": "web-token"}

    monkeypatch.setattr(GeocodingService, "reverse_geocode", fake_reverse_geocode)
    monkeypatch.setattr(DispatchSessionService, "create_session", fake_create_session)
    monkeypatch.setattr(retell_web, "_retell_create_web_call", fake_create_web_call)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/retell/roadside-web-call",
            json={"latitude": 28.0395, "longitude": -81.9498},
        )

    assert response.status_code == 200, response.text
    dynamic_vars = captured["body"]["retell_llm_dynamic_variables"]
    assert dynamic_vars["caller_location_phrase"] == (
        "at the GPS spot you just shared (roughly 28.0395, -81.9498)"
    )
    assert dynamic_vars["caller_address"] == ""
    assert dynamic_vars["caller_city"] == ""
    assert dynamic_vars["caller_state"] == ""
