"""Public marketplace endpoints — submit listing, rate provider, claim ownership.

Design rules:
- Any user can submit a new business or rate any listing (rate-limited by IP/phone).
- Only the rightful mechanic can edit their listing. Ownership is established via:
  1) Phone match — claim phone matches mechanic.phone (instant approval), OR
  2) Subscriber match — claim phone matches an active Roadcall Organization
     contact_phone (subscriber to AI Telephony / Voice+Text / Social / Website),
  3) Otherwise the claim is queued for admin review (no edits allowed yet).
- This protects against competitive/malicious edits as the user requested.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.logging import get_logger
from app.models.mechanic import Mechanic
from app.models.mechanic_marketplace import (
    ClaimMethod, ClaimStatus, MechanicClaim, MechanicReview,
)
from app.models.organization import Organization

router = APIRouter(prefix="/marketplace", tags=["marketplace"])
logger = get_logger(__name__)


SUBSCRIPTION_PRODUCTS = {"ai_telephony", "ai_voice_text", "social_media", "website_management"}


# ── helpers ──────────────────────────────────────────────────────────
_PHONE_DIGITS = re.compile(r"\D+")


def _normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = _PHONE_DIGITS.sub("", value)
    return digits[-10:] if len(digits) >= 10 else digits or None


async def _is_subscriber_phone(db: AsyncSession, phone: str) -> Organization | None:
    """Return the active Organization whose contact_phone matches the claim phone."""
    if not phone:
        return None
    stmt = select(Organization).where(Organization.is_active == True)  # noqa: E712
    rows = (await db.execute(stmt)).scalars().all()
    target = _normalize_phone(phone)
    for org in rows:
        if _normalize_phone(org.contact_phone) == target:
            return org
    return None


# ── schemas ──────────────────────────────────────────────────────────
class MarketplaceProvider(BaseModel):
    id: str
    company_name: str
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    service_types: list[str] = Field(default_factory=list)
    vehicle_types_supported: list[str] = Field(default_factory=list)
    accepts_mobile_roadside: bool = True
    emergency_service: bool = False
    service_radius_miles: int = 50
    rating: float | None = None
    review_count: int | None = None
    claimed: bool = False
    verified_listing: bool = False
    subscription_product: str | None = None


class ProviderDetailResponse(MarketplaceProvider):
    recent_reviews: list["ReviewView"]


class ReviewView(BaseModel):
    id: str
    rating: int
    comment: str | None = None
    reviewer_name: str | None = None
    verified: bool = False
    created_at: datetime


class SubmitListingRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    contact_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=7, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, min_length=2, max_length=2)
    base_lat: float | None = Field(default=None, ge=-90, le=90)
    base_lng: float | None = Field(default=None, ge=-180, le=180)
    service_types: list[str] = Field(default_factory=list)
    vehicle_types_supported: list[str] = Field(default_factory=list)
    accepts_mobile_roadside: bool = True
    emergency_service: bool = False
    service_radius_miles: int = Field(default=50, ge=1, le=500)
    notes: str | None = None


class SubmitListingResponse(BaseModel):
    id: str
    status: str  # "duplicate" | "created"
    message: str
    next_step: str  # "claim_to_edit"
    requires_admin_review: bool


class ReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)
    reviewer_name: str | None = Field(default=None, max_length=120)
    reviewer_phone: str | None = Field(default=None, max_length=30)


class ReviewResponse(BaseModel):
    id: str
    mechanic_id: str
    rating: int
    new_average: float
    new_review_count: int


class ClaimRequest(BaseModel):
    claimant_name: str = Field(..., min_length=2, max_length=255)
    claimant_phone: str = Field(..., min_length=7, max_length=30)
    claimant_email: str | None = Field(default=None, max_length=255)
    subscription_product: str | None = Field(
        default=None,
        description="ai_telephony | ai_voice_text | social_media | website_management",
    )
    notes: str | None = None


class ClaimResponse(BaseModel):
    id: str
    mechanic_id: str
    status: str            # pending | approved | rejected
    method: str            # phone_match | subscriber_match | manual_admin | pending_review
    message: str
    can_edit_now: bool


class EditListingRequest(BaseModel):
    """Self-edit fields. claimant_phone is the auth — must match claimed_by_phone."""
    claimant_phone: str = Field(..., min_length=7, max_length=30)

    company_name: str | None = Field(default=None, min_length=2, max_length=255)
    contact_name: str | None = None
    email: str | None = Field(default=None, max_length=255)
    website: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = Field(default=None, min_length=2, max_length=2)
    service_types: list[str] | None = None
    vehicle_types_supported: list[str] | None = None
    accepts_mobile_roadside: bool | None = None
    emergency_service: bool | None = None
    service_radius_miles: int | None = Field(default=None, ge=1, le=500)


# ── routes ───────────────────────────────────────────────────────────
@router.get("/{mechanic_id}", response_model=ProviderDetailResponse)
async def get_provider_detail(mechanic_id: str, db: AsyncSession = Depends(get_session)):
    mechanic = await db.get(Mechanic, mechanic_id)
    if not mechanic or not mechanic.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Provider not found")

    review_rows = (await db.execute(
        select(MechanicReview)
        .where(MechanicReview.mechanic_id == mechanic.id, MechanicReview.flagged == False)  # noqa: E712
        .order_by(MechanicReview.created_at.desc())
        .limit(10)
    )).scalars().all()

    return ProviderDetailResponse(
        id=str(mechanic.id),
        company_name=mechanic.company_name,
        contact_name=mechanic.contact_name,
        phone=mechanic.phone if mechanic.claimed else None,  # mask phone for unclaimed listings
        email=mechanic.email if mechanic.claimed else None,
        website=mechanic.website,
        address=mechanic.address,
        city=mechanic.city,
        state=mechanic.state,
        service_types=list(mechanic.service_types or []),
        vehicle_types_supported=list(mechanic.vehicle_types_supported or []),
        accepts_mobile_roadside=mechanic.accepts_mobile_roadside,
        emergency_service=mechanic.emergency_service,
        service_radius_miles=mechanic.service_radius_miles,
        rating=float(mechanic.rating) if mechanic.rating is not None else None,
        review_count=mechanic.review_count or 0,
        claimed=mechanic.claimed,
        verified_listing=mechanic.verified_listing,
        subscription_product=mechanic.subscription_product,
        recent_reviews=[
            ReviewView(
                id=str(r.id), rating=r.rating, comment=r.comment,
                reviewer_name=r.reviewer_name, verified=r.verified,
                created_at=r.created_at,
            ) for r in review_rows
        ],
    )


@router.post("/submit", response_model=SubmitListingResponse, status_code=status.HTTP_201_CREATED)
async def submit_listing(
    payload: SubmitListingRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Anyone can submit a business. Created as unverified + flagged for admin review."""
    norm_phone = _normalize_phone(payload.phone)
    if not norm_phone:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid phone")

    # Dedup by phone
    existing = (await db.execute(
        select(Mechanic).where(
            or_(Mechanic.phone == payload.phone, Mechanic.phone == norm_phone)
        ).limit(1)
    )).scalar_one_or_none()
    if existing:
        return SubmitListingResponse(
            id=str(existing.id),
            status="duplicate",
            message="A listing with this phone already exists. You can claim it to edit.",
            next_step="claim_to_edit",
            requires_admin_review=existing.requires_admin_review,
        )

    mech = Mechanic(
        company_name=payload.company_name.strip(),
        contact_name=payload.contact_name.strip(),
        phone=payload.phone.strip(),
        email=payload.email,
        website=payload.website,
        address=payload.address,
        city=(payload.city or "").strip() or None,
        state=(payload.state or "").upper() or None,
        base_lat=payload.base_lat or 0.0,
        base_lng=payload.base_lng or 0.0,
        service_types=payload.service_types or [],
        vehicle_types_supported=payload.vehicle_types_supported or [],
        accepts_mobile_roadside=payload.accepts_mobile_roadside,
        emergency_service=payload.emergency_service,
        service_radius_miles=payload.service_radius_miles,
        priority_score=40,
        active=False,  # not visible until admin reviews
        source="public_submission",
        submitted_by_public=True,
        requires_admin_review=True,
        verified_listing=False,
    )
    db.add(mech)
    await db.commit()
    await db.refresh(mech)
    logger.info("marketplace_submit_listing id=%s phone=%s ip=%s", mech.id, norm_phone, request.client.host if request.client else None)
    return SubmitListingResponse(
        id=str(mech.id),
        status="created",
        message="Submitted for review. We'll verify and publish your listing shortly.",
        next_step="claim_to_edit",
        requires_admin_review=True,
    )


