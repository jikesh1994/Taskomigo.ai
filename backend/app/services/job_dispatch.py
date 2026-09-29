"""How job searches and analyses leave the API: queued for the worker, or run inline."""

from __future__ import annotations

import asyncio
import uuid
from typing import Protocol

from app.ai.llm.base import LLMProvider
from app.core.database import Database
from app.jobs.providers import JobSearchProvider
from app.services.job_analysis_service import analyze_job
from app.services.job_search_service import run_search

SEARCH_TASK = "jobs.search"  # app/workers/job_tasks.py
ANALYZE_TASK = "jobs.analyze"


class JobDispatcher(Protocol):
    async def search(self, run_id: uuid.UUID) -> None: ...

    async def analyze(self, job_id: uuid.UUID) -> None: ...


class CeleryJobDispatcher:
    """Production path. Sent through the configured app (see resume_dispatch.py)."""

    async def _send(self, task: str, arg: uuid.UUID) -> None:
        from app.workers.celery_app import celery_app

        await asyncio.to_thread(celery_app.send_task, task, args=[str(arg)])

    async def search(self, run_id: uuid.UUID) -> None:
        await self._send(SEARCH_TASK, run_id)

    async def analyze(self, job_id: uuid.UUID) -> None:
        await self._send(ANALYZE_TASK, job_id)


class InlineJobDispatcher:
    """JOB_TASKS_INLINE=true: run within the request (tests, dev without a worker)."""

    def __init__(
        self,
        db: Database,
        providers: dict[str, JobSearchProvider],
        llm: LLMProvider,
        *,
        concurrency: int,
    ) -> None:
        self.db = db
        self.providers = providers
        self.llm = llm
        self.concurrency = concurrency

    async def search(self, run_id: uuid.UUID) -> None:
        async with self.db.session_factory() as session:
            await run_search(session, self.providers, run_id, concurrency=self.concurrency)

    async def analyze(self, job_id: uuid.UUID) -> None:
        async with self.db.session_factory() as session:
            await analyze_job(session, self.llm, job_id)
