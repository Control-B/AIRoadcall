"""Admin enrichment controls — kick off Apify scrape/email enrichment jobs and track status.

This is intentionally lightweight: it spawns the existing scripts as background subprocesses
and tracks the most recent run in memory. It does NOT replace a proper job queue.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.routes.admin_auth import verify_admin
from app.core.logging import get_logger
from app.models.mechanic import Mechanic

logger = get_logger(__name__)
router = APIRouter(prefix="/admin/enrichment", tags=["admin-enrichment"])

JobKind = Literal["emails", "email_sync", "mechanics"]

# Last-run state, in-memory. Acceptable for a single-process admin SaaS dashboard.
_last_run: dict[str, dict] = {}
_running: set[str] = set()
_tasks: set[asyncio.Task[None]] = set()


class EnrichmentStartRequest(BaseModel):
    kind: JobKind = "emails"
    limit: int = 200
    batch: int = 20
    runs: int = 100
    dry_run: bool = False


class EnrichmentStatus(BaseModel):
    kind: JobKind
    running: bool
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    log_tail: list[str] = []
    enriched_total: int = 0
    pending_total: int = 0


def _script_for(kind: JobKind) -> Path:
    backend_root = Path(__file__).resolve().parents[3]
    if kind == "email_sync":
        return backend_root / "scripts" / "sync_apify_email_datasets.py"
    if kind == "emails":
        return backend_root / "scripts" / "enrich_emails.py"
    return backend_root / "scripts" / "import_mechanics.py"


async def _run_enrichment_subprocess(kind: JobKind, args: list[str]) -> None:
    script = _script_for(kind)
    if not script.exists():
        logger.error(f"Enrichment script missing: {script}")
        _last_run[kind] = {
            **_last_run.get(kind, {}),
            "running": False,
            "exit_code": 127,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "log_tail": [f"Script not found: {script}"],
        }
        _running.discard(kind)
        return

    cmd = [sys.executable, str(script), *args]
    started = datetime.now(timezone.utc).isoformat()
    _last_run[kind] = {
        "kind": kind,
        "running": True,
        "started_at": started,
        "finished_at": None,
        "exit_code": None,
        "log_tail": [],
    }
    logger.info(f"[enrichment:{kind}] starting subprocess: {' '.join(cmd)}")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(script.parent.parent),
            env=os.environ.copy(),
        )

        log_lines: list[str] = []
        assert proc.stdout is not None
        async for raw in proc.stdout:
            try:
                line = raw.decode("utf-8", errors="replace").rstrip()
            except Exception:
                line = "<binary>"
            log_lines.append(line)
            if len(log_lines) > 200:
                log_lines = log_lines[-200:]
            _last_run[kind]["log_tail"] = log_lines[-50:]

        await proc.wait()
        _last_run[kind].update(
            running=False,
            exit_code=proc.returncode,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.info(f"[enrichment:{kind}] finished with exit code {proc.returncode}")
    except Exception as exc:
        logger.exception(f"[enrichment:{kind}] subprocess error")
        _last_run[kind].update(
            running=False,
            exit_code=-1,
            finished_at=datetime.now(timezone.utc).isoformat(),
            log_tail=(_last_run[kind].get("log_tail") or []) + [f"ERROR: {exc}"],
        )
    finally:
        _running.discard(kind)


@router.post(
    "/start",
    response_model=EnrichmentStatus,
    dependencies=[Depends(verify_admin)],
)
async def start_enrichment(
    payload: EnrichmentStartRequest,
    db: AsyncSession = Depends(get_session),
):
    if payload.kind in _running:
        raise HTTPException(status_code=409, detail=f"{payload.kind} job already running")

    if not os.environ.get("APIFY_API_TOKEN"):
        raise HTTPException(
            status_code=503,
            detail="APIFY_API_TOKEN is not configured on the backend",
        )

    args: list[str] = []
    if payload.kind == "emails":
        args = ["--limit", str(payload.limit), "--batch", str(payload.batch)]
        if payload.dry_run:
            args.append("--dry-run")
    elif payload.kind == "email_sync":
        args = ["--runs", str(payload.runs)]
        args.append("--dry-run" if payload.dry_run else "--apply")

    _running.add(payload.kind)
    started_at = datetime.now(timezone.utc).isoformat()
    _last_run[payload.kind] = {
        "kind": payload.kind,
        "running": True,
        "started_at": started_at,
        "finished_at": None,
        "exit_code": None,
        "log_tail": ["Job queued..."],
    }
    task = asyncio.create_task(_run_enrichment_subprocess(payload.kind, args))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)

    enriched, pending = await _coverage_counts(db)
    return EnrichmentStatus(
        kind=payload.kind,
        running=True,
        started_at=started_at,
        log_tail=["Job queued..."],
        enriched_total=enriched,
        pending_total=pending,
    )


@router.get(
    "/status",
    response_model=EnrichmentStatus,
    dependencies=[Depends(verify_admin)],
)
async def enrichment_status(
    kind: JobKind = "emails",
    db: AsyncSession = Depends(get_session),
):
    state = _last_run.get(kind, {})
    enriched, pending = await _coverage_counts(db)
    return EnrichmentStatus(
        kind=kind,
        running=kind in _running,
        started_at=state.get("started_at"),
        finished_at=state.get("finished_at"),
        exit_code=state.get("exit_code"),
        log_tail=state.get("log_tail", []),
        enriched_total=enriched,
        pending_total=pending,
    )


async def _coverage_counts(db: AsyncSession) -> tuple[int, int]:
    enriched = await db.scalar(
        select(func.count(Mechanic.id)).where(
            Mechanic.email.isnot(None), Mechanic.email != ""
        )
    ) or 0
    pending = await db.scalar(
        select(func.count(Mechanic.id)).where(
            Mechanic.website.isnot(None),
            Mechanic.website != "",
            (Mechanic.email.is_(None)) | (Mechanic.email == ""),
        )
    ) or 0
    return int(enriched), int(pending)
