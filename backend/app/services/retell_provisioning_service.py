from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.tenant_provisioning import RetellConnection, Tenant

logger = get_logger(__name__)


SERVICE_ADVISOR_PROMPT_TEMPLATE = """You are the advisor on duty for {shop_name}.

Roadcall is the operating platform. Retell is only the phone engine. Never describe yourself as AI, a bot, or an assistant.

Persona:
- experienced diesel service advisor
- roadside dispatcher
- blue-collar professional
- urgent, calm, and direct

Business context:
- Shop name: {shop_name}
- Shop address: {shop_address}
- Hourly rate: {hourly_rate}
- Mobile service available: {mobile_service_available}
- Service radius: {service_radius_miles} miles
- After-hours mode: {after_hours_mode}
- Dispatch phone: {dispatch_phone}
- Fleet priority accounts: {fleet_priority_accounts}
- Supported services: {supported_services}
- Supported engines: {supported_engines}

Triage every call into exactly one operating path:
1. roadside emergency
2. mobile repair
3. shop visit
4. scheduled service

If roadside, capture highway, mile marker, direction, nearest exit, nearby truck stop, city, and state when available. Ask technical diesel questions only when useful: derate, DPF light, air pressure above 90 PSI, whether the truck can move, overheating, and whether it is cranking.

Classify the breakdown as one of: critical_oos, unsafe_to_drive, mobile_service_candidate, can_limp_to_shop, scheduled_service.

Track service categories: tire, reefer, no_start, air_leak, dpf_derate, electrical, trailer_repair, overheating, towing, pm_service.

Use Roadcall backend tools for dispatch tickets, location links, after-hours contacts, fleet contracts, bay availability, and appointments. Do not promise dispatch, pricing, appointment confirmation, or technician assignment until Roadcall backend confirms it.
"""


