from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_admin_api_key
from app.models.ghl_integration import GHLRetryQueueItem, GHLTenantMapping
from app.models.job import Job
from app.models.lead_capture import LeadCapture
from app.services.ghl_service import GHLService

router = APIRouter(prefix="/ghl", tags=["gohighlevel"])
service = GHLService()


class TenantMappingIn(BaseModel):
    organization_id: str
    location_id: str
    subaccount_name: str | None = None
    access_token: str | None = Field(default=None, repr=False)
    refresh_token: str | None = Field(default=None, repr=False)
    webhook_secret: str | None = Field(default=None, repr=False)
    pipeline_id: str | None = None
    default_workflow_id: str | None = None


class TenantMappingOut(BaseModel):
    id: str
    organization_id: str
    location_id: str
    subaccount_name: str | None
    pipeline_id: str | None
    default_workflow_id: str | None
    is_active: bool


class TenantMappingListResponse(BaseModel):
    mappings: list[TenantMappingOut]


class RetryOverviewResponse(BaseModel):
    pending: int = 0
    succeeded: int = 0
    failed: int = 0


class OrganizationScopedIn(BaseModel):
    organization_id: str


class ContactSyncIn(OrganizationScopedIn):
    entity_type: str = "contact"
    entity_id: str | None = None
    name: str | None = None
    first_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    source: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else value


class DispatchStatusIn(OrganizationScopedIn):
    status: str | None = None
    pipeline_stage: str | None = None
    pipeline_id: str | None = None


class WorkflowTriggerIn(OrganizationScopedIn):
    event: str
    workflow_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RetryProcessIn(BaseModel):
    limit: int = Field(default=25, ge=1, le=100)


class GenericResponse(BaseModel):
    ok: bool = True
    result: dict[str, Any] | None = None


async def _mapping_or_404(db: AsyncSession, organization_id: str) -> GHLTenantMapping:
    mapping = await service.get_mapping_by_org(db, organization_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="No active GHL tenant mapping for organization")
    return mapping


def _get_signature(headers: dict[str, str]) -> str | None:
    return (
        headers.get("x-ghl-signature")
        or headers.get("x-leadconnector-signature")
        or headers.get("x-highlevel-signature")
        or headers.get("x-signature")
    )


def _get_signature_timestamp(headers: dict[str, str]) -> str | None:
    return headers.get("x-ghl-timestamp") or headers.get("x-leadconnector-timestamp") or headers.get("x-timestamp")


async def _signed_webhook_context(request: Request, db: AsyncSession) -> tuple[GHLTenantMapping, dict[str, Any], bytes]:
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    location = payload.get("location") if isinstance(payload.get("location"), dict) else {}
    location_id = payload.get("locationId") or payload.get("location_id") or location.get("id")
    mapping = await service.get_mapping_by_location(db, location_id)
    normalized_headers = {k.lower(): v for k, v in request.headers.items()}
    signature = _get_signature(normalized_headers)
    timestamp = _get_signature_timestamp(normalized_headers)
    if not service.verify_signature(mapping, raw_body, signature, timestamp):
        await service.record_webhook(db, mapping, payload.get("type") or "unknown", payload, False, "rejected", "Invalid GHL webhook signature")
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid GHL webhook signature")
    return mapping, payload, raw_body


def _lead_from_form_payload(payload: dict[str, Any]) -> dict[str, Any]:
    contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else {}
    fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    return {
        "email": (payload.get("email") or contact.get("email") or fields.get("email") or "").strip().lower(),
        "name": payload.get("name") or contact.get("name") or fields.get("name"),
        "company": payload.get("company") or contact.get("companyName") or fields.get("company"),
        "vertical": payload.get("vertical") or fields.get("vertical") or "general",
        "source": payload.get("source") or payload.get("formName") or "ghl_form",
        "notes": json.dumps({"ghl_form_submission": payload}, default=str)[:5000],
    }


