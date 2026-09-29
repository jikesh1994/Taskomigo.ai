from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, ProfileServiceDep, RequestContextDep
from app.schemas.common import (
    AUTH_RESPONSES,
    NOT_FOUND_RESPONSES,
    VALIDATION_RESPONSES,
    ErrorResponse,
)
from app.schemas.profile import (
    EducationCreate,
    EducationRead,
    EducationUpdate,
    ExperienceCreate,
    ExperienceRead,
    ExperienceUpdate,
    ProfileRead,
    ProfileReplace,
    ProfileUpdate,
    SkillCreate,
    SkillRead,
    SkillUpdate,
)

router = APIRouter(prefix="/profile", tags=["profile"], responses=AUTH_RESPONSES)

_ITEM_RESPONSES = {**NOT_FOUND_RESPONSES, **VALIDATION_RESPONSES}


# ------------------------------------------------------------------ profile


@router.get("", response_model=ProfileRead, summary="Get the full professional profile")
async def get_profile(user: CurrentUser, service: ProfileServiceDep) -> ProfileRead:
    return ProfileRead.model_validate(await service.get_profile(user.id))


@router.put(
    "",
    response_model=ProfileRead,
    summary="Replace profile fields",
    description="Replaces every profile field. Omitted fields reset to defaults. "
    "Experience, education and skills are managed through their own endpoints.",
    responses=VALIDATION_RESPONSES,
)
async def replace_profile(
    data: ProfileReplace, user: CurrentUser, service: ProfileServiceDep, ctx: RequestContextDep
) -> ProfileRead:
    return ProfileRead.model_validate(await service.replace_profile(user.id, data, ctx))


@router.patch(
    "",
    response_model=ProfileRead,
    summary="Partially update profile fields",
    responses=VALIDATION_RESPONSES,
)
async def update_profile(
    data: ProfileUpdate, user: CurrentUser, service: ProfileServiceDep, ctx: RequestContextDep
) -> ProfileRead:
    return ProfileRead.model_validate(await service.update_profile(user.id, data, ctx))


# ------------------------------------------------------------------ experience


@router.get("/experiences", response_model=list[ExperienceRead], summary="List work experience")
async def list_experiences(user: CurrentUser, service: ProfileServiceDep) -> list[ExperienceRead]:
    return [ExperienceRead.model_validate(e) for e in await service.list_experiences(user.id)]


@router.post(
    "/experiences",
    response_model=ExperienceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add work experience",
    responses=VALIDATION_RESPONSES,
)
async def add_experience(
    data: ExperienceCreate, user: CurrentUser, service: ProfileServiceDep
) -> ExperienceRead:
    return ExperienceRead.model_validate(await service.add_experience(user.id, data))


@router.patch(
    "/experiences/{experience_id}",
    response_model=ExperienceRead,
    summary="Update work experience",
    responses=_ITEM_RESPONSES,
)
async def update_experience(
    experience_id: uuid.UUID, data: ExperienceUpdate, user: CurrentUser, service: ProfileServiceDep
) -> ExperienceRead:
    return ExperienceRead.model_validate(
        await service.update_experience(user.id, experience_id, data)
    )


@router.delete(
    "/experiences/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete work experience",
    responses=NOT_FOUND_RESPONSES,
)
async def delete_experience(
    experience_id: uuid.UUID, user: CurrentUser, service: ProfileServiceDep
) -> Response:
    await service.delete_experience(user.id, experience_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ education


@router.get("/education", response_model=list[EducationRead], summary="List education")
async def list_education(user: CurrentUser, service: ProfileServiceDep) -> list[EducationRead]:
    return [EducationRead.model_validate(e) for e in await service.list_education(user.id)]


@router.post(
    "/education",
    response_model=EducationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add education",
    responses=VALIDATION_RESPONSES,
)
async def add_education(
    data: EducationCreate, user: CurrentUser, service: ProfileServiceDep
) -> EducationRead:
    return EducationRead.model_validate(await service.add_education(user.id, data))


@router.patch(
    "/education/{education_id}",
    response_model=EducationRead,
    summary="Update education",
    responses=_ITEM_RESPONSES,
)
async def update_education(
    education_id: uuid.UUID, data: EducationUpdate, user: CurrentUser, service: ProfileServiceDep
) -> EducationRead:
    return EducationRead.model_validate(await service.update_education(user.id, education_id, data))


@router.delete(
    "/education/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete education",
    responses=NOT_FOUND_RESPONSES,
)
async def delete_education(
    education_id: uuid.UUID, user: CurrentUser, service: ProfileServiceDep
) -> Response:
    await service.delete_education(user.id, education_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ skills

_SKILL_CONFLICT = {409: {"model": ErrorResponse, "description": "Skill already exists"}}


@router.get("/skills", response_model=list[SkillRead], summary="List skills")
async def list_skills(user: CurrentUser, service: ProfileServiceDep) -> list[SkillRead]:
    return [SkillRead.model_validate(s) for s in await service.list_skills(user.id)]


@router.post(
    "/skills",
    response_model=SkillRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a skill",
    responses={**VALIDATION_RESPONSES, **_SKILL_CONFLICT},
)
async def add_skill(data: SkillCreate, user: CurrentUser, service: ProfileServiceDep) -> SkillRead:
    return SkillRead.model_validate(await service.add_skill(user.id, data))


@router.patch(
    "/skills/{skill_id}",
    response_model=SkillRead,
    summary="Update a skill",
    responses={**_ITEM_RESPONSES, **_SKILL_CONFLICT},
)
async def update_skill(
    skill_id: uuid.UUID, data: SkillUpdate, user: CurrentUser, service: ProfileServiceDep
) -> SkillRead:
    return SkillRead.model_validate(await service.update_skill(user.id, skill_id, data))


@router.delete(
    "/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a skill",
    responses=NOT_FOUND_RESPONSES,
)
async def delete_skill(
    skill_id: uuid.UUID, user: CurrentUser, service: ProfileServiceDep
) -> Response:
    await service.delete_skill(user.id, skill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
