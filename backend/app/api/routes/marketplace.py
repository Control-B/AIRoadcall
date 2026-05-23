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
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.admin_auth import verify_admin
from app.core.logging import get_logger
from app.models.mechanic import Mechanic
from app.models.mechanic_marketplace import (
    ClaimMethod,
    ClaimStatus,
    MechanicClaim,
    MechanicReview,
    ProviderChangeLog,
    ProviderUpdateRequest,
    ProviderUpdateStatus,
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


def _mechanic_uuid(mechanic_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(mechanic_id))
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Provider not found") from exc


def _normalize_domain(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.netloc or parsed.path).split("/")[0].split(":")[0].lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _safe_url(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed.geturl()


def _name_match_score(left: str | None, right: str | None) -> float:
    def clean(value: str | None) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()
    a = clean(left)
    b = clean(right)
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, a, b).ratio(), 4)


def _email_domain_matches_website(email: str | None, website: str | None) -> bool | None:
    if not email or "@" not in email:
        return None
    website_domain = _normalize_domain(website)
    if not website_domain:
        return None
    email_domain = email.rsplit("@", 1)[-1].lower().strip()
    return email_domain == website_domain or email_domain.endswith(f".{website_domain}")


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
    contact_name: str = Field(..., min_length=1, max_length=255)
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


class ProviderUpdateRequestIn(BaseModel):
    role: str = Field(..., min_length=2, max_length=40)
    full_name: str = Field(..., min_length=2, max_length=255)
    work_email: str = Field(..., min_length=5, max_length=255)
    phone_number: str = Field(..., min_length=7, max_length=30)
    company_name: str = Field(..., min_length=2, max_length=255)
    company_address: str | None = Field(default=None, max_length=1000)
    website: str | None = Field(default=None, max_length=500)
    proof_message: str | None = Field(default=None, max_length=4000)
    requested_changes: dict = Field(default_factory=dict)


class ProviderUpdateRequestOut(BaseModel):
    id: str
    mechanic_id: str
    status: str
    match_score: float | None
    email_domain_matches_website: bool | None
    message: str


class AdminReviewQueues(BaseModel):
    pending_claims: list[dict]
    pending_updates: list[dict]
    data_quality: dict


class AdminDecisionRequest(BaseModel):
    status: str = Field(..., description="approved | rejected | more_info_requested")
    review_notes: str | None = None


class VerifyProviderRequest(BaseModel):
    verification_status: str = Field(default="verified")


# ── routes ───────────────────────────────────────────────────────────
@router.get("/admin/review-queues", response_model=AdminReviewQueues, dependencies=[Depends(verify_admin)])
async def admin_review_queues(db: AsyncSession = Depends(get_session)):
    claim_rows = (await db.execute(
        select(MechanicClaim, Mechanic)
        .join(Mechanic, Mechanic.id == MechanicClaim.mechanic_id)
        .where(MechanicClaim.status == ClaimStatus.pending)
        .order_by(MechanicClaim.created_at.desc())
        .limit(100)
    )).all()
    update_rows = (await db.execute(
        select(ProviderUpdateRequest, Mechanic)
        .join(Mechanic, Mechanic.id == ProviderUpdateRequest.mechanic_id)
        .where(ProviderUpdateRequest.status == ProviderUpdateStatus.pending_review)
        .order_by(ProviderUpdateRequest.created_at.desc())
        .limit(100)
    )).all()

    missing_websites = await db.scalar(select(func.count(Mechanic.id)).where(or_(Mechanic.website.is_(None), Mechanic.website == ""))) or 0
    missing_phones = await db.scalar(select(func.count(Mechanic.id)).where(or_(Mechanic.phone.is_(None), Mechanic.phone == ""))) or 0
    needs_review = await db.scalar(select(func.count(Mechanic.id)).where(Mechanic.requires_admin_review == True)) or 0  # noqa: E712
    low_confidence_addresses = await db.scalar(
        select(func.count(Mechanic.id)).where(
            or_(Mechanic.address.is_(None), Mechanic.address == "", Mechanic.base_lat.is_(None), Mechanic.base_lng.is_(None))
        )
    ) or 0

    return AdminReviewQueues(
        pending_claims=[
            {
                "id": str(claim.id),
                "listing_id": str(mechanic.id),
                "company_name": mechanic.company_name,
                "claimant_name": claim.claimant_name,
                "claimant_email": claim.claimant_email,
                "claimant_phone": claim.claimant_phone,
                "method": str(claim.method.value if hasattr(claim.method, "value") else claim.method),
                "notes": claim.notes,
                "created_at": claim.created_at.isoformat(),
            }
            for claim, mechanic in claim_rows
        ],
        pending_updates=[
            {
                "id": str(update.id),
                "listing_id": str(mechanic.id),
                "company_name": mechanic.company_name,
                "requester_name": update.requester_name,
                "requester_email": update.requester_email,
                "requester_role": update.requester_role,
                "match_score": update.match_score,
                "email_domain_matches_website": update.email_domain_matches_website,
                "requested_changes": update.requested_changes,
                "proof_message": update.proof_message,
                "created_at": update.created_at.isoformat(),
            }
            for update, mechanic in update_rows
        ],
        data_quality={
            "missing_websites": int(missing_websites),
            "missing_phone_numbers": int(missing_phones),
            "pending_public_submissions": int(needs_review),
            "low_confidence_addresses": int(low_confidence_addresses),
        },
    )


