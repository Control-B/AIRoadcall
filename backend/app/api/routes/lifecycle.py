from datetime import datetime
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.admin_auth import verify_admin
from app.models.lifecycle_event import LifecycleEvent
from app.services.lifecycle_service import LifecycleService

router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])
service = LifecycleService()


class LifecycleEventIn(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=120)
    source: str = Field(default="roadcall", max_length=80)
    organization_id: uuid.UUID | None = None
    entity_type: str | None = Field(default=None, max_length=80)
    entity_id: str | None = Field(default=None, max_length=120)
    idempotency_key: str | None = Field(default=None, max_length=180)
    payload: dict[str, Any] = Field(default_factory=dict)
    trigger_ghl: bool = True
    ghl_event_name: str | None = Field(default=None, max_length=120)


class LifecycleRetryIn(BaseModel):
    ghl_event_name: str | None = Field(default=None, max_length=120)


class LifecycleEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID | None
    event_type: str
    source: str
    entity_type: str | None
    entity_id: str | None
    idempotency_key: str | None
    payload_json: dict[str, Any] | None
    processing_status: str
    ghl_status: str | None
    ghl_result_json: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    processed_at: datetime | None


class LifecycleEventListResponse(BaseModel):
    events: list[LifecycleEventOut]
    count: int


@router.post("/events", response_model=LifecycleEventOut, dependencies=[Depends(verify_admin)])
async def create_lifecycle_event(payload: LifecycleEventIn, db: AsyncSession = Depends(get_session)):
    event = await service.emit_event(
        db,
        event_type=payload.event_type,
        source=payload.source,
        organization_id=payload.organization_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        payload=payload.payload,
        idempotency_key=payload.idempotency_key,
        trigger_ghl=payload.trigger_ghl,
        ghl_event_name=payload.ghl_event_name,
    )
    return event


@router.get("/events", response_model=LifecycleEventListResponse, dependencies=[Depends(verify_admin)])
async def list_lifecycle_events(
    db: AsyncSession = Depends(get_session),
    organization_id: uuid.UUID | None = Query(default=None),
    event_type: str | None = Query(default=None, max_length=120),
    source: str | None = Query(default=None, max_length=80),
    ghl_status: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
):
    stmt = select(LifecycleEvent)
    if organization_id:
        stmt = stmt.where(LifecycleEvent.organization_id == organization_id)
    if event_type:
        stmt = stmt.where(LifecycleEvent.event_type == event_type)
    if source:
        stmt = stmt.where(LifecycleEvent.source == source)
    if ghl_status:
        stmt = stmt.where(LifecycleEvent.ghl_status == ghl_status)
    result = await db.execute(stmt.order_by(desc(LifecycleEvent.created_at)).limit(limit))
    events = list(result.scalars().all())
    return LifecycleEventListResponse(events=events, count=len(events))


@router.post("/events/{event_id}/retry-ghl", response_model=LifecycleEventOut, dependencies=[Depends(verify_admin)])
async def retry_lifecycle_event_ghl(
    event_id: uuid.UUID,
    payload: LifecycleRetryIn | None = None,
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(LifecycleEvent).where(LifecycleEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Lifecycle event not found")
    await service.retry_ghl(db, event, ghl_event_name=payload.ghl_event_name if payload else None)
    return event
