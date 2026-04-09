"""Outreach Campaign models — track email/SMS campaigns to mechanic shops."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, JSON, Integer, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Campaign Details ───────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sms"
    )  # sms, email, voice
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="draft"
    )  # draft, scheduled, sending, completed, paused

    # ── Content ────────────────────────────────────────────
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)  # for email
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    # Template vars: {business_name}, {phone}, {demo_number}, {demo_url}, {address}

    # ── Targeting ──────────────────────────────────────────
    segment_filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # e.g. {"states": ["TX", "FL"], "roadside": true, "min_rating": 4.0}
    total_targeted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Delivery Stats ─────────────────────────────────────
    total_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_delivered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_opened: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_clicked: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_replied: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_demo_calls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_signups: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Scheduling ─────────────────────────────────────────
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Timestamps ─────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # ── Relationships ──────────────────────────────────────
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("outreach_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mechanic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("mechanics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Delivery ───────────────────────────────────────────
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # sms, email
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)  # phone or email
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending"
    )  # pending, sent, delivered, opened, clicked, replied, bounced, failed
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Engagement ─────────────────────────────────────────
    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    clicked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    demo_called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signed_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Timestamps ─────────────────────────────────────────
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
