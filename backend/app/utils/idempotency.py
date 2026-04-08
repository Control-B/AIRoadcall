from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_event import AuditEvent


async def check_idempotency(
    db: AsyncSession, job_id: str, event_type: str, idempotency_key: str
) -> bool:
    """Return True if this event has already been processed (duplicate)."""
    result = await db.execute(
        select(AuditEvent).where(
            AuditEvent.job_id == job_id,
            AuditEvent.event_type == event_type,
            AuditEvent.actor_id == idempotency_key,
        )
    )
    return result.scalar_one_or_none() is not None
