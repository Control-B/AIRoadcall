from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.plan_config import PlanFeature
from app.services.provisioning_service import ProvisioningService


service = ProvisioningService()


def require_tenant_feature(feature: PlanFeature | str) -> Callable:
    feature_value = str(feature)

    async def dependency(
        x_roadcall_tenant_id: str | None = Header(default=None),
        x_roadcall_organization_id: str | None = Header(default=None),
        db: AsyncSession = Depends(get_db),
    ):
        tenant_id: uuid.UUID | None = None
        if x_roadcall_tenant_id:
            try:
                tenant_id = uuid.UUID(x_roadcall_tenant_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid tenant header") from exc
        elif x_roadcall_organization_id:
            from sqlalchemy import select
            from app.models.tenant_provisioning import Tenant

            try:
                org_id = uuid.UUID(x_roadcall_organization_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid organization header") from exc
            result = await db.execute(select(Tenant).where(Tenant.organization_id == org_id))
            tenant = result.scalar_one_or_none()
            tenant_id = tenant.id if tenant else None

        if not tenant_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant context is required")

        allowed, tenant = await service.tenant_has_feature(db, tenant_id, feature_value)
        if not allowed:
            plan = tenant.current_plan if tenant else "unknown"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_value}' is not enabled for plan '{plan}'. Upgrade is required.",
            )
        return tenant

    return dependency