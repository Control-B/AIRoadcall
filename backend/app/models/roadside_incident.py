import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Float, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class IncidentStatus(str, enum.Enum):
    open = "open"
    dispatched = "dispatched"
    en_route = "en_route"
    on_site = "on_site"
    resolved = "resolved"
    cancelled = "cancelled"


class RoadsideIncident(Base):
    __tablename__ = "roadside_incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    public_incident_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True
    )

    # Caller info (may not be registered driver)
    caller_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caller_phone: Mapped[str] = mapped_column(String(30), nullable=False)

    # Breakdown details
    issue_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Location
    breakdown_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    breakdown_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    breakdown_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    breakdown_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    breakdown_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Dispatch
    assigned_vendor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        SAEnum(IncidentStatus, name="incident_status_enum", create_constraint=True),
        nullable=False,
        default=IncidentStatus.open,
    )

    # AI call references
    retell_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    call_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
