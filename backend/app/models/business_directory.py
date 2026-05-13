import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TruckingCompany(Base):
    __tablename__ = "trucking_companies"
    __table_args__ = (
        UniqueConstraint("phone", name="uq_trucking_companies_phone"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    dot_number: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    mc_number: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class NationalVendor(Base):
    __tablename__ = "national_vendors"
    __table_args__ = (
        UniqueConstraint("brand_name", "phone", "address", name="uq_national_vendors_brand_phone_address"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    location_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    services: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_national_chain: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
