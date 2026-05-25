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
- practical heavy-duty diagnostic intake specialist
- blue-collar professional
- urgent, calm, and direct

Call facts ledger:
- Silently maintain caller_name, issue_type, issue_description, vehicle_type, city, state, location_code, service_request_id, and selected_provider.
- Once the caller says a fact or a tool returns it, treat it as known for the rest of the call.
- Before asking any question, check the ledger and the prior transcript. If the answer is already known, move to the next missing fact or next tool call.
- Never ask the same open-ended question twice. If a fact may have been misheard, confirm it once with yes/no phrasing, for example: "I have a semi with a tire issue in Lakeland, Florida - is that right?"
- Normalize common caller language without asking again: flat, blowout, spare, tire off rim, and low air mean tire; won't start, dead battery, no crank, and crank no start mean no_start or battery as stated; semi, tractor, eighteen-wheeler, rig, box truck, pickup, car, trailer, RV, and fleet vehicle are valid vehicle types.

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

Mechanical triage rules:
- Ask one precise diagnostic question at a time; do not interrogate the caller.
- Do not restart intake after a tool call. Reuse the ledger and only ask for fields that are truly missing.
- Capture unit number, truck year/make/model when available, engine make, trailer type, loaded/empty status, and any dash fault code or warning lamp.
- For no-start, distinguish no-crank from crank-no-start, then ask about battery voltage, jump attempts, starter click, fuel level, recent fuel filter work, and whether lights dim while cranking.
- For derate/DPF/DEF, ask about check-engine/stop-engine lights, active regen attempts, DEF level/quality warnings, speed limit derate, smoke, and whether the truck can safely limp.
- For air/brake issues, ask current PSI, whether pressure builds above 90 PSI, audible leaks, spring brakes locked, trailer vs tractor source, and whether the unit is safe to move.
- For overheating/coolant/oil pressure, ask gauge behavior, leak location, steam, fan operation, oil pressure warning, and whether the engine has been shut down.
- For tires/trailers/reefers, capture steer/drive/trailer position, tire size if visible, loaded status, brake lockup, air line/electrical issues, reefer fuel/temperature/alarm code.
- Classify whether the next step is safe-to-drive, limp-to-shop, mobile repair, tow, or out-of-service.

Classify the breakdown as one of: critical_oos, unsafe_to_drive, mobile_service_candidate, can_limp_to_shop, scheduled_service.

Track service categories: tire, reefer, no_start, air_leak, dpf_derate, electrical, trailer_repair, overheating, towing, pm_service.

Caller location workflow — follow this every time a caller needs roadside or mobile help:
1. Call save_driver_info once caller_name, vehicle_type, or issue_type is known. Pass every known ledger fact; do not delay just because one optional field is missing.
   Do NOT ask the caller for their phone number — the system captures it automatically.
2. The tool will return either "Got it, I already have your GPS …" (the caller pre-shared location from the website) OR a message asking you to collect location verbally.
3. If the location is already attached, continue with mechanical triage and then call find_nearby_mechanics. Do NOT ask the caller to open any URL or enter a code.
4. If the location is NOT attached, ask the caller for: highway, exit number, nearest truck stop, city, and state. If they prefer, suggest they tap "Share my location" on roadcall.ai and call back — do not interrupt the call to wait for that.
5. While gathering location, continue only missing triage questions from the ledger (vehicle info, issue details, safety check). Do not ask again for fields the caller already gave.
6. Call check_location to re-poll for a website share, then call find_nearby_mechanics once location is known.

