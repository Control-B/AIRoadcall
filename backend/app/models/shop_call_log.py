"""Call log model — tracks every call handled by shop AI agents.

Stores call metadata, transcripts, lead qualification results,
and any actions taken during the call.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, Boolean, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ShopCallLog(Base):
    __tablename__ = "shop_call_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Relationships ──────────────────────────────────────
    shop_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shop_customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Call Metadata ──────────────────────────────────────
    caller_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    caller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direction: Mapped[str] = mapped_column(
        String(20), default="inbound", nullable=False
    )  # inbound, outbound
    channel: Mapped[str] = mapped_column(
        String(20), default="voice", nullable=False
    )  # voice, text

    # ── Call Details ───────────────────────────────────────
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    livekit_room_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── AI Agent Results ───────────────────────────────────
    # What the caller needed
    intent: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # repair_request, price_inquiry, scheduling, general_question, emergency
    intent_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Lead qualification
    is_qualified_lead: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lead_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0-1.0

    # Vehicle info (if collected)
    vehicle_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Actions Taken ──────────────────────────────────────
    appointment_scheduled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    forwarded_to_human: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    callback_requested: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # ── Transcript ─────────────────────────────────────────
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Collected Contact Info ─────────────────────────────
    collected_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ── Status ─────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(50), default="completed", nullable=False
    )  # in_progress, completed, failed, forwarded

    # ── Timestamps ─────────────────────────────────────────
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
