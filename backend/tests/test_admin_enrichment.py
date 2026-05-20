from __future__ import annotations

import asyncio

import pytest

from app.api.routes import admin_enrichment


@pytest.mark.asyncio
async def test_start_enrichment_detaches_email_sync_task(monkeypatch):
    admin_enrichment._last_run.clear()
    admin_enrichment._running.clear()
    admin_enrichment._tasks.clear()

    started = asyncio.Event()
    release = asyncio.Event()

    async def fake_run(kind, args):
        started.set()
        await release.wait()
        admin_enrichment._last_run[kind].update(running=False, exit_code=0, finished_at="done")
        admin_enrichment._running.discard(kind)

    async def fake_coverage_counts(_db):
        return 3, 7

    monkeypatch.setenv("APIFY_API_TOKEN", "test-token")
    monkeypatch.setattr(admin_enrichment, "_run_enrichment_subprocess", fake_run)
    monkeypatch.setattr(admin_enrichment, "_coverage_counts", fake_coverage_counts)

    try:
        status = await admin_enrichment.start_enrichment(
            admin_enrichment.EnrichmentStartRequest(kind="email_sync", runs=100),
            db=object(),
        )

        assert status.kind == "email_sync"
        assert status.running is True
        assert status.enriched_total == 3
        assert status.pending_total == 7
        assert status.log_tail == ["Job queued..."]
        assert "email_sync" in admin_enrichment._running
        assert admin_enrichment._tasks
        await asyncio.wait_for(started.wait(), timeout=1)
    finally:
        release.set()
        if admin_enrichment._tasks:
            await asyncio.gather(*admin_enrichment._tasks, return_exceptions=True)
        admin_enrichment._last_run.clear()
        admin_enrichment._running.clear()
        admin_enrichment._tasks.clear()