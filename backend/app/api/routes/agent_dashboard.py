from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.retell_provisioning_service import RetellProvisioningService

router = APIRouter(prefix="/agent-dashboard", tags=["agent-dashboard"])
logger = get_logger(__name__)
service = RetellProvisioningService()


class AgentTestCallIn(BaseModel):
    to_number: str = Field(min_length=7, max_length=32)
    agent_type: str = "mechanic"
    agent_name: str | None = None
    business_name: str | None = None
    welcome_message: str | None = None
    instructions: str | None = None


class AgentTestCallOut(BaseModel):
    ok: bool
    call_id: str | None = None
    call_status: str
    message: str


def _normalize_phone(value: str) -> str:
    stripped = value.strip()
    digits = re.sub(r"\D", "", stripped)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if stripped.startswith("+") and 8 <= len(digits) <= 15:
        return f"+{digits}"
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enter a valid phone number for the test call.")


@router.post("/test-call", response_model=AgentTestCallOut)
async def start_agent_test_call(payload: AgentTestCallIn) -> AgentTestCallOut:
    to_number = _normalize_phone(payload.to_number)
    try:
        result = await service.create_shop_test_call(
            to_number=to_number,
            agent_name=payload.agent_name,
            business_name=payload.business_name,
            welcome_message=payload.welcome_message,
            instructions=payload.instructions,
            agent_type=payload.agent_type,
        )
    except RuntimeError as exc:
        logger.warning("Roadcall test call could not start: %s", exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Roadcall test calling is not ready yet. Please contact support to finish phone activation.") from exc
    except Exception as exc:
        logger.exception("Roadcall test call failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Roadcall could not start the test call. Please try again shortly.") from exc

    return AgentTestCallOut(
        ok=True,
        call_id=result.get("call_id"),
        call_status=result.get("call_status") or "started",
        message="Roadcall test call started. Answer your phone to speak with the shop agent.",
    )
