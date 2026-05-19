import uuid
from types import SimpleNamespace

from app.services.shop_snapshot_service import DEFAULT_WORKFLOWS, ShopSnapshotService


def _obj(**kwargs):
    return SimpleNamespace(**kwargs)


def test_shop_snapshot_defaults_are_retell_intake_not_missed_call():
    intake = next(item for item in DEFAULT_WORKFLOWS if item["workflow_key"] == "retell_intake_qualification")
    sms_ack = next(item for item in DEFAULT_WORKFLOWS if item["workflow_key"] == "sms_lead_acknowledgement")
    missed_call = next(item for item in DEFAULT_WORKFLOWS if item["workflow_key"] == "missed_call_recovery")

    assert intake["trigger_event"] == "retell.call.completed"
    assert intake["config"]["qualifies_lead"] is True
    assert intake["config"]["missed_call_recovery"] is True
    assert sms_ack["channel"] == "sms"
    assert sms_ack["config"]["provider"] == "twilio"
    assert missed_call["trigger_event"] == "call.missed"
    assert missed_call["config"]["template_key"] == "missed_call_text_back"


def test_shop_snapshot_readiness_blocks_on_twilio_and_retell():
    service = ShopSnapshotService()
    tenant = _obj(id=uuid.uuid4(), subscription_status="active")
    account = _obj(email="owner@example.com")
    profile = _obj(
        business_name="Strong Diesel",
        phone="+15555550100",
        email="owner@example.com",
        address="10 Shop Rd",
        city="Akron",
        state="OH",
        services_offered=["diesel diagnostics"],
        business_hours={"monday": {"open": "08:00", "close": "17:00"}},
    )
    workflows = [
        _obj(enabled=True),
        _obj(enabled=True),
        _obj(enabled=True),
        _obj(enabled=True),
        _obj(enabled=True),
    ]

    readiness = service.build_readiness(
        tenant=tenant,
        account=account,
        profile=profile,
        messaging=_obj(status="needs_twilio_number"),
        retell_connection=_obj(agent_id=None, conversation_flow_id=None),
        retell_number=_obj(routing_status="ready"),
        subscription=None,
        workflows=workflows,
    )

    assert readiness["ready"] is False
    assert "twilio_sms" in readiness["blockers"]
    assert "retell_template" in readiness["blockers"]
    assert "calendar" in readiness["manual_setup"]


def test_shop_snapshot_readiness_allows_calendar_as_manual_setup():
    service = ShopSnapshotService()
    tenant = _obj(id=uuid.uuid4(), subscription_status="active")
    account = _obj(email="owner@example.com")
    profile = _obj(
        business_name="Strong Diesel",
        phone="+15555550100",
        email="owner@example.com",
        address="10 Shop Rd",
        city="Akron",
        state="OH",
        services_offered=["diesel diagnostics"],
        business_hours={"monday": {"open": "08:00", "close": "17:00"}},
        calcom_event_type_id=None,
        calcom_calendar_url=None,
    )
    workflows = [_obj(enabled=True) for _ in range(5)]

    readiness = service.build_readiness(
        tenant=tenant,
        account=account,
        profile=profile,
        messaging=_obj(status="ready"),
        retell_connection=_obj(agent_id=None, conversation_flow_id="flow_shop"),
        retell_number=_obj(routing_status="ready"),
        subscription=None,
        workflows=workflows,
    )

    assert readiness["ready"] is True
    assert readiness["blockers"] == []
    assert "calendar" in readiness["manual_setup"]


def test_shop_snapshot_generates_calcom_booking_url():
    service = ShopSnapshotService()
    payload = _obj(calcom_username="strong-diesel", calcom_event_slug="roadcall-service", calcom_base_url=None)
    org = _obj(name="Strong Diesel")

    assert service._generated_calcom_url(payload, org) == "https://cal.com/strong-diesel/roadcall-service"
