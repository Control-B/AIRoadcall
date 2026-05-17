"""Shop Telephony Service — manages shop customers and their AI agents.

Handles:
- CRUD for shop telephony customers
- Building per-shop agent prompts
- Routing incoming calls to the right agent config
- Tracking call metrics
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.shop_customer import ShopCustomer
from app.models.shop_call_log import ShopCallLog
from app.schemas.shop import ShopCustomerCreate, ShopCustomerUpdate

logger = get_logger(__name__)


DEFAULT_SHOP_PROMPT_TEMPLATE = """You are a professional AI phone assistant for {business_name}.

YOUR ROLE:
- Answer incoming calls professionally as if you work at {business_name}
- Help callers with service inquiries, scheduling, and general questions
- Qualify potential leads and capture their contact information
- Handle after-hours calls and take messages

BUSINESS CONTEXT:
- Business: {business_name}
- Address: {business_address}
- Services: {services_offered}
- Service Area: {service_area}
- Hours: {hours_of_operation}
{roadside_context}

CALL HANDLING RULES:
1. ALWAYS greet the caller warmly and identify the business
2. Listen carefully to understand what they need
3. For service requests:
   - Ask about their vehicle (make, model, year)
   - Ask about the issue/service needed
   - Ask about their preferred timing
   - Provide general pricing info if available
4. For emergencies/roadside:
   - Get their exact location
   - Get vehicle description
   - Assess urgency
   - Let them know help is on the way
5. ALWAYS capture:
   - Caller's name
   - Phone number (confirm from caller ID)
   - Vehicle info
   - What they need
6. If you cannot help, offer to transfer to the shop owner at {fallback_phone}

TONE:
- Professional but friendly
- Speak like a knowledgeable shop employee
- Be helpful and patient
- Keep responses concise for phone conversation

