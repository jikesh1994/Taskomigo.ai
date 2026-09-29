"""Profile aggregate data access.

Every query for a child row joins back to the profile's owner, so a caller can
never read or modify another user's data by guessing an ID.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.education import Education
from app.models.experience import Experience
from app.models.profile import ProfessionalProfile
from app.models.skill import Skill


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_user(
        self, user_id: uuid.UUID, *, with_children: bool = False
    ) -> ProfessionalProfile | None:
        stmt = select(ProfessionalProfile).where(ProfessionalProfile.user_id == user_id)
        if with_children:
            stmt = stmt.options(
                selectinload(ProfessionalProfile.experiences),
                selectinload(ProfessionalProfile.education),
                selectinload(ProfessionalProfile.skills),
            )
        # populate_existing refreshes collections already in the identity map.
        result = await self.session.execute(stmt.execution_options(populate_existing=True))
        return result.scalar_one_or_none()

    def add(self, obj: ProfessionalProfile | Experience | Education | Skill) -> None:
        self.session.add(obj)

    async def delete(self, obj: Experience | Education | Skill) -> None:
        await self.session.delete(obj)

    async def get_experience(
        self, user_id: uuid.UUID, experience_id: uuid.UUID
    ) -> Experience | None:
        result = await self.session.execute(
            select(Experience)
            .join(ProfessionalProfile, Experience.profile_id == ProfessionalProfile.id)
            .where(Experience.id == experience_id, ProfessionalProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_experiences(self, user_id: uuid.UUID) -> list[Experience]:
        result = await self.session.execute(
            select(Experience)
            .join(ProfessionalProfile, Experience.profile_id == ProfessionalProfile.id)
            .where(ProfessionalProfile.user_id == user_id)
            .order_by(Experience.start_date.desc())
        )
        return list(result.scalars())

    async def get_education(self, user_id: uuid.UUID, education_id: uuid.UUID) -> Education | None:
        result = await self.session.execute(
            select(Education)
            .join(ProfessionalProfile, Education.profile_id == ProfessionalProfile.id)
            .where(Education.id == education_id, ProfessionalProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_education(self, user_id: uuid.UUID) -> list[Education]:
        result = await self.session.execute(
            select(Education)
            .join(ProfessionalProfile, Education.profile_id == ProfessionalProfile.id)
            .where(ProfessionalProfile.user_id == user_id)
            .order_by(Education.start_date.desc())
        )
        return list(result.scalars())

    async def get_skill(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> Skill | None:
        result = await self.session.execute(
            select(Skill)
            .join(ProfessionalProfile, Skill.profile_id == ProfessionalProfile.id)
            .where(Skill.id == skill_id, ProfessionalProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_skills(self, user_id: uuid.UUID) -> list[Skill]:
        result = await self.session.execute(
            select(Skill)
            .join(ProfessionalProfile, Skill.profile_id == ProfessionalProfile.id)
            .where(ProfessionalProfile.user_id == user_id)
            .order_by(Skill.normalized_name)
        )
        return list(result.scalars())

    async def skill_name_taken(
        self, profile_id: uuid.UUID, normalized_name: str, *, exclude_id: uuid.UUID | None = None
    ) -> bool:
        stmt = select(Skill.id).where(
            Skill.profile_id == profile_id, Skill.normalized_name == normalized_name
        )
        if exclude_id is not None:
            stmt = stmt.where(Skill.id != exclude_id)
        return (await self.session.execute(stmt)).first() is not None
