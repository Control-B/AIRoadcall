import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.enums.dispatch_status import DispatchStatus


class DispatchAttempt(Base):
    __tablename__ = "dispatch_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    mechanic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mechanics.id"), nullable=False, index=True
    )

    rank_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    dispatch_status: Mapped[str] = mapped_column(
        SAEnum(DispatchStatus, name="dispatch_status_enum", create_constraint=True),
        nullable=False,
        default=DispatchStatus.queued,
    )

    called_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    availability_eta_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    response_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
