from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ActiveCallSession(Base):
    __tablename__ = "active_call_sessions"
    __table_args__ = (
        UniqueConstraint("provider_call_id", name="uq_active_call_sessions_provider_call_id"),
        UniqueConstraint("location_code", name="uq_active_call_sessions_location_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_provider: Mapped[str] = mapped_column(String(40), default="retell", nullable=False, index=True)
    provider_call_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    caller_phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    location_code: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="waiting_for_location", nullable=False, index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    highway_or_exit: Mapped[str | None] = mapped_column(Text, nullable=True)
    manual_location_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
