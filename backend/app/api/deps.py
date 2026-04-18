from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import decode_magic_link_token, decode_mechanic_tracking_token
from app.models.job import Job


async def get_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    """Dependency to provide a database session."""
    return db


async def require_admin_api_key(x_admin_key: str | None = Header(default=None)) -> None:
    """Protect internal automation endpoints with the shared admin API key."""
    settings = get_settings()
    expected = settings.ADMIN_API_KEY.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin API key is not configured",
        )
    if not x_admin_key or x_admin_key.strip() != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin API key",
        )


async def validate_magic_token(
    token: str, db: AsyncSession = Depends(get_db)
) -> Job:
    """Validate a magic-link token and return the associated Job.

    Raises 401 if the token is invalid, expired, or revoked.
    """
    claims = decode_magic_link_token(token)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired magic link",
        )

    result = await db.execute(
        select(Job).where(Job.magic_link_token == token)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic link not found",
        )

    if job.magic_link_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic link has expired",
        )

    return job


async def validate_mechanic_tracking_token(
    token: str, db: AsyncSession = Depends(get_db)
) -> Job:
    """Validate a mechanic-safe tracking token and return the associated Job."""
    claims = decode_mechanic_tracking_token(token)
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired mechanic tracking link",
        )

    job_id = claims.get("job_id")
    mechanic_id = claims.get("mechanic_id")
    if not job_id or not mechanic_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mechanic tracking link",
        )

    try:
        job_uuid = uuid.UUID(str(job_id))
        mechanic_uuid = uuid.UUID(str(mechanic_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mechanic tracking link",
        ) from exc

    result = await db.execute(select(Job).where(Job.id == job_uuid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.public_job_id != claims.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mechanic tracking link is no longer valid",
        )

    if job.assigned_mechanic_id != mechanic_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mechanic tracking link is no longer valid",
        )

    return job
