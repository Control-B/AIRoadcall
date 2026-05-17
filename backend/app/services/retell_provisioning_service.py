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
    ) -> dict[str, Any]:
        flow_id = (conversation_flow_id or (connection.conversation_flow_id if connection else None) or self.settings.RETELL_CONVERSATION_FLOW_ID).strip()
        if not flow_id:
            raise RuntimeError("RETELL_CONVERSATION_FLOW_ID is not configured")

        dynamic_variables = self.build_dynamic_variables(tenant, metadata)
        service_advisor_prompt = self.build_service_advisor_prompt(tenant, metadata)
        agent_body = {
            "agent_name": f"Roadcall — {tenant.name} Service Desk",
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