@router.get("/{mechanic_id}", response_model=ProviderDetailResponse)
async def get_provider_detail(mechanic_id: str, db: AsyncSession = Depends(get_session)):
    mechanic = await db.get(Mechanic, _mechanic_uuid(mechanic_id))
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
    mechanic = await db.get(Mechanic, _mechanic_uuid(mechanic_id))
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
    if existing_recent:
        created_at = existing_recent.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
    if existing_recent and (cutoff - created_at).total_seconds() < 86400:
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
    mechanic = await db.get(Mechanic, _mechanic_uuid(mechanic_id))
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


@router.post("/{mechanic_id}/update-request", response_model=ProviderUpdateRequestOut, status_code=status.HTTP_201_CREATED)
async def suggest_provider_update(
    mechanic_id: str,
    payload: ProviderUpdateRequestIn,
    x_roadcall_user_id: str | None = Header(default=None),
    db: AsyncSession = Depends(get_session),
):
    mechanic = await db.get(Mechanic, _mechanic_uuid(mechanic_id))
    if not mechanic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Provider not found")

    allowed_roles = {"owner", "manager", "dispatcher", "authorized_company_rep"}
    role = payload.role.strip().lower().replace(" ", "_")
    if role not in allowed_roles:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid representative role")

    match_score = _name_match_score(payload.company_name, mechanic.company_name)
    website = _safe_url(payload.website)
    domain_match = _email_domain_matches_website(payload.work_email, website or mechanic.website)
    if match_score < 0.62:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Submitted company name does not closely match this listing")

    changes = dict(payload.requested_changes or {})
    if payload.company_address:
        changes.setdefault("address", payload.company_address.strip())
    if website:
        changes.setdefault("website", website)

    request_row = ProviderUpdateRequest(
        mechanic_id=mechanic.id,
        user_id=x_roadcall_user_id,
        requester_role=role,
        requester_name=payload.full_name.strip(),
        requester_email=payload.work_email.strip().lower(),
        requester_phone=payload.phone_number.strip(),
        proof_message=payload.proof_message,
        submitted_company_name=payload.company_name.strip(),
        submitted_company_address=payload.company_address,
        submitted_website=website,
        requested_changes=changes,
        match_score=match_score,
        email_domain_matches_website=domain_match,
        status=ProviderUpdateStatus.pending_review,
    )
    db.add(request_row)
    await db.commit()
    await db.refresh(request_row)
    return ProviderUpdateRequestOut(
        id=str(request_row.id),
        mechanic_id=str(mechanic.id),
        status="pending_review",
        match_score=match_score,
        email_domain_matches_website=domain_match,
        message="Update request submitted for Roadcall admin review.",
    )


