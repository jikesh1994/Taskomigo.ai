from __future__ import annotations

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume


class ResumeRepository:
    """Resume access. User-facing lookups are always scoped to the owner."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, resume: Resume) -> None:
        self.session.add(resume)

    async def delete(self, resume: Resume) -> None:
        await self.session.delete(resume)

    async def get_for_user(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume | None:
        result = await self.session.execute(
            select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, resume_id: uuid.UUID) -> Resume | None:
        """Unscoped: only for trusted internal callers (the parsing worker)."""
        return await self.session.get(Resume, resume_id, populate_existing=True)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Resume]:
        result = await self.session.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.is_default.desc(), Resume.created_at.desc())
        )
        return list(result.scalars())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(Resume.id)).where(Resume.user_id == user_id)
        )
        return int(result.scalar_one())

    async def find_duplicate(self, user_id: uuid.UUID, sha256: str) -> Resume | None:
        result = await self.session.execute(
            select(Resume).where(Resume.user_id == user_id, Resume.sha256 == sha256).limit(1)
        )
        return result.scalar_one_or_none()

    async def clear_default(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Resume)
            .where(Resume.user_id == user_id, Resume.is_default.is_(True))
            .values(is_default=False)
        )

    async def newest_for_user(self, user_id: uuid.UUID) -> Resume | None:
        result = await self.session.execute(
            select(Resume)
            .where(Resume.user_id == user_id)
            .order_by(Resume.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
