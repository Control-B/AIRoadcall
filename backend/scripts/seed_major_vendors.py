"""CLI: seed major chain vendor locations into the live DB.

Usage (from /root/AIRoadcall/backend):
    .venv/bin/python -m scripts.seed_major_vendors

Idempotent — safe to run after each deploy.
"""
from __future__ import annotations

import asyncio

from app.core.database import async_session_factory
from app.services.major_vendor_service import MajorVendorService


async def main() -> None:
    async with async_session_factory() as session:
        result = await MajorVendorService.bootstrap_seed(session)
    print(f"major_vendor_seed: inserted={result['inserted']} updated={result['updated']} total={result['total']}")


if __name__ == "__main__":
    asyncio.run(main())
