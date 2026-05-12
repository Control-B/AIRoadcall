"""Major chain truck service vendor locations.

Separate from the local mechanic / Vendor tables. This layer contains
nationally-known providers (Love's Truck Care, TA, Petro, Pilot/Flying J,
Speedco, Rush Truck Centers, FleetPride, Boss Truck Shops, Southern Tire Mart)
so the dispatcher can always offer at least one big-vendor option alongside
local mobile mechanics.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MajorVendorLocation(Base):
    """National chain truck service vendor location."""

    __tablename__ = "vendor_locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    brand_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    location_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    zip_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    interstate: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    exit_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    services: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    heavy_duty: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rv_service: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    towing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tire_service: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mobile_service: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_24_7: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    priority_score: Mapped[int] = mapped_column(Integer, default=80, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