@router.post("/admin/tenant-mappings", response_model=TenantMappingOut, dependencies=[Depends(require_admin_api_key)])
async def upsert_tenant_mapping(payload: TenantMappingIn, db: AsyncSession = Depends(get_db)):
    mapping = await service.upsert_mapping(db, **payload.model_dump())
    await db.commit()
    await db.refresh(mapping)
    return TenantMappingOut(
        id=str(mapping.id),
        organization_id=str(mapping.organization_id),
        location_id=mapping.location_id,
        subaccount_name=mapping.subaccount_name,
        pipeline_id=mapping.pipeline_id,
        default_workflow_id=mapping.default_workflow_id,
        is_active=mapping.is_active,
    )


@router.get("/admin/tenant-mappings", response_model=TenantMappingListResponse, dependencies=[Depends(require_admin_api_key)])
async def list_tenant_mappings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GHLTenantMapping).order_by(GHLTenantMapping.created_at.desc()))
    mappings = result.scalars().all()
    return TenantMappingListResponse(
        mappings=[
            TenantMappingOut(
                id=str(mapping.id),
                organization_id=str(mapping.organization_id),
                location_id=mapping.location_id,
                subaccount_name=mapping.subaccount_name,
                pipeline_id=mapping.pipeline_id,
                default_workflow_id=mapping.default_workflow_id,
                is_active=mapping.is_active,
            )
            for mapping in mappings
        ]
    )


@router.get("/retry/overview", response_model=RetryOverviewResponse, dependencies=[Depends(require_admin_api_key)])
async def get_retry_overview(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GHLRetryQueueItem.status, func.count()).group_by(GHLRetryQueueItem.status))
    counts = {status: count for status, count in result.all()}
    return RetryOverviewResponse(
        pending=counts.get("pending", 0),
        succeeded=counts.get("succeeded", 0),
        failed=counts.get("failed", 0),
    )


