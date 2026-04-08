import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_event import AuditEvent
from typing import Any


class AuditService:

    @staticmethod
    async def log(
        db: AsyncSession,
        job_id: uuid.UUID,
        event_type: str,
        actor_type: str,
        actor_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Record an audit event for a job."""
        event = AuditEvent(
            job_id=job_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            payload_json=payload,
        )
        db.add(event)
        await db.flush()
