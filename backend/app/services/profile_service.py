"""Professional profile aggregate: profile fields, experience, education, skills."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.education import Education
from app.models.experience import Experience
from app.models.profile import ProfessionalProfile
from app.models.skill import Skill
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import (
    EducationCreate,
    EducationUpdate,
    ExperienceCreate,
    ExperienceUpdate,
    ProfileReplace,
    ProfileUpdate,
    SkillCreate,
    SkillUpdate,
    validate_education_dates,
    validate_experience_dates,
    validate_salary_expectation,
)
from app.services.audit_service import AuditService, RequestContext
from app.services.validation import run_invariant


def normalize_skill_name(name: str) -> str:
    return " ".join(name.split()).casefold()


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProfileRepository(session)
        self.audit = AuditService(session)

    # ------------------------------------------------------------------ profile

    async def get_profile(self, user_id: uuid.UUID) -> ProfessionalProfile:
        profile = await self.repo.get_for_user(user_id, with_children=True)
        if profile is None:
            await self._create_profile(user_id)
            await self.session.commit()
            profile = await self.repo.get_for_user(user_id, with_children=True)
        assert profile is not None
        return profile

    async def replace_profile(
        self, user_id: uuid.UUID, data: ProfileReplace, ctx: RequestContext
    ) -> ProfessionalProfile:
        profile = await self._get_or_create(user_id)
        values = data.model_dump()
        for field, value in values.items():
            setattr(profile, field, value)
        self._audit_profile_change(user_id, profile.id, sorted(values), ctx)
        await self.session.commit()
        return await self.get_profile(user_id)

    async def update_profile(
        self, user_id: uuid.UUID, data: ProfileUpdate, ctx: RequestContext
    ) -> ProfessionalProfile:
        profile = await self._get_or_create(user_id)
        changes = data.changes()
        run_invariant(
            validate_salary_expectation,
            changes.get("expected_salary_min", profile.expected_salary_min),
            changes.get("expected_salary_max", profile.expected_salary_max),
            changes.get("currency", profile.currency),
            field="expected_salary",
        )
        for field, value in changes.items():
            setattr(profile, field, value)
        if changes:
            self._audit_profile_change(user_id, profile.id, sorted(changes), ctx)
            await self.session.commit()
        return await self.get_profile(user_id)

    # ------------------------------------------------------------------ experience

    async def list_experiences(self, user_id: uuid.UUID) -> list[Experience]:
        return await self.repo.list_experiences(user_id)

    async def add_experience(self, user_id: uuid.UUID, data: ExperienceCreate) -> Experience:
        profile = await self._get_or_create(user_id)
        experience = Experience(profile_id=profile.id, **data.model_dump())
        self.repo.add(experience)
        await self.session.commit()
        return experience

    async def update_experience(
        self, user_id: uuid.UUID, experience_id: uuid.UUID, data: ExperienceUpdate
    ) -> Experience:
        experience = await self.repo.get_experience(user_id, experience_id)
        if experience is None:
            raise NotFoundError("Experience not found.")
        changes = data.changes()
        # Marking a role as current implicitly clears its end date.
        if changes.get("is_current") and "end_date" not in changes:
            changes["end_date"] = None
        run_invariant(
            validate_experience_dates,
            changes.get("start_date", experience.start_date),
            changes.get("end_date", experience.end_date),
            changes.get("is_current", experience.is_current),
            field="dates",
        )
        for field, value in changes.items():
            setattr(experience, field, value)
        await self.session.commit()
        return experience

    async def delete_experience(self, user_id: uuid.UUID, experience_id: uuid.UUID) -> None:
        experience = await self.repo.get_experience(user_id, experience_id)
        if experience is None:
            raise NotFoundError("Experience not found.")
        await self.repo.delete(experience)
        await self.session.commit()

    # ------------------------------------------------------------------ education

    async def list_education(self, user_id: uuid.UUID) -> list[Education]:
        return await self.repo.list_education(user_id)

    async def add_education(self, user_id: uuid.UUID, data: EducationCreate) -> Education:
        profile = await self._get_or_create(user_id)
        education = Education(profile_id=profile.id, **data.model_dump())
        self.repo.add(education)
        await self.session.commit()
        return education

    async def update_education(
        self, user_id: uuid.UUID, education_id: uuid.UUID, data: EducationUpdate
    ) -> Education:
        education = await self.repo.get_education(user_id, education_id)
        if education is None:
            raise NotFoundError("Education entry not found.")
        changes = data.changes()
        run_invariant(
            validate_education_dates,
            changes.get("start_date", education.start_date),
            changes.get("end_date", education.end_date),
            field="dates",
        )
        for field, value in changes.items():
            setattr(education, field, value)
        await self.session.commit()
        return education

    async def delete_education(self, user_id: uuid.UUID, education_id: uuid.UUID) -> None:
        education = await self.repo.get_education(user_id, education_id)
        if education is None:
            raise NotFoundError("Education entry not found.")
        await self.repo.delete(education)
        await self.session.commit()

    # ------------------------------------------------------------------ skills

    async def list_skills(self, user_id: uuid.UUID) -> list[Skill]:
        return await self.repo.list_skills(user_id)

    async def add_skill(self, user_id: uuid.UUID, data: SkillCreate) -> Skill:
        profile = await self._get_or_create(user_id)
        normalized = normalize_skill_name(data.name)
        if await self.repo.skill_name_taken(profile.id, normalized):
            raise ConflictError(f"Skill '{data.name}' already exists.", code="skill_exists")
        skill = Skill(profile_id=profile.id, normalized_name=normalized, **data.model_dump())
        self.repo.add(skill)
        await self._commit_skill()
        return skill

    async def update_skill(
        self, user_id: uuid.UUID, skill_id: uuid.UUID, data: SkillUpdate
    ) -> Skill:
        skill = await self.repo.get_skill(user_id, skill_id)
        if skill is None:
            raise NotFoundError("Skill not found.")
        changes = data.changes()
        if "name" in changes:
            normalized = normalize_skill_name(changes["name"])
            if await self.repo.skill_name_taken(skill.profile_id, normalized, exclude_id=skill.id):
                raise ConflictError(
                    f"Skill '{changes['name']}' already exists.", code="skill_exists"
                )
            skill.normalized_name = normalized
        for field, value in changes.items():
            setattr(skill, field, value)
        await self._commit_skill()
        return skill

    async def delete_skill(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> None:
        skill = await self.repo.get_skill(user_id, skill_id)
        if skill is None:
            raise NotFoundError("Skill not found.")
        await self.repo.delete(skill)
        await self.session.commit()

    # ------------------------------------------------------------------ helpers

    async def _get_or_create(self, user_id: uuid.UUID) -> ProfessionalProfile:
        profile = await self.repo.get_for_user(user_id)
        return profile if profile is not None else await self._create_profile(user_id)

    async def _create_profile(self, user_id: uuid.UUID) -> ProfessionalProfile:
        profile = ProfessionalProfile(id=uuid.uuid4(), user_id=user_id)
        self.repo.add(profile)
        await self.session.flush()
        return profile

    async def _commit_skill(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:  # concurrent insert of the same skill
            await self.session.rollback()
            raise ConflictError("Skill already exists.", code="skill_exists") from exc

    def _audit_profile_change(
        self, user_id: uuid.UUID, profile_id: uuid.UUID, fields: list[str], ctx: RequestContext
    ) -> None:
        # Record which fields changed, never their values (they may be personal data).
        self.audit.record(
            "profile.update",
            user_id=user_id,
            entity="professional_profile",
            entity_id=profile_id,
            context=ctx,
            details={"fields": fields},
        )
