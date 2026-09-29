"""Periodic housekeeping executed by Celery beat."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utc_now
from app.repositories.token_repository import RefreshTokenRepository

# Revoked tokens are kept briefly so reuse of a just-rotated token is still detected.
REVOKED_TOKEN_RETENTION = timedelta(days=7)


async def purge_refresh_tokens(session: AsyncSession) -> int:
    now = utc_now()
    deleted = await RefreshTokenRepository(session).purge(
        expired_before=now, revoked_before=now - REVOKED_TOKEN_RETENTION
    )
    await session.commit()
    return deleted