@router.post("/leads/{lead_id}/sync", response_model=GenericResponse, dependencies=[Depends(require_admin_api_key)])
async def sync_roadcall_lead_to_ghl(lead_id: str, payload: OrganizationScopedIn, db: AsyncSession = Depends(get_db)):
    mapping = await _mapping_or_404(db, payload.organization_id)
    try:
        lead_uuid = uuid.UUID(str(lead_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid lead id") from exc
    result = await db.execute(select(LeadCapture).where(LeadCapture.id == lead_uuid))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    sync_result = await service.send_new_lead(db, mapping, lead)
    await db.commit()
    return GenericResponse(result=sync_result)


@router.post("/contacts/sync", response_model=GenericResponse, dependencies=[Depends(require_admin_api_key)])
async def sync_contact_to_ghl(payload: ContactSyncIn, db: AsyncSession = Depends(get_db)):
    mapping = await _mapping_or_404(db, payload.organization_id)
    contact = payload.model_dump(exclude={"organization_id", "entity_type", "entity_id"}, exclude_none=True)
    entity_id = payload.entity_id or payload.email or payload.phone or str(uuid.uuid4())
    result = await service.sync_contact(db, mapping, contact, payload.entity_type, entity_id)
    await db.commit()
    return GenericResponse(result=result)


@router.post("/dispatch/{job_id}/status", response_model=GenericResponse, dependencies=[Depends(require_admin_api_key)])
async def push_dispatch_status_to_ghl(job_id: str, payload: DispatchStatusIn, db: AsyncSession = Depends(get_db)):
    mapping = await _mapping_or_404(db, payload.organization_id)
    try:
        job_uuid = uuid.UUID(str(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid job id") from exc
    result = await db.execute(select(Job).where(Job.id == job_uuid))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    status_value = payload.status or str(job.status.value if hasattr(job.status, "value") else job.status)
    sync_payload = {
        "job_id": str(job.id),
        "public_job_id": job.public_job_id,
        "status": status_value,
        "pipeline_stage": payload.pipeline_stage,
        "pipeline_id": payload.pipeline_id,
        "driver_name": job.driver_name,
        "driver_phone": job.driver_phone,
        "issue_type": str(job.issue_type.value if hasattr(job.issue_type, "value") else job.issue_type),
        "driver_city": job.driver_city,
        "driver_state": job.driver_state,
    }
    sync_result = await service.push_dispatch_status(db, mapping, sync_payload)
    await db.commit()
    return GenericResponse(result=sync_result)


@router.post("/workflows/trigger", response_model=GenericResponse, dependencies=[Depends(require_admin_api_key)])
async def trigger_ghl_workflow(payload: WorkflowTriggerIn, db: AsyncSession = Depends(get_db)):
    mapping = await _mapping_or_404(db, payload.organization_id)
    workflow_payload = dict(payload.payload)
    if payload.workflow_id:
        workflow_payload["workflow_id"] = payload.workflow_id
    result = await service.trigger_workflow(db, mapping, payload.event, workflow_payload)
    await db.commit()
    return GenericResponse(result=result)


@router.post("/retry/process", response_model=GenericResponse, dependencies=[Depends(require_admin_api_key)])
async def process_ghl_retry_queue(payload: RetryProcessIn, db: AsyncSession = Depends(get_db)):
    result = await service.process_retry_queue(db, payload.limit)
    await db.commit()
    return GenericResponse(result=result)


@router.post("/webhooks/forms", status_code=status.HTTP_202_ACCEPTED)
async def receive_ghl_form_submission(request: Request, db: AsyncSession = Depends(get_db)):
    mapping, payload, _ = await _signed_webhook_context(request, db)
    lead_data = _lead_from_form_payload(payload)
    if not lead_data["email"]:
        await service.record_webhook(db, mapping, "form_submission", payload, True, "ignored", "No email in form submission")
        await db.commit()
        return {"ok": True, "ignored": True}

    result = await db.execute(select(LeadCapture).where(LeadCapture.email == lead_data["email"]))
    lead = result.scalar_one_or_none()
    if lead is None:
        lead = LeadCapture(**lead_data)
        db.add(lead)
    else:
        lead.name = lead_data["name"] or lead.name
        lead.company = lead_data["company"] or lead.company
        lead.vertical = lead_data["vertical"] or lead.vertical
        lead.source = lead.source or lead_data["source"]
        lead.notes = lead_data["notes"]
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Lead already exists")
    await service.record_webhook(db, mapping, "form_submission", payload, True, "processed")
    await service.upsert_contact_link(
        db,
        mapping,
        str(payload.get("contactId") or (payload.get("contact") if isinstance(payload.get("contact"), dict) else {}).get("id") or lead.id),
        "lead",
        str(lead.id),
        lead.email,
        None,
    )
    await db.commit()
    return {"ok": True, "lead_id": str(lead.id)}


@router.post("/webhooks/contact-updates", status_code=status.HTTP_202_ACCEPTED)
async def receive_ghl_contact_update(request: Request, db: AsyncSession = Depends(get_db)):
    mapping, payload, _ = await _signed_webhook_context(request, db)
    contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else payload
    contact_id = str(contact.get("id") or payload.get("contactId") or "")
    await service.record_webhook(db, mapping, "contact_update", payload, True, "processed")
    if contact_id:
        await service.upsert_contact_link(
            db,
            mapping,
            contact_id,
            str(contact.get("entityType") or "ghl_contact"),
            str(contact.get("entityId") or contact_id),
            contact.get("email"),
            contact.get("phone"),
        )
    await db.commit()
    return {"ok": True}


@router.post("/webhooks/appointments", status_code=status.HTTP_202_ACCEPTED)
async def receive_ghl_appointment(request: Request, db: AsyncSession = Depends(get_db)):
    mapping, payload, _ = await _signed_webhook_context(request, db)
    await service.record_webhook(db, mapping, "appointment_booking", payload, True, "processed")
    await service.trigger_workflow(db, mapping, "new_lead", {"source": "ghl_appointment", "appointment": payload})
    await db.commit()
    return {"ok": True}


@router.post("/webhooks/voice-call", status_code=status.HTTP_202_ACCEPTED)
async def receive_ghl_voice_call(request: Request, db: AsyncSession = Depends(get_db)):
    mapping, payload, _ = await _signed_webhook_context(request, db)
    call_status = str(payload.get("status") or payload.get("callStatus") or "").lower()
    await service.record_webhook(db, mapping, "ai_voice_call", payload, True, "processed")
    if "missed" in call_status:
        await service.trigger_workflow(db, mapping, "missed_call", {"source": "ghl_ai_receptionist", "call": payload})
    await db.commit()
    return {"ok": True}
