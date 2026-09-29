from __future__ import annotations

import asyncio
import uuid

from celery import shared_task

from app.core.config import get_settings
from app.core.database import Database
from app.core.logging import get_logger
from app.jobs.providers.registry import build_providers, new_http_client
from app.services.job_analysis_service import analyze_job
from app.services.job_search_service import run_search
from app.workers.resume_tasks import worker_llm_provider

logger = get_logger(__name__)


async def _search(run_id: uuid.UUID) -> str:
    settings = get_settings()
    # Each task runs its own event loop, so use a non-pooled engine and a fresh client.
    db = Database(settings.database_url, use_null_pool=True)
    try:
        async with new_http_client(settings) as client, db.session_factory() as session:
            run = await run_search(
                session,
                build_providers(client, settings),
                run_id,
                concurrency=settings.job_fetch_concurrency,
            )
            return run.status.value if run else "missing"
    finally:
        await db.dispose()


async def _analyze(job_id: uuid.UUID) -> str:
    settings = get_settings()
    db = Database(settings.database_url, use_null_pool=True)
    try:
        async with db.session_factory() as session:
            job = await analyze_job(session, worker_llm_provider(), job_id)
            return job.analysis_status.value if job else "missing"
    finally:
        await db.dispose()


@shared_task(name="jobs.search", ignore_result=True, acks_late=True)
def search_jobs_task(run_id: str) -> str:
    """Idempotent (finished runs are skipped; upserts are keyed), so redelivery is safe."""
    status = asyncio.run(_search(uuid.UUID(run_id)))
    logger.info("job_search_task_done", run_id=run_id, status=status)
    return status


@shared_task(name="jobs.analyze", ignore_result=True, acks_late=True)
def analyze_job_task(job_id: str) -> str:
    """Idempotent: a job already analysed with the current prompt is skipped."""
    status = asyncio.run(_analyze(uuid.UUID(job_id)))
    logger.info("job_analyze_task_done", job_id=job_id, status=status)
    return status