When you have collected the caller's information, call the store_call_data function.
If the caller requests to speak to a human, call the transfer_call function."""


class ShopTelephonyService:
    """Service for managing shop telephony customers and AI agents."""

    # ── CRUD Operations ──────────────────────────────────────

    @staticmethod
    async def create_shop(
        db: AsyncSession, data: ShopCustomerCreate
    ) -> ShopCustomer:
        """Create a new shop telephony customer with auto-generated prompt."""
        # Build the agent prompt if not provided
        prompt = data.agent_prompt
        if not prompt:
            prompt = ShopTelephonyService._build_default_prompt(data)

        shop = ShopCustomer(
            id=uuid.uuid4(),
            business_name=data.business_name,
            owner_name=data.owner_name,
            business_phone=data.business_phone,
            business_email=data.business_email,
            business_address=data.business_address,
            agent_prompt=prompt,
            agent_greeting=data.agent_greeting,
            voice_id=data.voice_id,
            text_agent_id=data.text_agent_id,
            services_offered=data.services_offered,
            service_area=data.service_area,
            hours_of_operation=data.hours_of_operation,
            offers_roadside=data.offers_roadside,
            knowledge_base=data.knowledge_base,
            sip_phone_number=data.sip_phone_number,
            sip_trunk_id=data.sip_trunk_id,
            fallback_phone=data.fallback_phone,
            phone_onboarding_mode=data.phone_onboarding_mode,
            requested_area_code=data.requested_area_code,
            twilio_number_sid=data.twilio_number_sid,
            twilio_number_status=data.twilio_number_status,
            retell_agent_id=data.retell_agent_id,
            retell_phone_number_id=data.retell_phone_number_id,
            retell_flow_id=data.retell_flow_id,
            appointment_booking_enabled=data.appointment_booking_enabled,
            calcom_calendar_url=data.calcom_calendar_url,
            calcom_event_type_id=data.calcom_event_type_id,
            after_hours_enabled=data.after_hours_enabled,
            emergency_dispatch_enabled=data.emergency_dispatch_enabled,
            plan=data.plan,
            active=True,
        )
        db.add(shop)
        await db.commit()
        await db.refresh(shop)
        logger.info(f"Created shop customer: {shop.business_name} ({shop.id})")
        return shop

    @staticmethod
    async def get_shop(db: AsyncSession, shop_id: uuid.UUID) -> Optional[ShopCustomer]:
        """Get a shop customer by ID."""
        result = await db.execute(
            select(ShopCustomer).where(ShopCustomer.id == shop_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_shop_by_phone(
        db: AsyncSession, phone: str
    ) -> Optional[ShopCustomer]:
        """Look up a shop by their SIP phone number (for call routing)."""
        result = await db.execute(
            select(ShopCustomer).where(
                ShopCustomer.sip_phone_number == phone,
                ShopCustomer.active == True,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_shop_by_business_phone(
        db: AsyncSession, phone: str
    ) -> Optional[ShopCustomer]:
        """Look up a shop by their business phone number."""
        result = await db.execute(
            select(ShopCustomer).where(
                ShopCustomer.business_phone == phone,
                ShopCustomer.active == True,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_shops(
        db: AsyncSession, active_only: bool = True, limit: int = 100, offset: int = 0
    ) -> list[ShopCustomer]:
        """List all shop customers."""
        query = select(ShopCustomer).limit(limit).offset(offset)
        if active_only:
            query = query.where(ShopCustomer.active == True)
        query = query.order_by(ShopCustomer.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_shop(
        db: AsyncSession, shop_id: uuid.UUID, data: ShopCustomerUpdate
    ) -> Optional[ShopCustomer]:
        """Update a shop customer's configuration."""
        shop = await ShopTelephonyService.get_shop(db, shop_id)
        if not shop:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(shop, field, value)

        shop.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(shop)
        logger.info(f"Updated shop customer: {shop.business_name} ({shop.id})")
        return shop

    @staticmethod
    async def delete_shop(db: AsyncSession, shop_id: uuid.UUID) -> bool:
        """Deactivate a shop customer (soft delete)."""
        shop = await ShopTelephonyService.get_shop(db, shop_id)
        if not shop:
            return False
        shop.active = False
        shop.updated_at = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Deactivated shop customer: {shop.business_name} ({shop.id})")
        return True

    # ── Call Routing ─────────────────────────────────────────

    @staticmethod
    async def get_agent_config(
        db: AsyncSession, called_number: str
    ) -> Optional[dict]:
        """Get the AI agent configuration for a shop by the called number.

        This is called when an incoming call arrives at a SIP number.
        We look up which shop owns that number and return their agent config.
        """
        shop = await ShopTelephonyService.get_shop_by_phone(db, called_number)
        if not shop:
            # Try by business phone as fallback
            shop = await ShopTelephonyService.get_shop_by_business_phone(
                db, called_number
            )

        if not shop:
            logger.warning(f"No shop found for called number: {called_number}")
            return None

        config = {
            "shop_id": str(shop.id),
            "business_name": shop.business_name,
            "agent_prompt": shop.agent_prompt,
            "agent_greeting": shop.agent_greeting,
            "voice_id": shop.voice_id,
            "text_agent_id": shop.text_agent_id,
            "fallback_phone": shop.fallback_phone,
            "services_offered": shop.services_offered,
            "hours_of_operation": shop.hours_of_operation,
            "offers_roadside": shop.offers_roadside,
            "knowledge_base": shop.knowledge_base,
            "phone_onboarding_mode": shop.phone_onboarding_mode,
            "twilio_number_status": shop.twilio_number_status,
            "retell_agent_id": shop.retell_agent_id,
            "retell_phone_number_id": shop.retell_phone_number_id,
            "retell_flow_id": shop.retell_flow_id,
            "appointment_booking_enabled": shop.appointment_booking_enabled,
            "calcom_calendar_url": shop.calcom_calendar_url,
            "calcom_event_type_id": shop.calcom_event_type_id,
            "after_hours_enabled": shop.after_hours_enabled,
            "emergency_dispatch_enabled": shop.emergency_dispatch_enabled,
        }

        logger.info(
            f"Loaded agent config for {shop.business_name} "
            f"(shop_id={shop.id}, called={called_number})"
        )
        return config

    @staticmethod
    async def get_agent_config_by_id(
        db: AsyncSession, shop_id: uuid.UUID
    ) -> Optional[dict]:
        """Get agent config by shop ID directly."""
        shop = await ShopTelephonyService.get_shop(db, shop_id)
        if not shop or not shop.active:
            return None

        return {
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
            "phone_onboarding_mode": shop.phone_onboarding_mode,
            "twilio_number_status": shop.twilio_number_status,
            "retell_agent_id": shop.retell_agent_id,
            "retell_phone_number_id": shop.retell_phone_number_id,
            "retell_flow_id": shop.retell_flow_id,
            "appointment_booking_enabled": shop.appointment_booking_enabled,
            "calcom_calendar_url": shop.calcom_calendar_url,
            "calcom_event_type_id": shop.calcom_event_type_id,
            "after_hours_enabled": shop.after_hours_enabled,
            "emergency_dispatch_enabled": shop.emergency_dispatch_enabled,
        }

    # ── Call Logging ─────────────────────────────────────────

    @staticmethod
    async def log_call(
        db: AsyncSession,
        shop_id: uuid.UUID,
        caller_phone: str,
        channel: str = "voice",
        direction: str = "inbound",
        **kwargs,
    ) -> ShopCallLog:
        """Create a call log entry."""
        log = ShopCallLog(
            id=uuid.uuid4(),
            shop_id=shop_id,
            caller_phone=caller_phone,
            channel=channel,
            direction=direction,
            **kwargs,
        )
        db.add(log)

        # Increment shop metrics
        shop = await ShopTelephonyService.get_shop(db, shop_id)
        if shop:
            if channel == "voice":
                shop.total_calls_handled += 1
            else:
                shop.total_chats_handled += 1
            if kwargs.get("is_qualified_lead"):
                shop.total_leads_captured += 1
            if kwargs.get("forwarded_to_human"):
                shop.total_calls_forwarded += 1

        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def get_call_logs(
        db: AsyncSession,
        shop_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ShopCallLog]:
        """Get call logs for a shop."""
        result = await db.execute(
            select(ShopCallLog)
            .where(ShopCallLog.shop_id == shop_id)
            .order_by(ShopCallLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    # ── Prompt Building ──────────────────────────────────────

    @staticmethod
    def _build_default_prompt(data: ShopCustomerCreate) -> str:
        """Build a default agent prompt from shop data."""
        roadside_context = ""
        if data.offers_roadside:
            roadside_context = (
                "- This shop offers MOBILE ROADSIDE SERVICE\n"
                "- For roadside emergencies, prioritize getting the caller's location"
            )

        services = ", ".join(data.services_offered) if data.services_offered else "General truck repair and maintenance"
        hours = json.dumps(data.hours_of_operation) if data.hours_of_operation else "Contact shop for hours"
        fallback = data.fallback_phone or data.business_phone

        return DEFAULT_SHOP_PROMPT_TEMPLATE.format(
            business_name=data.business_name,
            business_address=data.business_address or "Contact shop for address",
            services_offered=services,
            service_area=data.service_area or "Local area",
            hours_of_operation=hours,
            roadside_context=roadside_context,
            fallback_phone=fallback,
        )
