from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preferences import JobPreferences


class PreferencesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_user(self, user_id: uuid.UUID) -> JobPreferences | None:
        result = await self.session.execute(
            select(JobPreferences).where(JobPreferences.user_id == user_id)
        )
        return result.scalar_one_or_none()

    def add(self, preferences: JobPreferences) -> None:
        self.session.add(preferences)
