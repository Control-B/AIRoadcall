from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.ghl_integration import (
    GHLAuditLog,
    GHLContactLink,
    GHLRetryQueueItem,
    GHLTenantMapping,
    GHLWebhookEvent,
)
from app.models.lead_capture import LeadCapture

logger = get_logger(__name__)


class GHLService:
    """GoHighLevel CRM/workflow adapter.

    Roadcall remains the source of truth. This service only syncs CRM/contact
    state, workflow triggers, appointments, AI receptionist events, and pipeline
    signals to/from GHL.
    """

    WORKFLOW_EVENT_MAP = {
        "new_lead": "new_lead",
        "missed_call": "missed_call",
        "qualified_roadside_request": "qualified_roadside_request",
        "successful_transfer": "successful_transfer",
        "completed_job": "completed_job",
        "review_request": "review_request",
        "subscription_event": "subscription_event",
    }

    DISPATCH_STAGE_MAP = {
        "created": "new_roadside_request",
        "locating": "qualified_roadside_request",
        "matched": "provider_matched",
        "transfer_started": "transfer_in_progress",
        "transfer_successful": "successful_transfer",
        "completed": "completed_job",
        "cancelled": "cancelled",
        "failed": "needs_follow_up",
    }

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.GHL_BASE_URL.rstrip("/")

    def _fernet(self) -> Fernet:
        secret = (self.settings.GHL_ENCRYPTION_KEY or self.settings.MAGIC_LINK_SECRET or "").strip()
        if not secret:
            secret = "local-dev-ghl-encryption-key"
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
        return Fernet(key)

    def encrypt_secret(self, value: str | None) -> str | None:
        if not value:
            return None
        return self._fernet().encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt_secret(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            return self._fernet().decrypt(value.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            logger.warning("Could not decrypt GHL secret; encryption key may have changed")
            return None

    async def get_mapping_by_org(self, db: AsyncSession, organization_id: str | uuid.UUID) -> GHLTenantMapping | None:
        try:
            org_id = organization_id if isinstance(organization_id, uuid.UUID) else uuid.UUID(str(organization_id))
        except ValueError:
            return None
        result = await db.execute(
            select(GHLTenantMapping).where(
                GHLTenantMapping.organization_id == org_id,
                GHLTenantMapping.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def get_mapping_by_location(self, db: AsyncSession, location_id: str | None) -> GHLTenantMapping | None:
        if not location_id:
            return None
        result = await db.execute(
            select(GHLTenantMapping).where(
                GHLTenantMapping.location_id == location_id,
                GHLTenantMapping.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def upsert_mapping(
        self,
        db: AsyncSession,
        *,
        organization_id: str,
        location_id: str,
        subaccount_name: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        webhook_secret: str | None = None,
        pipeline_id: str | None = None,
        default_workflow_id: str | None = None,
    ) -> GHLTenantMapping:
        org_uuid = uuid.UUID(str(organization_id))
        result = await db.execute(select(GHLTenantMapping).where(GHLTenantMapping.organization_id == org_uuid))
        mapping = result.scalar_one_or_none()
        if mapping is None:
            mapping = GHLTenantMapping(organization_id=org_uuid, location_id=location_id)
            db.add(mapping)
        mapping.location_id = location_id
        mapping.subaccount_name = subaccount_name or mapping.subaccount_name
        mapping.pipeline_id = pipeline_id or mapping.pipeline_id
        mapping.default_workflow_id = default_workflow_id or mapping.default_workflow_id
        if access_token:
            mapping.encrypted_access_token = self.encrypt_secret(access_token)
        if refresh_token:
            mapping.encrypted_refresh_token = self.encrypt_secret(refresh_token)
        if webhook_secret:
            mapping.encrypted_webhook_secret = self.encrypt_secret(webhook_secret)
        mapping.is_active = True
        await db.flush()
        await self.audit(db, mapping, "mapping.upsert", "inbound", "success", "organization", str(org_uuid), {"location_id": location_id})
        return mapping

    def verify_signature(
        self,
        mapping: GHLTenantMapping | None,
        raw_body: bytes,
        signature: str | None,
        timestamp: str | None = None,
    ) -> bool:
        if not mapping or not signature:
            return False
        if timestamp:
            try:
                event_time = datetime.fromtimestamp(int(timestamp), timezone.utc)
            except (TypeError, ValueError):
                return False
            age = abs((datetime.now(timezone.utc) - event_time).total_seconds())
            if age > self.settings.GHL_WEBHOOK_TOLERANCE_SECONDS:
                return False
        secret = self.decrypt_secret(mapping.encrypted_webhook_secret)
        if not secret:
            return False
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        timestamped_expected = None
        if timestamp:
            timestamped_expected = hmac.new(
                secret.encode("utf-8"),
                timestamp.encode("utf-8") + b"." + raw_body,
                hashlib.sha256,
            ).hexdigest()
        normalized = signature.strip()
        if normalized.startswith("sha256="):
            normalized = normalized.split("=", 1)[1]
        return hmac.compare_digest(expected, normalized) or (
            timestamped_expected is not None and hmac.compare_digest(timestamped_expected, normalized)
        )

    async def audit(
        self,
        db: AsyncSession,
        mapping: GHLTenantMapping | None,
        action: str,
        direction: str,
        status: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        db.add(
            GHLAuditLog(
                tenant_mapping_id=mapping.id if mapping else None,
                organization_id=mapping.organization_id if mapping else None,
                action=action,
                direction=direction,
                status=status,
                entity_type=entity_type,
                entity_id=entity_id,
                payload_json=payload,
                error_message=error,
            )
        )

    async def record_webhook(
        self,
        db: AsyncSession,
        mapping: GHLTenantMapping | None,
        event_type: str,
        payload: dict[str, Any],
        signature_valid: bool,
        status: str = "received",
        error: str | None = None,
    ) -> GHLWebhookEvent:
        event = GHLWebhookEvent(
            tenant_mapping_id=mapping.id if mapping else None,
            event_type=event_type,
            external_event_id=str(payload.get("id") or payload.get("eventId") or payload.get("contactId") or "") or None,
            signature_valid=signature_valid,
            payload_json=payload,
            processing_status=status,
            error_message=error,
        )
        db.add(event)
        await db.flush()
        await self.audit(db, mapping, f"webhook.{event_type}", "inbound", status, payload=payload, error=error)
        return event

    async def queue_retry(
        self,
        db: AsyncSession,
        mapping: GHLTenantMapping | None,
        action: str,
        endpoint: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
        error: str | None = None,
    ) -> GHLRetryQueueItem:
        item = GHLRetryQueueItem(
            tenant_mapping_id=mapping.id if mapping else None,
            action=action,
            endpoint=endpoint,
            method="POST",
            payload_json=payload,
            headers_json=headers or {},
            status="pending",
            last_error=error,
            next_attempt_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        db.add(item)
        await self.audit(db, mapping, f"retry.queued.{action}", "outbound", "queued", payload=payload, error=error)
        return item

    def _auth_headers(self, mapping: GHLTenantMapping) -> dict[str, str]:
        token = self.decrypt_secret(mapping.encrypted_access_token)
        if not token:
            raise RuntimeError("GHL access token is not configured for this tenant")
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Version": "2021-07-28",
        }

    async def _post(self, db: AsyncSession, mapping: GHLTenantMapping, endpoint: str, payload: dict[str, Any], action: str) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            headers = self._auth_headers(mapping)
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, headers=headers, json=payload)
            if response.status_code >= 400:
                raise RuntimeError(f"GHL HTTP {response.status_code}: {response.text[:500]}")
            await self.audit(db, mapping, action, "outbound", "success", payload=payload)
            if response.text:
                return response.json()
            return {"success": True}
        except Exception as exc:
            await self.queue_retry(db, mapping, action, endpoint, payload, headers={}, error=str(exc))
            await self.audit(db, mapping, action, "outbound", "queued", payload=payload, error=str(exc))
            return {"queued": True, "error": str(exc)}

    async def sync_contact(self, db: AsyncSession, mapping: GHLTenantMapping, contact: dict[str, Any], entity_type: str, entity_id: str) -> dict[str, Any]:
        payload = {
            "locationId": mapping.location_id,
            "firstName": contact.get("first_name") or contact.get("name"),
            "name": contact.get("name"),
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "companyName": contact.get("company") or contact.get("company_name"),
            "source": contact.get("source") or "Roadcall",
            "tags": sorted(set(["roadcall", *(contact.get("tags") or [])])),
            "customFields": contact.get("custom_fields") or [],
        }
        result = await self._post(db, mapping, "/contacts/upsert", payload, "contact.upsert")
        contact_id = result.get("contact", {}).get("id") or result.get("id") or contact.get("ghl_contact_id")
        if contact_id:
            await self.upsert_contact_link(db, mapping, contact_id, entity_type, entity_id, contact.get("email"), contact.get("phone"))
        return result

    async def upsert_contact_link(
        self,
        db: AsyncSession,
        mapping: GHLTenantMapping,
        ghl_contact_id: str,
        entity_type: str,
        entity_id: str,
        email: str | None,
        phone: str | None,
    ) -> GHLContactLink:
        result = await db.execute(
            select(GHLContactLink).where(
                GHLContactLink.tenant_mapping_id == mapping.id,
                GHLContactLink.roadcall_entity_type == entity_type,
                GHLContactLink.roadcall_entity_id == str(entity_id),
            )
        )
        link = result.scalar_one_or_none()
        if link is None:
            link = GHLContactLink(
                tenant_mapping_id=mapping.id,
                ghl_contact_id=ghl_contact_id,
                roadcall_entity_type=entity_type,
                roadcall_entity_id=str(entity_id),
            )
            db.add(link)
        link.ghl_contact_id = ghl_contact_id
        link.email = email or link.email
        link.phone = phone or link.phone
        link.last_synced_at = datetime.now(timezone.utc)
        await db.flush()
        return link

    async def send_new_lead(self, db: AsyncSession, mapping: GHLTenantMapping, lead: LeadCapture | dict[str, Any]) -> dict[str, Any]:
        if isinstance(lead, LeadCapture):
            contact = {
                "name": lead.name,
                "email": lead.email,
                "company": lead.company,
                "source": lead.source or "Roadcall lead capture",
                "tags": ["new-lead", lead.vertical or "general"],
            }
            entity_id = str(lead.id)
        else:
            contact = dict(lead)
            contact.setdefault("tags", ["new-lead"])
            entity_id = str(contact.get("id") or contact.get("email") or uuid.uuid4())
        result = await self.sync_contact(db, mapping, contact, "lead", entity_id)
        await self.trigger_workflow(db, mapping, "new_lead", {"contact": contact, "entity_id": entity_id})
        return result

    async def trigger_workflow(self, db: AsyncSession, mapping: GHLTenantMapping, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        workflow_event = self.WORKFLOW_EVENT_MAP.get(event, event)
        workflow_id = payload.get("workflow_id") or mapping.default_workflow_id
        body = {
            "locationId": mapping.location_id,
            "event": workflow_event,
            "workflowId": workflow_id,
            "payload": payload,
        }
        return await self._post(db, mapping, "/workflows/trigger", body, f"workflow.trigger.{workflow_event}")

    async def push_dispatch_status(self, db: AsyncSession, mapping: GHLTenantMapping, payload: dict[str, Any]) -> dict[str, Any]:
        status = str(payload.get("status") or "").lower()
        stage = payload.get("pipeline_stage") or self.DISPATCH_STAGE_MAP.get(status, status)
        body = {
            "locationId": mapping.location_id,
            "pipelineId": payload.get("pipeline_id") or mapping.pipeline_id,
            "stage": stage,
            "status": status,
            "jobId": payload.get("job_id"),
            "publicJobId": payload.get("public_job_id"),
            "driverPhone": payload.get("driver_phone"),
            "driverName": payload.get("driver_name"),
            "issueType": payload.get("issue_type"),
            "metadata": payload,
        }
        return await self._post(db, mapping, "/opportunities/roadcall-status", body, "dispatch.status.push")

    async def process_retry_queue(self, db: AsyncSession, limit: int = 25) -> dict[str, int]:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(GHLRetryQueueItem)
            .where(
                GHLRetryQueueItem.status == "pending",
                GHLRetryQueueItem.next_attempt_at <= now,
                GHLRetryQueueItem.attempt_count < GHLRetryQueueItem.max_attempts,
            )
            .order_by(GHLRetryQueueItem.next_attempt_at.asc())
            .limit(limit)
        )
        items = list(result.scalars().all())
        processed = succeeded = failed = 0
        for item in items:
            processed += 1
            mapping = None
            if item.tenant_mapping_id:
                mapping = await db.get(GHLTenantMapping, item.tenant_mapping_id)
            if not mapping:
                item.status = "failed"
                item.last_error = "Missing tenant mapping"
                failed += 1
                continue
            try:
                headers = self._auth_headers(mapping)
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.request(item.method, f"{self.base_url}{item.endpoint}", headers=headers, json=item.payload_json)
                if response.status_code < 400:
                    item.attempt_count += 1
                    item.status = "succeeded"
                    item.last_error = None
                    succeeded += 1
                else:
                    raise RuntimeError(f"GHL HTTP {response.status_code}: {response.text[:500]}")
            except Exception as exc:
                item.attempt_count += 1
                item.last_error = str(exc)
                if item.attempt_count >= item.max_attempts:
                    item.status = "failed"
                    failed += 1
                else:
                    item.next_attempt_at = now + timedelta(minutes=min(60, 5 * item.attempt_count))
        return {"processed": processed, "succeeded": succeeded, "failed": failed}
