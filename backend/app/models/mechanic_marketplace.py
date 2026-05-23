"""Public reviews and ownership claims for mechanic listings.

`MechanicReview` — open ratings (1–5) with optional comment + caller phone for
rate-limiting. Aggregated into `Mechanic.rating` / `Mechanic.review_count`.

`MechanicClaim` — when a mechanic wants to manage their own listing. Auto-
approved when the claim phone matches the mechanic.phone or matches a known
Roadcall subscriber organization. Otherwise queued for admin review.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, JSON, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClaimStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ClaimMethod(str, enum.Enum):
    phone_match = "phone_match"           # claim phone matches mechanic.phone
    subscriber_match = "subscriber_match"  # phone matches an active Organization
    manual_admin = "manual_admin"         # admin override
    pending_review = "pending_review"      # awaiting admin review


class ProviderUpdateStatus(str, enum.Enum):
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    more_info_requested = "more_info_requested"


class EnrichmentSuggestionStatus(str, enum.Enum):
    suggested = "suggested"
    approved = "approved"
    rejected = "rejected"


class MechanicReview(Base):
    __tablename__ = "mechanic_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mechanic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mechanics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewer_phone: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    reviewer_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class MechanicClaim(Base):
    __tablename__ = "mechanic_claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mechanic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mechanics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    claimant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    claimant_phone: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    claimant_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_product: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # ai_telephony | ai_voice_text | social_media | website_management

    method: Mapped[str] = mapped_column(
        SAEnum(ClaimMethod, name="mechanic_claim_method"),
        nullable=False, default=ClaimMethod.pending_review,
    )
    status: Mapped[str] = mapped_column(
        SAEnum(ClaimStatus, name="mechanic_claim_status"),
        nullable=False, default=ClaimStatus.pending, index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ProviderUpdateRequest(Base):
    __tablename__ = "provider_update_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mechanic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mechanics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    requester_role: Mapped[str] = mapped_column(String(40), nullable=False)
    requester_name: Mapped[str] = mapped_column(String(255), nullable=False)
    requester_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    requester_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    proof_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_company_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_website: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_changes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    email_domain_matches_website: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(ProviderUpdateStatus, name="provider_update_status"),
        nullable=False,
        default=ProviderUpdateStatus.pending_review,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ProviderEnrichmentSuggestion(Base):
    __tablename__ = "provider_enrichment_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mechanic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mechanics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    suggested_values: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(EnrichmentSuggestionStatus, name="provider_enrichment_suggestion_status"),
        nullable=False,
        default=EnrichmentSuggestionStatus.suggested,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class ProviderChangeLog(Base):
    __tablename__ = "provider_change_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mechanic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mechanics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    field_name: Mapped[str] = mapped_column(String(120), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_request_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="approved", index=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