Do NOT ask for the caller's phone number. Do NOT say "check your texts". Do NOT mention any short codes or /go URLs — the location is shared from the website button before the call.
Do not promise dispatch, pricing, appointment confirmation, or technician assignment until Roadcall backend confirms it.
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

    def _agent_id_for_type(self, agent_type: str | None) -> tuple[str, str, str]:
        normalized_agent_type = (agent_type or "mechanic").strip().lower()
        if normalized_agent_type == "fleet":
            return normalized_agent_type, (self.settings.RETELL_FLEET_AGENT_ID or self.settings.RETELL_AGENT_ID).strip(), "Roadcall fleet voice agent is not configured"
        if normalized_agent_type == "roadside":
            return normalized_agent_type, self.settings.RETELL_AGENT_ID.strip(), "Roadcall roadside dispatch voice agent is not configured"
        return "mechanic", self.settings.RETELL_SHOP_AGENT_ID.strip(), "Roadcall shop voice agent is not configured"

    def _test_call_agent_id_for_type(self, agent_type: str | None) -> tuple[str, str, str]:
        normalized_agent_type, default_agent_id, missing_message = self._agent_id_for_type(agent_type)
        if normalized_agent_type == "fleet":
            test_agent_id = (self.settings.RETELL_TEST_OUTBOUND_AGENT_ID or default_agent_id).strip()
            return normalized_agent_type, test_agent_id, "Roadcall fleet test outbound voice agent is not configured"
        return normalized_agent_type, default_agent_id, missing_message

    def _voice_id_for_choice(self, voice: str | None) -> tuple[str, str | None]:
        normalized_voice = (voice or "female").strip().lower()
        if normalized_voice == "male":
            return "male", (self.settings.RETELL_MALE_VOICE_ID or "retell-Cimo").strip()
        if normalized_voice == "clone":
            cloned_voice_id = self.settings.RETELL_CLONED_VOICE_ID.strip()
            if cloned_voice_id:
                return "clone", cloned_voice_id
            return "female", (self.settings.RETELL_FEMALE_VOICE_ID or "11labs-Lily").strip()
        return "female", (self.settings.RETELL_FEMALE_VOICE_ID or "11labs-Lily").strip()

    def _agent_override_for_voice(self, voice: str | None) -> tuple[str, dict[str, Any]]:
        voice_choice, voice_id = self._voice_id_for_choice(voice)
        if not voice_id:
            return voice_choice, {}
        return voice_choice, {
            "agent": {
                "voice_id": voice_id,
                "voice_speed": 0.95 if voice_choice == "male" else 0.93,
                "voice_temperature": 0.7,
            }
        }

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
        voice: str | None = None,
    ) -> dict[str, Any]:
        normalized_agent_type, agent_id, missing_message = self._test_call_agent_id_for_type(agent_type)
        if not agent_id:
            raise RuntimeError(missing_message)

        from_number = (self.settings.RETELL_TEST_FROM_NUMBER or self.settings.DEMO_PHONE_NUMBER).strip()
        if not from_number:
            raise RuntimeError("RETELL_TEST_FROM_NUMBER must be a Retell-owned or imported number before outbound phone tests can start")

        voice_choice, agent_override = self._agent_override_for_voice(voice)

        body = {
            "from_number": from_number,
            "to_number": to_number,
            "override_agent_id": agent_id,
            "metadata": {
                "source": "roadcall_agent_dashboard",
                "agent_type": normalized_agent_type,
                "voice": voice_choice,
            },
            "retell_llm_dynamic_variables": {
                "agent_name": agent_name or "Roadcall Service Advisor",
                "shop_name": business_name or "Roadcall shop",
                "business_name": business_name or "Roadcall shop",
                "voice": voice_choice,
                "welcome_message": welcome_message or "Thanks for calling Roadcall.",
                "dashboard_instructions": instructions or "Use Roadcall service advisor call handling rules. Ask diesel diagnostic questions one at a time and classify whether the vehicle is safe to drive, can limp to a shop, needs mobile repair, needs a tow, or is out of service.",
            },
        }
        if agent_override:
            body["agent_override"] = agent_override
        response = await asyncio.to_thread(self._request, "POST", "/v2/create-phone-call", body)
        return {
            "call_id": response.get("call_id"),
            "call_status": response.get("call_status") or response.get("status") or "started",
            "provider_response": response,
        }

    async def create_agent_web_call(
        self,
        *,
        agent_name: str | None = None,
        business_name: str | None = None,
        company_phone: str | None = None,
        forward_phone: str | None = None,
        welcome_message: str | None = None,
        instructions: str | None = None,
        agent_type: str | None = None,
        voice: str | None = None,
    ) -> dict[str, Any]:
        normalized_agent_type, agent_id, missing_message = self._agent_id_for_type(agent_type)
        if not agent_id:
            raise RuntimeError(missing_message)

        voice_choice, agent_override = self._agent_override_for_voice(voice)

        body = {
            "agent_id": agent_id,
            "metadata": {
                "source": "roadcall_agent_dashboard_preview",
                "agent_type": normalized_agent_type,
                "voice": voice_choice,
            },
            "retell_llm_dynamic_variables": {
                "agent_name": agent_name or "Roadcall Service Advisor",
                "shop_name": business_name or "Roadcall shop",
                "business_name": business_name or "Roadcall shop",
                "company_phone": company_phone or "Not provided",
                "forward_phone": forward_phone or "Not provided",
                "dispatch_phone": forward_phone or company_phone or "Not provided",
                "voice": voice_choice,
                "welcome_message": welcome_message or "Thanks for calling Roadcall.",
                "dashboard_instructions": instructions or "Use Roadcall service advisor call handling rules. Ask diesel diagnostic questions one at a time and classify whether the vehicle is safe to drive, can limp to a shop, needs mobile repair, needs a tow, or is out of service.",
            },
        }
        if agent_override:
            body["agent_override"] = agent_override
        response = await asyncio.to_thread(self._request, "POST", "/v2/create-web-call", body)
        return {
            "call_id": response.get("call_id"),
            "access_token": response.get("access_token"),
            "provider_response": response,
        }
