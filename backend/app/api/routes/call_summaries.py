import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_admin_api_key
from app.models.call_summary import CallSummary
from app.models.job import Job
from app.schemas.call_summary import CallSummaryResponse

router = APIRouter(prefix="/call-summaries", tags=["call-summaries"])


def _as_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return {}


def _coalesce_str(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _coalesce_dt(payload: dict[str, Any], *keys: str) -> datetime | None:
    for key in keys:
        value = payload.get(key)
        if not value:
            continue
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            continue
    return None


@router.post("/livekit", response_model=CallSummaryResponse, dependencies=[Depends(require_admin_api_key)])
async def ingest_livekit_call_summary(
    request: Request,
    body: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_session),
):
    payload = body or {}
    request_json = _as_dict(payload)
    meta = _as_dict(request_json.get("metadata"))
    room = _as_dict(request_json.get("room"))

    public_job_id = _coalesce_str(
        request_json,
        "public_job_id",
    ) or _coalesce_str(meta, "public_job_id", "job_public_id")

    job_id = None
    if public_job_id:
        result = await db.execute(select(Job).where(Job.public_job_id == public_job_id))
        job = result.scalar_one_or_none()
        if job:
            job_id = job.id

    summary_text = _coalesce_str(
        request_json,
        "summary",
        "summary_text",
        "call_summary",
    )
    if not summary_text and isinstance(request_json.get("summary"), dict):
        summary_text = _coalesce_str(_as_dict(request_json.get("summary")), "text", "summary")

    transcript = _coalesce_str(request_json, "transcript")
    if transcript is None and isinstance(request_json.get("transcript"), list):
        transcript = json.dumps(request_json.get("transcript"))

    call_summary = CallSummary(
        provider=_coalesce_str(request_json, "provider") or "livekit",
        source=_coalesce_str(request_json, "source") or "livekit_console",
        agent_name=_coalesce_str(request_json, "agent_name", "agent") or _coalesce_str(meta, "agent_name"),
        call_type=_coalesce_str(request_json, "call_type") or _coalesce_str(meta, "type"),
        livekit_room_name=_coalesce_str(request_json, "room_name") or _coalesce_str(room, "name"),
        provider_call_id=_coalesce_str(request_json, "call_id", "provider_call_id", "session_id"),
        from_number=_coalesce_str(request_json, "from_number", "caller_phone", "from"),
        to_number=_coalesce_str(request_json, "to_number", "to"),
        public_job_id=public_job_id,
        job_id=job_id,
        duration_seconds=request_json.get("duration_seconds") or request_json.get("duration"),
        summary_text=summary_text,
        transcript=transcript,
        payload_json=request_json,
        started_at=_coalesce_dt(request_json, "started_at", "call_started_at"),
        ended_at=_coalesce_dt(request_json, "ended_at", "call_ended_at"),
    )
    db.add(call_summary)
    await db.flush()
    await db.refresh(call_summary)

    return CallSummaryResponse(
        id=str(call_summary.id),
        provider=call_summary.provider,
        source=call_summary.source,
        agent_name=call_summary.agent_name,
        call_type=call_summary.call_type,
        livekit_room_name=call_summary.livekit_room_name,
        provider_call_id=call_summary.provider_call_id,
        public_job_id=call_summary.public_job_id,
        summary_text=call_summary.summary_text,
        duration_seconds=call_summary.duration_seconds,
        created_at=call_summary.created_at,
    )