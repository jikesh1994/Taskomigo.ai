"""How a parse request leaves the API: queued for the worker, or run inline."""

from __future__ import annotations

import asyncio
import uuid
from typing import Protocol

from app.ai.llm.base import LLMProvider
from app.core.database import Database
from app.services.resume_parsing_service import parse_resume
from app.storage import ObjectStorage

PARSE_TASK = "resumes.parse"  # app/workers/resume_tasks.py


class ParseDispatcher(Protocol):
    async def dispatch(self, resume_id: uuid.UUID) -> None: ...


class CeleryParseDispatcher:
    """Production path: the API returns immediately; a worker does the slow AI call."""

    async def dispatch(self, resume_id: uuid.UUID) -> None:
        # Send through the configured app explicitly. `shared_task.delay()` would bind to
        # Celery's *default* app in the API process (which never imports celery_app) and
        # try an AMQP broker on localhost instead of our Redis.
        from app.workers.celery_app import celery_app

        # Publishing is synchronous network I/O; keep it off the event loop.
        await asyncio.to_thread(celery_app.send_task, PARSE_TASK, args=[str(resume_id)])


class InlineParseDispatcher:
    """RESUME_PARSE_INLINE=true: parse within the request (tests, dev without a worker)."""

    def __init__(
        self, db: Database, storage: ObjectStorage, llm: LLMProvider, *, max_pages: int
    ) -> None:
        self.db = db
        self.storage = storage
        self.llm = llm
        self.max_pages = max_pages

    async def dispatch(self, resume_id: uuid.UUID) -> None:
        async with self.db.session_factory() as session:
            await parse_resume(session, self.storage, self.llm, resume_id, max_pages=self.max_pages)
