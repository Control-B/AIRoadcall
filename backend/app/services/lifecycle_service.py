import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lifecycle_event import LifecycleEvent
from app.services.ghl_service import GHLService


class LifecycleService:
    GHL_EVENT_MAP = {
        "new_lead": "new_lead",
        "missed_call": "missed_call",
        "qualified_roadside_request": "qualified_roadside_request",
        "successful_transfer": "successful_transfer",
        "completed_job": "completed_job",
        "review_request": "review_request",
        "demo_booked": "demo_booked",
        "subscription_started": "subscription_event",
        "subscription_updated": "subscription_event",
        "subscription_cancelled": "subscription_event",
        "checkout_completed": "subscription_event",
        "invoice_paid": "subscription_event",
        "payment_failed": "subscription_event",
    }

    def __init__(self) -> None:
        self.ghl = GHLService()

    def _normalize_uuid(self, value: str | uuid.UUID | None) -> uuid.UUID | None:
        if not value:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (TypeError, ValueError):
            return None

    def _ghl_event_for(self, event_type: str, override: str | None = None) -> str | None:
        if override:
            return override
        return self.GHL_EVENT_MAP.get(event_type)

    async def emit_event(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        source: str = "roadcall",
        organization_id: str | uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        trigger_ghl: bool = True,
        ghl_event_name: str | None = None,
    ) -> LifecycleEvent:
        if idempotency_key:
            existing = await db.execute(select(LifecycleEvent).where(LifecycleEvent.idempotency_key == idempotency_key))
            event = existing.scalar_one_or_none()
            if event:
                return event

        event = LifecycleEvent(
            organization_id=self._normalize_uuid(organization_id),
            event_type=event_type,
            source=source,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            idempotency_key=idempotency_key,
            payload_json=payload or {},
            processing_status="recorded",
            ghl_status="pending" if trigger_ghl else "not_applicable",
        )
        db.add(event)
        await db.flush()

        if not trigger_ghl:
            event.processing_status = "processed"
            event.processed_at = datetime.now(timezone.utc)
            await db.flush()
            return event

        await self._trigger_ghl(db, event, ghl_event_name=ghl_event_name)
        return event

    async def retry_ghl(self, db: AsyncSession, event: LifecycleEvent, ghl_event_name: str | None = None) -> LifecycleEvent:
        event.ghl_status = "pending"
        event.error_message = None
        await self._trigger_ghl(db, event, ghl_event_name=ghl_event_name)
        return event

    async def _trigger_ghl(self, db: AsyncSession, event: LifecycleEvent, ghl_event_name: str | None = None) -> None:
        mapped_event = self._ghl_event_for(event.event_type, ghl_event_name)
        if not mapped_event:
            event.ghl_status = "skipped_no_workflow"
            event.processing_status = "processed"
            event.processed_at = datetime.now(timezone.utc)
            await db.flush()
            return

        if not event.organization_id:
            event.ghl_status = "skipped_no_organization"
            event.processing_status = "processed"
            event.processed_at = datetime.now(timezone.utc)
            await db.flush()
            return

        mapping = await self.ghl.get_mapping_by_org(db, event.organization_id)
        if not mapping:
            event.ghl_status = "skipped_no_mapping"
            event.processing_status = "processed"
            event.processed_at = datetime.now(timezone.utc)
            await db.flush()
            return

        payload = dict(event.payload_json or {})
        payload.update(
            {
                "lifecycle_event_id": str(event.id),
                "event_type": event.event_type,
                "source": event.source,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
            }
        )
        try:
            result = await self.ghl.trigger_workflow(db, mapping, mapped_event, payload)
            event.ghl_result_json = result
            event.ghl_status = "queued" if result.get("queued") else "sent"
            event.processing_status = "processed"
            event.error_message = result.get("error")
        except Exception as exc:
            event.ghl_status = "failed"
            event.processing_status = "processed"
            event.error_message = str(exc)
        finally:
            event.processed_at = datetime.now(timezone.utc)
            await db.flush()
