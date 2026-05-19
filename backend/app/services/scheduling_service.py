from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ghl_integration import GHLTenantMapping
from app.services.ghl_service import GHLService


class SchedulingService:
    """Appointment boundary for mechanic tenants.

    GHL is the default scheduling system for the SaaS pivot. Cal.com remains in
    the codebase as a legacy/manual fallback until those fields can be removed
    safely from existing UI and data.
    """

    def __init__(self) -> None:
        self.ghl = GHLService()

    async def fetch_calendars(self, db: AsyncSession, mapping: GHLTenantMapping | None) -> dict[str, Any]:
        if not mapping:
            return {"provider": "gohighlevel", "status": "not_connected", "calendars": []}
        result = await self.ghl.fetch_calendars(db, mapping)
        return {"provider": "gohighlevel", "status": "connected", "result": result}

    async def create_appointment(self, db: AsyncSession, mapping: GHLTenantMapping | None, payload: dict[str, Any]) -> dict[str, Any]:
        if not mapping:
            return {
                "provider": "manual",
                "status": "needs_human_follow_up",
                "message": "No GHL location mapping is connected for this mechanic.",
                "payload": payload,
            }
        result = await self.ghl.create_appointment(db, mapping, payload)
        return {"provider": "gohighlevel", "status": "requested", "result": result}