@router.post("/{mechanic_id}/review", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def submit_review(
    mechanic_id: str,
    payload: ReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    mechanic = await db.get(Mechanic, mechanic_id)
    if not mechanic or not mechanic.active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Provider not found")

    ip = request.client.host if request.client else None
    norm_phone = _normalize_phone(payload.reviewer_phone)

    # Rate limit: same IP or same phone — max 1 review per mechanic per 24h.
    cutoff = datetime.now(timezone.utc).replace(microsecond=0)
    recent_q = select(MechanicReview).where(MechanicReview.mechanic_id == mechanic.id)
    if norm_phone:
        recent_q = recent_q.where(MechanicReview.reviewer_phone == norm_phone)
    elif ip:
        recent_q = recent_q.where(MechanicReview.reviewer_ip == ip)
    existing_recent = (await db.execute(recent_q.order_by(MechanicReview.created_at.desc()).limit(1))).scalar_one_or_none()
    if existing_recent and (cutoff - existing_recent.created_at).total_seconds() < 86400:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You already reviewed this provider in the last 24 hours.",
        )

    review = MechanicReview(
        mechanic_id=mechanic.id,
        rating=payload.rating,
        comment=(payload.comment or "").strip() or None,
        reviewer_name=(payload.reviewer_name or "").strip() or None,
        reviewer_phone=norm_phone,
        reviewer_ip=ip,
        verified=False,
    )
    db.add(review)
    await db.flush()

    # Recompute aggregate rating + count from non-flagged reviews.
    agg = (await db.execute(
        select(func.avg(MechanicReview.rating), func.count(MechanicReview.id))
        .where(MechanicReview.mechanic_id == mechanic.id, MechanicReview.flagged == False)  # noqa: E712
    )).one()
    new_avg = float(agg[0] or 0.0)
    new_count = int(agg[1] or 0)
    mechanic.rating = round(new_avg, 2)
    mechanic.review_count = new_count
    await db.commit()
    await db.refresh(review)
    logger.info("marketplace_review mechanic_id=%s rating=%s avg=%.2f count=%d", mechanic.id, payload.rating, new_avg, new_count)
    return ReviewResponse(
        id=str(review.id),
        mechanic_id=str(mechanic.id),
        rating=review.rating,
        new_average=round(new_avg, 2),
        new_review_count=new_count,
    )


@router.post("/{mechanic_id}/claim", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
async def claim_listing(
    mechanic_id: str,
    payload: ClaimRequest,
    db: AsyncSession = Depends(get_session),
):
    """Claim ownership of a listing.

    Auto-approved when the claim phone matches the mechanic's phone OR matches
    an active Roadcall subscriber organization. Otherwise queued for admin review.
    """
    mechanic = await db.get(Mechanic, mechanic_id)
    if not mechanic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Provider not found")

    norm_claim = _normalize_phone(payload.claimant_phone)
    if not norm_claim:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid phone")

    if mechanic.claimed and _normalize_phone(mechanic.claimed_by_phone) != norm_claim:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="This listing is already claimed.")

    if payload.subscription_product and payload.subscription_product not in SUBSCRIPTION_PRODUCTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid subscription product")

    # Determine method.
    method = ClaimMethod.pending_review
    org = None
    if _normalize_phone(mechanic.phone) == norm_claim:
        method = ClaimMethod.phone_match
    else:
        org = await _is_subscriber_phone(db, payload.claimant_phone)
        if org is not None:
            method = ClaimMethod.subscriber_match

    auto_approved = method in {ClaimMethod.phone_match, ClaimMethod.subscriber_match}

    claim = MechanicClaim(
        mechanic_id=mechanic.id,
        organization_id=(org.id if org else None),
        claimant_name=payload.claimant_name.strip(),
        claimant_phone=norm_claim,
        claimant_email=payload.claimant_email,
        subscription_product=payload.subscription_product,
        method=method,
        status=ClaimStatus.approved if auto_approved else ClaimStatus.pending,
        notes=payload.notes,
        verification_token=secrets.token_urlsafe(24) if not auto_approved else None,
        approved_at=datetime.now(timezone.utc) if auto_approved else None,
    )
    db.add(claim)

    if auto_approved:
        mechanic.claimed = True
        mechanic.claimed_at = datetime.now(timezone.utc)
        mechanic.claimed_by_phone = norm_claim
        mechanic.claimed_by_organization_id = org.id if org else None
        mechanic.subscription_product = payload.subscription_product
        mechanic.verified_listing = True

    await db.commit()
    await db.refresh(claim)
    logger.info(
        "marketplace_claim mechanic_id=%s method=%s status=%s",
        mechanic.id, method.value, claim.status.value if hasattr(claim.status, "value") else claim.status,
    )

    msg = {
        ClaimMethod.phone_match: "Verified by phone match — you can edit this listing now.",
        ClaimMethod.subscriber_match: "Verified by Roadcall subscription — you can edit this listing now.",
        ClaimMethod.pending_review: "Claim received. Our team will verify ownership within one business day.",
        ClaimMethod.manual_admin: "Approved by admin.",
    }[method]
    return ClaimResponse(
        id=str(claim.id),
        mechanic_id=str(mechanic.id),
        status=str(claim.status.value if hasattr(claim.status, "value") else claim.status),
        method=str(method.value if hasattr(method, "value") else method),
        message=msg,
        can_edit_now=auto_approved,
    )


@router.patch("/{mechanic_id}", response_model=MarketplaceProvider)
async def edit_listing(
    mechanic_id: str,
    payload: EditListingRequest,
    db: AsyncSession = Depends(get_session),
):
    """Self-edit a claimed listing. Auth = phone matches claimed_by_phone."""
    mechanic = await db.get(Mechanic, mechanic_id)
    if not mechanic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Provider not found")
    if not mechanic.claimed:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="This listing isn't claimed yet. Submit a claim first.",
        )
    if _normalize_phone(payload.claimant_phone) != _normalize_phone(mechanic.claimed_by_phone):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Phone does not match the verified owner of this listing.",
        )

    data = payload.model_dump(exclude_none=True, exclude={"claimant_phone"})
    for field, value in data.items():
        if field == "state" and isinstance(value, str):
            value = value.upper()
        setattr(mechanic, field, value)
    await db.commit()
    await db.refresh(mechanic)

    return MarketplaceProvider(
        id=str(mechanic.id),
        company_name=mechanic.company_name,
        contact_name=mechanic.contact_name,
        phone=mechanic.phone,
        email=mechanic.email,
        website=mechanic.website,
        address=mechanic.address,
        city=mechanic.city,
        state=mechanic.state,
        service_types=list(mechanic.service_types or []),
        vehicle_types_supported=list(mechanic.vehicle_types_supported or []),
        accepts_mobile_roadside=mechanic.accepts_mobile_roadside,
        emergency_service=mechanic.emergency_service,
        service_radius_miles=mechanic.service_radius_miles,
        rating=float(mechanic.rating) if mechanic.rating is not None else None,
        review_count=mechanic.review_count or 0,
        claimed=mechanic.claimed,
        verified_listing=mechanic.verified_listing,
        subscription_product=mechanic.subscription_product,
    )
