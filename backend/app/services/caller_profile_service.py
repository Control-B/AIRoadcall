"""Caller profile lookup / upsert keyed by normalized phone."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.caller_profile import CallerProfile
from app.services.shared_caller_location_service import normalize_phone


_UPDATABLE_FIELDS = (
    "driver_name",
    "vehicle_type",
    "truck_number",
    "trailer_number",
    "company_name",
)


class CallerProfileService:
    @staticmethod
    async def get_by_phone(db: AsyncSession, phone: str | None) -> CallerProfile | None:
        norm = normalize_phone(phone)
        if not norm:
            return None
        result = await db.execute(select(CallerProfile).where(CallerProfile.phone == norm))
        return result.scalar_one_or_none()

    @staticmethod
    async def upsert(
        db: AsyncSession,
        *,
        phone: str,
        bump_call_count: bool = True,
        **fields: Any,
    ) -> CallerProfile | None:
        norm = normalize_phone(phone)
        if not norm:
            return None

        existing = await CallerProfileService.get_by_phone(db, norm)
        now = datetime.now(timezone.utc)

        if existing is None:
            profile = CallerProfile(
                phone=norm,
                call_count=1 if bump_call_count else 0,
                last_call_at=now if bump_call_count else None,
            )
            for key in _UPDATABLE_FIELDS:
                value = fields.get(key)
                if value:
                    setattr(profile, key, str(value).strip())
            db.add(profile)
            await db.flush()
            return profile

        for key in _UPDATABLE_FIELDS:
            value = fields.get(key)
            if value:
                setattr(existing, key, str(value).strip())
        if bump_call_count:
            existing.call_count = (existing.call_count or 0) + 1
            existing.last_call_at = now
        await db.flush()
        return existing

    @staticmethod
    def summarize(profile: CallerProfile) -> str:
        bits: list[str] = []
        if profile.driver_name:
            bits.append(profile.driver_name)
        if profile.company_name:
            bits.append(f"with {profile.company_name}")
        if profile.vehicle_type:
            bits.append(f"driving a {profile.vehicle_type}")
        if profile.truck_number:
            bits.append(f"truck #{profile.truck_number}")
        if profile.trailer_number:
            bits.append(f"trailer #{profile.trailer_number}")
        return ", ".join(bits) if bits else ""
