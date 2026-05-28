from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.sms_provider import GhlSmsProvider, TwilioSmsProvider
from app.services.sms_service import SMSService


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = "{}"

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_twilio_provider_blocks_non_mobile_number(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*args, **kwargs):
        return FakeResponse({"line_type_intelligence": {"type": "landline"}})

    monkeypatch.setattr("httpx.get", fake_get)

    provider = TwilioSmsProvider("AC123", "token", "+17275550000")
    result = provider.send("+17275550123", "Roadcall.ai: test")

    assert result.success is False
    assert result.error == "Phone number is not SMS-safe mobile line type: landline"


def test_sms_service_blocks_non_mobile_number_before_twilio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = SimpleNamespace(
        TWILIO_ACCOUNT_SID="AC123",
        TWILIO_AUTH_TOKEN="token",
        TELNYX_API_KEY="",
        TELNYX_FROM_NUMBER="",
    )

    def fake_get(*args, **kwargs):
        return FakeResponse({"line_type_intelligence": {"type": "landline"}})

    def fake_send_via_twilio(*args, **kwargs):
        raise AssertionError("Twilio send should not run for non-mobile numbers")

    monkeypatch.setattr("app.services.sms_service.get_settings", lambda: cfg)
    monkeypatch.setattr("httpx.get", fake_get)
    monkeypatch.setattr(SMSService, "_send_via_twilio", fake_send_via_twilio)

    assert SMSService._send_sync("+17275550123", "Roadcall.ai: test") is False


def test_ghl_provider_blocks_non_mobile_number(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*args, **kwargs):
        return FakeResponse({"line_type_intelligence": {"type": "fixedVoip"}})

    def fake_post(*args, **kwargs):
        raise AssertionError("GHL send should not run for non-mobile numbers")

    monkeypatch.setattr("httpx.get", fake_get)
    monkeypatch.setattr("httpx.post", fake_post)

    provider = GhlSmsProvider(
        "ghl-key",
        "loc-123",
        twilio_account_sid="AC123",
        twilio_auth_token="token",
    )
    result = provider.send("+17275550123", "Roadcall.ai: test")

    assert result.success is False
    assert result.error == "Phone number is not SMS-safe mobile line type: fixedVoip"


def test_ghl_provider_blocks_existing_contact_with_sms_dnd(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, *args, **kwargs):
        if "lookups.twilio.com" in url:
            return FakeResponse({"line_type_intelligence": {"type": "mobile"}})
        return FakeResponse(
            {
                "contacts": [
                    {
                        "id": "contact-123",
                        "phone": "+1 727-555-0123",
                        "dndSettings": {"SMS": {"status": "active"}},
                    }
                ]
            }
        )

    def fake_post(*args, **kwargs):
        raise AssertionError("GHL send should not run when SMS DND is active")

    monkeypatch.setattr("httpx.get", fake_get)
    monkeypatch.setattr("httpx.post", fake_post)

    provider = GhlSmsProvider(
        "ghl-key",
        "loc-123",
        twilio_account_sid="AC123",
        twilio_auth_token="token",
    )
    result = provider.send("+17275550123", "Roadcall.ai: test")

    assert result.success is False
    assert result.error == "GHL contact has SMS DND enabled: contact-123"


def test_ghl_provider_sends_when_mobile_and_not_dnd(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url, *args, **kwargs):
        if "lookups.twilio.com" in url:
            return FakeResponse({"line_type_intelligence": {"type": "mobile"}})
        return FakeResponse({"contacts": [{"id": "contact-123", "phone": "+17275550123"}]})

    def fake_post(*args, **kwargs):
        return FakeResponse({"messageId": "msg-123"})

    monkeypatch.setattr("httpx.get", fake_get)
    monkeypatch.setattr("httpx.post", fake_post)

    provider = GhlSmsProvider(
        "ghl-key",
        "loc-123",
        twilio_account_sid="AC123",
        twilio_auth_token="token",
    )
    result = provider.send("+17275550123", "Roadcall.ai: test")

    assert result.success is True
    assert result.message_id == "msg-123"
