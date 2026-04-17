from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CallSummaryIn(BaseModel):
    provider: str = "livekit"
    source: str | None = None
    agent_name: str | None = None
    call_type: str | None = None
    livekit_room_name: str | None = None
    provider_call_id: str | None = None
    from_number: str | None = None
    to_number: str | None = None
    public_job_id: str | None = None
    duration_seconds: int | None = None
    summary_text: str | None = None
    transcript: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    payload_json: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class CallSummaryResponse(BaseModel):
    id: str
    provider: str
    source: str | None = None
    agent_name: str | None = None
    call_type: str | None = None
    livekit_room_name: str | None = None
    provider_call_id: str | None = None
    public_job_id: str | None = None
    summary_text: str | None = None
    duration_seconds: int | None = None
    created_at: datetime
