import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, Query, Request
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, require_admin_api_key
from app.models.call_summary import CallSummary
from app.models.job import Job
from app.schemas.call_summary import CallSummaryResponse

router = APIRouter(prefix="/call-summaries", tags=["call-summaries"])


def _normalize_phone(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


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


@router.post("/call-summary", response_model=CallSummaryResponse, dependencies=[Depends(require_admin_api_key)])
async def ingest_call_summary(
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


@router.get("/memory", dependencies=[Depends(require_admin_api_key)])
async def get_caller_memory(
    phone: str = Query(..., min_length=7),
    limit: int = Query(default=3, ge=1, le=10),
    db: AsyncSession = Depends(get_session),
):
    normalized_phone = _normalize_phone(phone)
    if not normalized_phone:
        return {"phone": phone, "recent_summaries": [], "pronunciation_hints": [], "memory_notes": []}

    result = await db.execute(
        select(CallSummary)
        .where(
            or_(
                CallSummary.from_number.like(f"%{normalized_phone[-10:]}%"),
                CallSummary.to_number.like(f"%{normalized_phone[-10:]}%"),
            )
        )
        .order_by(desc(CallSummary.created_at))
        .limit(25)
    )
    rows = result.scalars().all()

    recent_summaries: list[dict[str, Any]] = []
    pronunciation_hints: list[str] = []
    memory_notes: list[str] = []

    for row in rows:
        payload = row.payload_json or {}
        if row.source == "agent_memory":
            note = str(payload.get("memory_note") or row.summary_text or "").strip()
            if note:
                memory_notes.append(note)
            hints = payload.get("pronunciation_hints") or []
            if isinstance(hints, list):
                for hint in hints:
                    text = str(hint).strip()
                    if text:
                        pronunciation_hints.append(text)
            elif isinstance(hints, str) and hints.strip():
                pronunciation_hints.append(hints.strip())
            continue

        summary_text = str(row.summary_text or "").strip()
        if summary_text:
            recent_summaries.append(
                {
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "call_type": row.call_type,
                    "summary_text": summary_text,
                }
            )

    dedup_pronunciations = list(dict.fromkeys(pronunciation_hints))[:10]
    dedup_notes = list(dict.fromkeys(memory_notes))[:10]

    return {
        "phone": phone,
        "recent_summaries": recent_summaries[:limit],
        "pronunciation_hints": dedup_pronunciations,
        "memory_notes": dedup_notes,
    }


@router.post("/memory", dependencies=[Depends(require_admin_api_key)])
async def save_caller_memory(
    body: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_session),
):
    phone = str(body.get("phone") or body.get("from_number") or "").strip()
    if not phone:
        return {"saved": False, "reason": "missing phone"}

    memory_note = str(body.get("memory_note") or "").strip()
    pronunciation_hints = body.get("pronunciation_hints") or []
    if isinstance(pronunciation_hints, str):
        pronunciation_hints = [pronunciation_hints]
    pronunciation_hints = [str(item).strip() for item in pronunciation_hints if str(item).strip()]

    if not memory_note and not pronunciation_hints:
        return {"saved": False, "reason": "no memory content"}

    record = CallSummary(
        provider="roadcall",
        source="agent_memory",
        agent_name=str(body.get("agent_name") or "roadcall-agent"),
        call_type="memory_note",
        from_number=phone,
        to_number=str(body.get("to_number") or "").strip() or None,
        summary_text=memory_note or "; ".join(pronunciation_hints),
        payload_json={
            "memory_note": memory_note or None,
            "pronunciation_hints": pronunciation_hints,
            "category": str(body.get("category") or "caller_memory"),
        },
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return {"saved": True, "id": str(record.id)}