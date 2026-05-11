"""LeadCapture — website email lead magnet sign-ups."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LeadCapture(Base):
    __tablename__ = "lead_captures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vertical: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # "shops" | "fleet" | "general"
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # page slug or utm
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    unsubscribed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    welcome_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
