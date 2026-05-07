"""Shop Telephony API routes.

CRUD for shop customers, call routing, text chat, and call logs.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.logging import get_logger
from app.schemas.shop import (
    ShopCustomerCreate,
    ShopCustomerUpdate,
    ShopCustomerResponse,
    ShopCallLogResponse,
    ChatRequest,
    ChatResponse,
    IncomingCallRequest,
)
from app.services.shop_telephony_service import ShopTelephonyService
from app.services.do_ai_chat_service import DOAIChatService

router = APIRouter(prefix="/shops", tags=["shop-telephony"])
logger = get_logger(__name__)


# ── Shop Customer CRUD ─────────────────────────────────────


@router.post("/", response_model=ShopCustomerResponse, status_code=201)
async def create_shop(
    data: ShopCustomerCreate,
    db: AsyncSession = Depends(get_session),
):
    """Onboard a new mechanic shop for AI telephony."""
    shop = await ShopTelephonyService.create_shop(db, data)
    return shop


@router.get("/", response_model=list[ShopCustomerResponse])
async def list_shops(
    active_only: bool = True,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    """List all shop telephony customers."""
    shops = await ShopTelephonyService.list_shops(db, active_only, limit, offset)
    return shops


@router.get("/{shop_id}", response_model=ShopCustomerResponse)
async def get_shop(
    shop_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Get a shop customer by ID."""
    shop = await ShopTelephonyService.get_shop(db, shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    return shop


@router.patch("/{shop_id}", response_model=ShopCustomerResponse)
async def update_shop(
    shop_id: uuid.UUID,
    data: ShopCustomerUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update a shop customer's configuration."""
    shop = await ShopTelephonyService.update_shop(db, shop_id, data)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")
    return shop


@router.delete("/{shop_id}", status_code=204)
async def delete_shop(
    shop_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Deactivate a shop customer (soft delete)."""
    success = await ShopTelephonyService.delete_shop(db, shop_id)
    if not success:
        raise HTTPException(status_code=404, detail="Shop not found")


# ── Call Routing ─────────────────────────────────────────────


@router.post("/incoming-call")
async def handle_incoming_call(
    data: IncomingCallRequest,
    db: AsyncSession = Depends(get_session),
):
    """Route an incoming call to the correct shop's AI agent.

    Called by the SIP trunk when a call arrives at a shop's number.
    Looks up the shop config and returns the agent configuration.
    """
    config = await ShopTelephonyService.get_agent_config(db, data.called_number)

    if not config:
        logger.warning(f"No shop config for number: {data.called_number}")
        raise HTTPException(
            status_code=404,
            detail=f"No shop configured for number: {data.called_number}",
        )

    # Log the incoming call
    await ShopTelephonyService.log_call(
        db,
        shop_id=uuid.UUID(config["shop_id"]),
        caller_phone=data.caller_number,
        channel="voice",
        direction="inbound",
        status="in_progress",
        livekit_room_name=data.call_id,
    )

    logger.info(
        f"Routing call from {data.caller_number} to shop {config['business_name']} "
        f"(shop_id={config['shop_id']})"
    )

    return {
        "status": "routed",
        "shop_id": config["shop_id"],
        "business_name": config["business_name"],
        "agent_config": {
            "type": "shop_inbound",
            "shop_id": config["shop_id"],
            "business_name": config["business_name"],
            "prompt": config["agent_prompt"],
            "greeting": config["agent_greeting"],
            "voice_id": config["voice_id"],
            "fallback_phone": config["fallback_phone"],
            "caller_phone": data.caller_number,
        },
    }


# ── Text Chat ────────────────────────────────────────────────


@router.post("/chat", response_model=ChatResponse)
async def shop_chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_session),
):
    """Handle a text chat message for a shop's AI agent.

    Uses DO AI Gradient for text-based customer service.
    """
    config = await ShopTelephonyService.get_agent_config_by_id(db, data.shop_id)
    if not config:
        shop = await ShopTelephonyService.get_shop(db, data.shop_id)
        if not shop or not shop.active:
            raise HTTPException(status_code=404, detail="Shop not found or inactive")
        config = {
            "shop_id": str(shop.id),
            "business_name": shop.business_name,
            "agent_prompt": shop.agent_prompt,
            "agent_greeting": shop.agent_greeting,
            "voice_id": shop.voice_id,
            "text_agent_id": shop.text_agent_id,
            "fallback_phone": shop.fallback_phone or shop.business_phone,
            "services_offered": shop.services_offered,
            "hours_of_operation": shop.hours_of_operation,
            "offers_roadside": shop.offers_roadside,
            "knowledge_base": shop.knowledge_base,
        }

    result = await DOAIChatService.chat(
        shop_config=config,
        message=data.message,
        conversation_id=data.conversation_id,
    )

    # Log the chat interaction
    await ShopTelephonyService.log_call(
        db,
        shop_id=data.shop_id,
        caller_phone=data.caller_phone or "web_chat",
        channel="text",
        direction="inbound",
        intent=result.get("intent"),
        intent_summary=data.message[:500],
        is_qualified_lead=result.get("is_qualified_lead", False),
        status="completed",
    )

    return ChatResponse(**result)


# ── Call Logs ────────────────────────────────────────────────


@router.get("/{shop_id}/calls", response_model=list[ShopCallLogResponse])
async def get_call_logs(
    shop_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
):
    """Get call logs for a shop."""
    shop = await ShopTelephonyService.get_shop(db, shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    logs = await ShopTelephonyService.get_call_logs(db, shop_id, limit, offset)
    return logs


# ── Shop Stats ───────────────────────────────────────────────


@router.get("/{shop_id}/stats")
async def get_shop_stats(
    shop_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    """Get usage stats for a shop."""
    shop = await ShopTelephonyService.get_shop(db, shop_id)
    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    return {
        "shop_id": str(shop.id),
        "business_name": shop.business_name,
        "plan": shop.plan,
        "stats": {
            "total_calls_handled": shop.total_calls_handled,
            "total_leads_captured": shop.total_leads_captured,
            "total_chats_handled": shop.total_chats_handled,
            "total_calls_forwarded": shop.total_calls_forwarded,
        },
        "active": shop.active,
    }
