"""Outreach Service — campaign management, segmentation, and message delivery."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, or_, and_, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.mechanic import Mechanic
from app.models.outreach_campaign import OutreachCampaign, OutreachMessage
from app.schemas.outreach import (
    CampaignCreate,
    CampaignUpdate,
    SegmentFilters,
)

logger = get_logger(__name__)
settings = get_settings()


class OutreachService:

    # ── Campaign CRUD ────────────────────────────────────────

    @staticmethod
    async def create_campaign(db: AsyncSession, data: CampaignCreate) -> OutreachCampaign:
        campaign = OutreachCampaign(
            id=uuid.uuid4(),
            name=data.name,
            description=data.description,
            channel=data.channel,
            subject=data.subject,
            body_template=data.body_template,
            segment_filters=data.segment_filters,
            scheduled_at=data.scheduled_at,
            status="draft",
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        logger.info(f"Created campaign: {campaign.name} ({campaign.id})")
        return campaign

    @staticmethod
    async def get_campaign(db: AsyncSession, campaign_id: uuid.UUID) -> Optional[OutreachCampaign]:
        result = await db.execute(
            select(OutreachCampaign).where(OutreachCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_campaigns(
        db: AsyncSession, limit: int = 50, offset: int = 0
    ) -> list[OutreachCampaign]:
        result = await db.execute(
            select(OutreachCampaign)
            .order_by(OutreachCampaign.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def update_campaign(
        db: AsyncSession, campaign_id: uuid.UUID, data: CampaignUpdate
    ) -> Optional[OutreachCampaign]:
        campaign = await OutreachService.get_campaign(db, campaign_id)
        if not campaign:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)
        campaign.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(campaign)
        return campaign

    @staticmethod
    async def delete_campaign(db: AsyncSession, campaign_id: uuid.UUID) -> bool:
        campaign = await OutreachService.get_campaign(db, campaign_id)
        if not campaign:
            return False
        await db.delete(campaign)
        await db.commit()
        return True

    # ── Segmentation ─────────────────────────────────────────

    @staticmethod
    def _build_segment_query(filters: Optional[dict] = None):
        """Build a SQLAlchemy query from segment filters."""
        query = select(Mechanic).where(Mechanic.active == True)

        if not filters:
            return query

        # State filter — extract from address
        if filters.get("states"):
            state_conditions = []
            for state in filters["states"]:
                state_conditions.append(
                    Mechanic.address.ilike(f"%, {state} %")
                )
            if state_conditions:
                query = query.where(or_(*state_conditions))

        # Roadside filter
        if filters.get("roadside_only"):
            query = query.where(Mechanic.accepts_mobile_roadside == True)

        # Rating filter
        if filters.get("min_rating"):
            query = query.where(Mechanic.rating >= filters["min_rating"])

        # Review count filter
        if filters.get("min_reviews"):
            query = query.where(Mechanic.review_count >= filters["min_reviews"])

        # Website filter
        if filters.get("has_website"):
            query = query.where(
                and_(Mechanic.website.isnot(None), Mechanic.website != "")
            )

        # Lead status filter
        if filters.get("lead_statuses"):
            query = query.where(Mechanic.lead_status.in_(filters["lead_statuses"]))

        # Limit
        if filters.get("limit"):
            query = query.limit(filters["limit"])

        return query

    @staticmethod
    async def preview_segment(
        db: AsyncSession, filters: Optional[dict] = None
    ) -> dict:
        """Preview how many mechanics match a segment."""
        base_query = OutreachService._build_segment_query(filters)

        # Get count
        count_query = select(func.count()).select_from(base_query.subquery())
        result = await db.execute(count_query)
        total = result.scalar() or 0

        # Get sample
        sample_query = base_query.limit(10)
        sample_result = await db.execute(sample_query)
        mechanics = sample_result.scalars().all()

        sample = [
            {
                "id": str(m.id),
                "company_name": m.company_name,
                "phone": m.phone,
                "address": m.address,
                "rating": float(m.rating) if m.rating else None,
                "review_count": m.review_count,
                "lead_status": m.lead_status if hasattr(m, "lead_status") else "new",
            }
            for m in mechanics
        ]

        return {"total_matching": total, "sample": sample}

    # ── Send Campaign ────────────────────────────────────────

    @staticmethod
    async def send_campaign(
        db: AsyncSession, campaign_id: uuid.UUID, batch_size: int = 100
    ) -> dict:
        """Queue messages for a campaign. Returns send stats."""
        campaign = await OutreachService.get_campaign(db, campaign_id)
        if not campaign:
            return {"error": "Campaign not found"}
        if campaign.status not in ("draft", "paused"):
            return {"error": f"Campaign is {campaign.status}, cannot send"}

        # Get targeted mechanics
        query = OutreachService._build_segment_query(campaign.segment_filters)
        result = await db.execute(query)
        mechanics = result.scalars().all()

        if not mechanics:
            return {"error": "No mechanics match the segment filters"}

        campaign.status = "sending"
        campaign.started_at = datetime.now(timezone.utc)
        campaign.total_targeted = len(mechanics)

        # Create outreach messages
        messages_created = 0
        for mechanic in mechanics:
            # Determine address based on channel
            if campaign.channel == "sms":
                to_address = mechanic.phone
            elif campaign.channel == "email":
                to_address = mechanic.email
                if not to_address:
                    continue
            else:
                to_address = mechanic.phone

            # Check for existing message in this campaign
            existing = await db.execute(
                select(OutreachMessage).where(
                    OutreachMessage.campaign_id == campaign_id,
                    OutreachMessage.mechanic_id == mechanic.id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Render template
            rendered_body = campaign.body_template.format(
                business_name=mechanic.company_name,
                phone=mechanic.phone,
                address=mechanic.address or "your area",
                demo_number=settings.DEMO_PHONE_NUMBER,
                demo_url=f"{settings.FRONTEND_URL}/demo",
            )

            msg = OutreachMessage(
                id=uuid.uuid4(),
                campaign_id=campaign_id,
                mechanic_id=mechanic.id,
                channel=campaign.channel,
                to_address=to_address,
                status="pending",
            )
            db.add(msg)
            messages_created += 1

            # Update mechanic lead status if it's new
            if not mechanic.lead_status or mechanic.lead_status == "new":
                mechanic.lead_status = "contacted"

        await db.commit()

        logger.info(
            f"Campaign {campaign.name}: queued {messages_created} messages "
            f"for {len(mechanics)} targeted mechanics"
        )

        return {
            "campaign_id": str(campaign_id),
            "total_targeted": len(mechanics),
            "messages_queued": messages_created,
            "status": "sending",
        }

    @staticmethod
    async def process_pending_messages(
        db: AsyncSession, campaign_id: uuid.UUID, batch_size: int = 50
    ) -> dict:
        """Process pending messages — actually send SMS/email via provider.

        This would be called by a background worker. For now, uses Twilio for SMS.
        """
        result = await db.execute(
            select(OutreachMessage)
            .where(
                OutreachMessage.campaign_id == campaign_id,
                OutreachMessage.status == "pending",
            )
            .limit(batch_size)
        )
        messages = list(result.scalars().all())

        sent_count = 0
        failed_count = 0

        for msg in messages:
            try:
                if msg.channel == "sms":
                    success = await OutreachService._send_sms(
                        msg.to_address, msg, db
                    )
                elif msg.channel == "email":
                    success = await OutreachService._send_email(
                        msg.to_address, msg, db
                    )
                else:
                    success = False

                if success:
                    msg.status = "sent"
                    msg.sent_at = datetime.now(timezone.utc)
                    sent_count += 1
                else:
                    msg.status = "failed"
                    failed_count += 1

            except Exception as e:
                msg.status = "failed"
                msg.error_message = str(e)[:500]
                failed_count += 1
                logger.error(f"Failed to send message {msg.id}: {e}")

        # Update campaign stats
        campaign = await OutreachService.get_campaign(db, campaign_id)
        if campaign:
            campaign.total_sent += sent_count

            # Check if all messages processed
            pending_result = await db.execute(
                select(func.count()).where(
                    OutreachMessage.campaign_id == campaign_id,
                    OutreachMessage.status == "pending",
                )
            )
            pending_count = pending_result.scalar() or 0
            if pending_count == 0:
                campaign.status = "completed"
                campaign.completed_at = datetime.now(timezone.utc)

        await db.commit()

        return {
            "batch_sent": sent_count,
            "batch_failed": failed_count,
            "remaining": pending_count if campaign else 0,
        }

    # ── SMS Delivery ─────────────────────────────────────────

    @staticmethod
    async def _send_sms(to: str, msg: OutreachMessage, db: AsyncSession) -> bool:
        """Send SMS via Twilio."""
        try:
            # Get the campaign to render the body
            campaign = await OutreachService.get_campaign(db, msg.campaign_id)
            if not campaign:
                return False

            # Get the mechanic for template rendering
            mech_result = await db.execute(
                select(Mechanic).where(Mechanic.id == msg.mechanic_id)
            )
            mechanic = mech_result.scalar_one_or_none()
            if not mechanic:
                return False

            body = campaign.body_template.format(
                business_name=mechanic.company_name,
                phone=mechanic.phone,
                address=mechanic.address or "your area",
                demo_number=settings.DEMO_PHONE_NUMBER,
                demo_url=f"{settings.FRONTEND_URL}/demo",
            )

            if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
                from twilio.rest import Client
                client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                message = client.messages.create(
                    body=body,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=to,
                )
                msg.provider_message_id = message.sid
                logger.info(f"SMS sent to {to}: {message.sid}")
                return True
            else:
                # Stub mode — log and mark as sent for testing
                logger.info(f"[STUB] SMS to {to}: {body[:100]}...")
                msg.provider_message_id = f"stub_{uuid.uuid4().hex[:8]}"
                return True

        except Exception as e:
            msg.error_message = str(e)[:500]
            logger.error(f"SMS send failed to {to}: {e}")
            return False

    @staticmethod
    async def _send_email(to: str, msg: OutreachMessage, db: AsyncSession) -> bool:
        """Send email via Resend."""
        try:
            campaign = await OutreachService.get_campaign(db, msg.campaign_id)
            if not campaign:
                return False

            mech_result = await db.execute(
                select(Mechanic).where(Mechanic.id == msg.mechanic_id)
            )
            mechanic = mech_result.scalar_one_or_none()
            if not mechanic:
                return False

            body = campaign.body_template.format(
                business_name=mechanic.company_name,
                phone=mechanic.phone,
                address=mechanic.address or "your area",
                demo_number=settings.DEMO_PHONE_NUMBER,
                demo_url=f"{settings.FRONTEND_URL}/demo",
            )

            if settings.RESEND_API_KEY:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.resend.com/emails",
                        headers={
                            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "from": settings.RESEND_FROM_EMAIL,
                            "to": [to],
                            "subject": campaign.subject or f"AI Receptionist for {mechanic.company_name}",
                            "html": body,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        msg.provider_message_id = data.get("id", "")
                        logger.info(f"Email sent to {to}: {msg.provider_message_id}")
                        return True
                    else:
                        msg.error_message = resp.text[:500]
                        return False
            else:
                logger.info(f"[STUB] Email to {to}: {campaign.subject}")
                msg.provider_message_id = f"stub_{uuid.uuid4().hex[:8]}"
                return True

        except Exception as e:
            msg.error_message = str(e)[:500]
            logger.error(f"Email send failed to {to}: {e}")
            return False

    # ── Campaign Stats ───────────────────────────────────────

    @staticmethod
    async def get_campaign_stats(db: AsyncSession, campaign_id: uuid.UUID) -> dict:
        """Get detailed stats for a campaign."""
        campaign = await OutreachService.get_campaign(db, campaign_id)
        if not campaign:
            return {}

        # Get message status breakdown
        status_query = await db.execute(
            select(OutreachMessage.status, func.count())
            .where(OutreachMessage.campaign_id == campaign_id)
            .group_by(OutreachMessage.status)
        )
        status_breakdown = dict(status_query.all())

        total_sent = campaign.total_sent or 1  # avoid division by zero

        return {
            "campaign_id": str(campaign_id),
            "name": campaign.name,
            "channel": campaign.channel,
            "status": campaign.status,
            "total_targeted": campaign.total_targeted,
            "total_sent": campaign.total_sent,
            "total_delivered": campaign.total_delivered,
            "total_opened": campaign.total_opened,
            "total_clicked": campaign.total_clicked,
            "total_replied": campaign.total_replied,
            "total_demo_calls": campaign.total_demo_calls,
            "total_signups": campaign.total_signups,
            "delivery_rate": round(campaign.total_delivered / total_sent, 3),
            "open_rate": round(campaign.total_opened / total_sent, 3),
            "click_rate": round(campaign.total_clicked / total_sent, 3),
            "reply_rate": round(campaign.total_replied / total_sent, 3),
            "demo_rate": round(campaign.total_demo_calls / total_sent, 3),
            "signup_rate": round(campaign.total_signups / total_sent, 3),
            "message_statuses": status_breakdown,
        }

    # ── Dashboard Stats ──────────────────────────────────────

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> dict:
        """Get overall outreach dashboard stats."""
        async def scalar_or_zero(query, label: str) -> int:
            try:
                result = await db.execute(query)
                return int(result.scalar() or 0)
            except SQLAlchemyError as exc:
                logger.warning("Dashboard stat '%s' unavailable: %s", label, exc)
                await db.rollback()
                return 0

        total = await scalar_or_zero(select(func.count()).select_from(Mechanic), "total_mechanics")
        with_phone = await scalar_or_zero(
            select(func.count()).where(Mechanic.phone.isnot(None), Mechanic.phone != ""),
            "total_with_phone",
        )
        with_email = await scalar_or_zero(
            select(func.count()).where(Mechanic.email.isnot(None), Mechanic.email != ""),
            "total_with_email",
        )
        with_website = await scalar_or_zero(
            select(func.count()).where(Mechanic.website.isnot(None), Mechanic.website != ""),
            "total_with_website",
        )
        total_campaigns = await scalar_or_zero(
            select(func.count()).select_from(OutreachCampaign),
            "total_campaigns",
        )
        total_sent = await scalar_or_zero(
            select(func.count()).where(OutreachMessage.status != "pending"),
            "total_messages_sent",
        )

        lead_breakdown = {}
        try:
            lead_query = await db.execute(
                select(Mechanic.lead_status, func.count()).group_by(Mechanic.lead_status)
            )
            for status, count in lead_query.all():
                lead_breakdown[status or "new"] = count
        except SQLAlchemyError as exc:
            logger.warning("Dashboard lead status breakdown unavailable: %s", exc)
            await db.rollback()

        try:
            state_query = await db.execute(
                text("""
                    SELECT COALESCE(NULLIF(state, ''), 'Unknown') as state, COUNT(*) as count
                    FROM mechanics
                    GROUP BY state
                    ORDER BY count DESC
                    LIMIT 15
                """)
            )
            top_states = [
                {"state": row[0], "count": row[1]}
                for row in state_query.all()
                if row[0] and row[0] != "Unknown"
            ]
        except SQLAlchemyError as exc:
            logger.warning("Dashboard top states unavailable: %s", exc)
            await db.rollback()
            top_states = []

        return {
            "total_mechanics": total,
            "total_with_phone": with_phone,
            "total_with_email": with_email,
            "total_with_website": with_website,
            "total_campaigns": total_campaigns,
            "total_messages_sent": total_sent,
            "total_demos_booked": lead_breakdown.get("demo_scheduled", 0),
            "total_signups": lead_breakdown.get("signed_up", 0),
            "lead_status_breakdown": lead_breakdown,
            "top_states": top_states,
        }