@router.patch("/admin/claims/{claim_id}", dependencies=[Depends(verify_admin)])
async def review_claim(
    claim_id: str,
    payload: AdminDecisionRequest,
    admin_user: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_session),
):
    claim = await db.get(MechanicClaim, _mechanic_uuid(claim_id))
    if not claim:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Claim not found")
    mechanic = await db.get(Mechanic, claim.mechanic_id)
    if not mechanic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Provider not found")

    decision = payload.status.strip().lower()
    if decision == "approved":
        claim.status = ClaimStatus.approved
        claim.method = ClaimMethod.manual_admin
        claim.approved_at = datetime.now(timezone.utc)
        mechanic.claimed = True
        mechanic.claimed_at = datetime.now(timezone.utc)
        mechanic.claimed_by_phone = claim.claimant_phone
        mechanic.verified_listing = True
        mechanic.verification_status = "claimed"
    elif decision == "rejected":
        claim.status = ClaimStatus.rejected
        claim.rejected_reason = payload.review_notes
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Claim decisions support approved or rejected")
    await db.commit()
    return {"id": str(claim.id), "status": str(claim.status.value if hasattr(claim.status, "value") else claim.status), "reviewed_by": admin_user}


@router.patch("/admin/update-requests/{request_id}", dependencies=[Depends(verify_admin)])
async def review_update_request(
    request_id: str,
    payload: AdminDecisionRequest,
    admin_user: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_session),
):
    update = await db.get(ProviderUpdateRequest, _mechanic_uuid(request_id))
    if not update:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Update request not found")
    mechanic = await db.get(Mechanic, update.mechanic_id)
    if not mechanic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Provider not found")

    decision = payload.status.strip().lower()
    now = datetime.now(timezone.utc)
    if decision == "approved":
        allowed_fields = {"company_name", "contact_name", "phone", "email", "website", "address", "city", "state", "zip_code", "google_maps_url", "service_types", "vehicle_types_supported", "accepts_mobile_roadside", "emergency_service", "service_radius_miles"}
        for field, new_value in (update.requested_changes or {}).items():
            if field not in allowed_fields:
                continue
            old_value = getattr(mechanic, field, None)
            if field == "website":
                new_value = _safe_url(str(new_value))
            if field == "state" and isinstance(new_value, str):
                new_value = new_value.upper()[:2]
            setattr(mechanic, field, new_value)
            db.add(ProviderChangeLog(
                mechanic_id=mechanic.id,
                user_id=update.user_id,
                field_name=field,
                old_value=str(old_value) if old_value is not None else None,
                new_value=str(new_value) if new_value is not None else None,
                source_request_id=update.id,
                status="approved",
                submitted_at=update.created_at,
                reviewed_at=now,
                reviewed_by=admin_user,
            ))
        update.status = ProviderUpdateStatus.approved
        mechanic.requires_admin_review = False
        if mechanic.verification_status == "unverified":
            mechanic.verification_status = "claimed"
    elif decision == "rejected":
        update.status = ProviderUpdateStatus.rejected
    elif decision == "more_info_requested":
        update.status = ProviderUpdateStatus.more_info_requested
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid review status")
    update.reviewed_at = now
    update.reviewed_by = admin_user
    update.review_notes = payload.review_notes
    await db.commit()
    return {"id": str(update.id), "status": str(update.status.value if hasattr(update.status, "value") else update.status), "reviewed_by": admin_user}


@router.post("/admin/{mechanic_id}/verify", dependencies=[Depends(verify_admin)])
async def verify_provider(
    mechanic_id: str,
    payload: VerifyProviderRequest,
    admin_user: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_session),
):
    mechanic = await db.get(Mechanic, _mechanic_uuid(mechanic_id))
    if not mechanic:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Provider not found")
    status_value = payload.verification_status.strip().lower()
    if status_value not in {"unverified", "claimed", "verified", "needs_review"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid verification status")
    old_status = getattr(mechanic, "verification_status", "unverified")
    mechanic.verification_status = status_value
    mechanic.verified_listing = status_value == "verified"
    mechanic.requires_admin_review = status_value == "needs_review"
    db.add(ProviderChangeLog(
        mechanic_id=mechanic.id,
        user_id=admin_user,
        field_name="verification_status",
        old_value=old_status,
        new_value=status_value,
        status="approved",
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by=admin_user,
    ))
    await db.commit()
    return {"id": str(mechanic.id), "verification_status": status_value}


@router.patch("/{mechanic_id}", response_model=MarketplaceProvider)
async def edit_listing(
    mechanic_id: str,
    payload: EditListingRequest,
    db: AsyncSession = Depends(get_session),
):
    """Self-edit a claimed listing. Auth = phone matches claimed_by_phone."""
    mechanic = await db.get(Mechanic, _mechanic_uuid(mechanic_id))
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
