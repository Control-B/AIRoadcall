import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Boolean, DateTime, JSON, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Mechanic(Base):
    __tablename__ = "mechanics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)

    # Service capabilities stored as JSON arrays
    service_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    vehicle_types_supported: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )

    # Location
    base_lat: Mapped[float] = mapped_column(Float, nullable=False)
    base_lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Availability
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accepts_mobile_roadside: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # Live tracking location
    last_known_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_known_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_location_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Quality
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Data source & enrichment
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    hours_of_operation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Enrichment tracking
    last_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    enrichment_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Dispatch performance (self-improving loop)
    total_dispatches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_dispatches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_response_time_min: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Lead tracking (outreach system)
    lead_status: Mapped[str | None] = mapped_column(String(50), nullable=True, default="new", index=True)
    # new, contacted, interested, demo_scheduled, demo_completed, negotiating, signed_up, not_interested, do_not_contact
    lead_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    lead_contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
