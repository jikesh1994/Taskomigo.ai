from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    def add(self, token: RefreshToken) -> None:
        self.session.add(token)

    async def mark_rotated(
        self, token_id: uuid.UUID, now: datetime, *, replaced_by_id: uuid.UUID
    ) -> bool:
        """Revoke a token only if it is still active. Returns False if it was already used."""
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now, replaced_by_id=replaced_by_id)
            .execution_options(synchronize_session=False)
        )
        return (result.rowcount or 0) == 1

    async def revoke_family(self, family_id: uuid.UUID, now: datetime) -> int:
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return result.rowcount or 0

    async def revoke_all_for_user(self, user_id: uuid.UUID, now: datetime) -> int:
        result = await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return result.rowcount or 0

    async def purge(self, *, expired_before: datetime, revoked_before: datetime) -> int:
        """Delete tokens that can never be used again."""
        result = await self.session.execute(
            delete(RefreshToken).where(
                or_(
                    RefreshToken.expires_at < expired_before,
                    RefreshToken.revoked_at < revoked_before,
                )
            )
        )
        return result.rowcount or 0