class RetellProvisioningService:
    """Server-side Retell provisioning bridge.

    Roadcall remains the source of truth. This service only mirrors a tenant's
    telephony agent into Retell so the subscriber account appears there.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = "https://api.retellai.com"

    def build_dynamic_variables(self, tenant: Tenant, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = metadata or {}
        return {
            "shop_name": tenant.name,
            "shop_address": metadata.get("shop_address") or "Not provided",
            "hourly_rate": metadata.get("hourly_rate") or "Not provided",
            "mobile_service_available": bool(metadata.get("mobile_service_available", True)),
            "service_radius_miles": metadata.get("service_radius_miles") or 50,
            "after_hours_mode": metadata.get("after_hours_mode") or "capture_and_escalate",
            "dispatch_phone": metadata.get("dispatch_phone") or tenant.contact_phone or "Not provided",
            "fleet_priority_accounts": metadata.get("fleet_priority_accounts") or [],
            "supported_services": metadata.get("supported_services") or ["tire", "no_start", "air_leak", "dpf_derate", "electrical", "trailer_repair", "overheating", "towing", "pm_service"],
            "supported_engines": metadata.get("supported_engines") or [],
        }

    def build_service_advisor_prompt(self, tenant: Tenant, metadata: dict[str, Any] | None = None) -> str:
        variables = self.build_dynamic_variables(tenant, metadata)
        return SERVICE_ADVISOR_PROMPT_TEMPLATE.format(**variables)

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        api_key = self.settings.RETELL_API_KEY.strip()
        if not api_key:
            raise RuntimeError("RETELL_API_KEY is not configured")
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method.upper(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read().decode() or "{}"
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode()[:800]
            raise RuntimeError(f"Retell API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Retell API network error: {exc}") from exc

    async def provision_agent(
        self,
        tenant: Tenant,
        connection: RetellConnection | None,
        *,
        metadata: dict[str, Any] | None = None,
        conversation_flow_id: str | None = None,
        voice_id: str = "11labs-Lily",
        vertical: str | None = None,
    ) -> dict[str, Any]:
        is_shop = (vertical or "").lower() == "shops"
        default_flow_id = (
            self.settings.RETELL_SHOP_CONVERSATION_FLOW_ID
            if is_shop
            else self.settings.RETELL_CONVERSATION_FLOW_ID
        )
        flow_id = (conversation_flow_id or (connection.conversation_flow_id if connection else None) or default_flow_id).strip()
        if not flow_id:
            missing = "RETELL_SHOP_CONVERSATION_FLOW_ID" if is_shop else "RETELL_CONVERSATION_FLOW_ID"
            raise RuntimeError(f"{missing} is not configured")

        dynamic_variables = self.build_dynamic_variables(tenant, metadata)
        service_advisor_prompt = self.build_service_advisor_prompt(tenant, metadata)
        agent_label = "Shop Receptionist" if is_shop else "Service Desk"
        agent_body = {
            "agent_name": f"Roadcall — {tenant.name} {agent_label}",
            "response_engine": {
                "type": "conversation-flow",
                "conversation_flow_id": flow_id,
            },
            "voice_id": voice_id,
            "language": "en-US",
            "interruption_sensitivity": 0.55,
            "responsiveness": 0.75,
            "voice_speed": 0.94,
            "voice_temperature": 0.7,
            "enable_backchannel": True,
            "backchannel_frequency": 0.45,
            "backchannel_words": ["okay", "got it", "right"],
            "max_call_duration_ms": 1800000,
            "end_call_after_silence_ms": 120000,
            "boosted_keywords": [
                tenant.name,
                "roadside",
                "diesel",
                "mechanic",
                "service desk",
                "dispatch",
                "tire",
                "reefer",
                "derate",
                "DPF",
                "air leak",
                "no start",
                "trailer repair",
            ],
            "normalize_for_speech": True,
        }

        path = f"/update-agent/{connection.agent_id}" if connection and connection.agent_id else "/create-agent"
        method = "PATCH" if connection and connection.agent_id else "POST"
        response = await asyncio.to_thread(self._request, method, path, agent_body)
        agent_id = response.get("agent_id") or (connection.agent_id if connection else None)
        if not agent_id:
            raise RuntimeError("Retell did not return an agent_id")

        return {
            "agent_id": agent_id,
            "conversation_flow_id": flow_id,
            "agent_name": agent_body["agent_name"],
            "provisioning_status": "active",
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "retell_response": response,
            "dynamic_variables": dynamic_variables,
            "service_advisor_prompt": service_advisor_prompt,
        }

    async def create_shop_test_call(
        self,
        *,
        to_number: str,
        agent_name: str | None = None,
        business_name: str | None = None,
        welcome_message: str | None = None,
        instructions: str | None = None,
        agent_type: str | None = None,
    ) -> dict[str, Any]:
        normalized_agent_type = (agent_type or "mechanic").strip().lower()
        if normalized_agent_type == "fleet":
            agent_id = (self.settings.RETELL_FLEET_AGENT_ID or self.settings.RETELL_AGENT_ID).strip()
            missing_message = "Roadcall fleet voice agent is not configured"
        elif normalized_agent_type == "roadside":
            agent_id = self.settings.RETELL_AGENT_ID.strip()
            missing_message = "Roadcall roadside dispatch voice agent is not configured"
        else:
            agent_id = self.settings.RETELL_SHOP_AGENT_ID.strip()
            missing_message = "Roadcall shop voice agent is not configured"
        if not agent_id:
            raise RuntimeError(missing_message)

        from_number = (self.settings.RETELL_TEST_FROM_NUMBER or self.settings.DEMO_PHONE_NUMBER).strip()
        if not from_number:
            raise RuntimeError("Roadcall test calling number is not configured")

        body = {
            "from_number": from_number,
            "to_number": to_number,
            "override_agent_id": agent_id,
            "metadata": {
                "source": "roadcall_agent_dashboard",
                "agent_type": normalized_agent_type,
            },
            "retell_llm_dynamic_variables": {
                "agent_name": agent_name or "Roadcall Service Advisor",
                "shop_name": business_name or "Roadcall shop",
                "business_name": business_name or "Roadcall shop",
                "welcome_message": welcome_message or "Thanks for calling Roadcall.",
                "dashboard_instructions": instructions or "Use Roadcall service advisor call handling rules.",
            },
        }
        response = await asyncio.to_thread(self._request, "POST", "/v2/create-phone-call", body)
        return {
            "call_id": response.get("call_id"),
            "call_status": response.get("call_status") or response.get("status") or "started",
            "provider_response": response,
        }
