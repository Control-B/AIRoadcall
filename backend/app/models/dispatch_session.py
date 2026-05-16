import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DispatchSessionStatus(str, enum.Enum):
    created = "created"
    intake = "intake"
    awaiting_location = "awaiting_location"
    matching = "matching"
    matched = "matched"
    payment_required = "payment_required"
    payment_authorized = "payment_authorized"
    assigned = "assigned"
    en_route = "en_route"
    on_site = "on_site"
    completed = "completed"
    cancelled = "cancelled"
    manual_review = "manual_review"


class DispatchSession(Base):
    __tablename__ = "dispatch_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default=DispatchSessionStatus.created.value, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="api", index=True)

    caller_phone_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    caller_phone_encrypted: Mapped[str | None] = mapped_column(String(64), nullable=True)
    caller_phone_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    caller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    retell_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    twilio_call_sid: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    active_location_token_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    problem_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    vehicle_description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    location_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    selected_mechanic_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    payment_status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_required", index=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), index=True)


Index("ix_dispatch_sessions_status_updated", DispatchSession.status, DispatchSession.updated_at)
Index("ix_dispatch_sessions_phone_created", DispatchSession.caller_phone_hash, DispatchSession.created_at)


class DispatchLocationToken(Base):
    __tablename__ = "dispatch_location_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("dispatch_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class DispatchLocationEvent(Base):
    __tablename__ = "dispatch_location_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("dispatch_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="browser_gps")
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class DispatchMatchResult(Base):
    __tablename__ = "dispatch_match_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("dispatch_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    request_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    search_level: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    candidates: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    selected_mechanic_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class DispatchSessionEvent(Base):
    __tablename__ = "dispatch_session_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("dispatch_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(40), nullable=False, default="system")
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)