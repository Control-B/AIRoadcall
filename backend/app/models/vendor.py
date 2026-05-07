import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Vendor(Base):
    """Roadside service vendor (mechanic shop, mobile mechanic, towing, etc.)"""
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Location
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Capabilities
    service_types: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list: ["towing","tire","diesel"]
    heavy_duty_capable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    service_radius_miles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    operates_24_7: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Rating / reliability
    average_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_jobs_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
