import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CallSummary(Base):
    __tablename__ = "call_summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="livekit")
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    call_type: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    livekit_room_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    provider_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    from_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    public_job_id: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=True, index=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
