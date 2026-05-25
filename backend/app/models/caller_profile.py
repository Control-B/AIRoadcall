"""Persistent caller profile keyed by phone number.

Stores the vehicle / fleet details a driver gives Sandy on their first call so
subsequent calls can confirm "anything changed?" instead of re-collecting from
scratch.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CallerProfile(Base):
    __tablename__ = "caller_profiles"

    phone: Mapped[str] = mapped_column(String(20), primary_key=True)
    driver_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    truck_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    trailer_number: Mapped[str | None] = mapped_column(String(60), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_call_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
