from __future__ import annotations

import asyncio

from celery import shared_task

from app.core.config import get_settings
from app.core.database import Database
from app.core.logging import get_logger
from app.services.maintenance_service import purge_refresh_tokens

logger = get_logger(__name__)


async def _purge() -> int:
    # Each task invocation runs its own event loop, so use a non-pooled engine.
    db = Database(get_settings().database_url, use_null_pool=True)
    try:
        async with db.session_factory() as session:
            return await purge_refresh_tokens(session)
    finally:
        await db.dispose()


@shared_task(name="maintenance.purge_refresh_tokens", ignore_result=True)
def purge_refresh_tokens_task() -> int:
    deleted = asyncio.run(_purge())
    logger.info("refresh_tokens_purged", deleted=deleted)
    return deleted


@shared_task(name="maintenance.ping")
def ping() -> str:
    """Used by health checks and smoke tests to verify a worker is consuming tasks."""
    return "pong"
