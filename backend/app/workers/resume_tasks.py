from __future__ import annotations

import asyncio
import uuid

from celery import shared_task

from app.ai.llm import create_llm_provider
from app.ai.llm.base import DisabledProvider, LLMProvider
from app.core.config import get_settings
from app.core.database import Database
from app.core.exceptions import ConfigurationError
from app.core.logging import get_logger
from app.services.resume_parsing_service import parse_resume
from app.storage.factory import create_storage

logger = get_logger(__name__)


def worker_llm_provider() -> LLMProvider:
    settings = get_settings()
    try:
        return create_llm_provider(settings)
    except ConfigurationError as exc:
        # Misconfiguration becomes a clear per-resume failure instead of a crash loop.
        logger.error("llm_misconfigured", error=str(exc))
        return DisabledProvider()


async def _parse(resume_id: uuid.UUID) -> str:
    settings = get_settings()
    # Each task runs its own event loop, so use a non-pooled engine.
    db = Database(settings.database_url, use_null_pool=True)
    try:
        async with db.session_factory() as session:
            resume = await parse_resume(
                session,
                create_storage(settings),
                worker_llm_provider(),
                resume_id,
                max_pages=settings.resume_max_pages,
            )
            return resume.parse_status.value if resume else "missing"
    finally:
        await db.dispose()


@shared_task(name="resumes.parse", ignore_result=True, acks_late=True)
def parse_resume_task(resume_id: str) -> str:
    """Idempotent (parse_resume skips already-parsed resumes), so redelivery is safe."""
    status = asyncio.run(_parse(uuid.UUID(resume_id)))
    logger.info("resume_parse_task_done", resume_id=resume_id, status=status)
    return status
