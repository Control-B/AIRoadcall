import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, Enum as SAEnum, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.enums.job_status import JobStatus
from app.enums.payment_status import PaymentStatus
from app.enums.issue_type import IssueType


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    public_job_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    magic_link_token: Mapped[str] = mapped_column(
        Text, unique=True, nullable=False, index=True
    )
    magic_link_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Driver info
    driver_name: Mapped[str] = mapped_column(String(255), nullable=False)
    driver_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(100), nullable=True)

    # Issue
    issue_type: Mapped[str] = mapped_column(
        SAEnum(IssueType, name="issue_type_enum", create_constraint=True),
        nullable=False,
    )
    issue_summary: Mapped[str] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        SAEnum(JobStatus, name="job_status_enum", create_constraint=True),
        nullable=False,
        default=JobStatus.created,
    )

    # Payment
    payment_status: Mapped[str] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status_enum", create_constraint=True),
        nullable=False,
        default=PaymentStatus.not_started,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    payment_hold_amount: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    # Location
    driver_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    driver_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    driver_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    driver_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    driver_location_captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Assignment
    assigned_mechanic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
