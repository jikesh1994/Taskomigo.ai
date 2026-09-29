from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, PreferenceServiceDep, RequestContextDep
from app.schemas.common import AUTH_RESPONSES, VALIDATION_RESPONSES
from app.schemas.preferences import PreferencesRead, PreferencesReplace, PreferencesUpdate

router = APIRouter(prefix="/preferences", tags=["preferences"], responses=AUTH_RESPONSES)


@router.get("", response_model=PreferencesRead, summary="Get job-search and agent preferences")
async def get_preferences(user: CurrentUser, service: PreferenceServiceDep) -> PreferencesRead:
    return PreferencesRead.model_validate(await service.get(user.id))


@router.put(
    "",
    response_model=PreferencesRead,
    summary="Replace preferences",
    description="`auto_submit_enabled` requires `review_before_submit=false`. Limits are "
    "capped by platform-wide maximums. Sensitive or legal steps always require explicit "
    "approval, whatever these settings say.",
    responses=VALIDATION_RESPONSES,
)
async def replace_preferences(
    data: PreferencesReplace,
    user: CurrentUser,
    service: PreferenceServiceDep,
    ctx: RequestContextDep,
) -> PreferencesRead:
    return PreferencesRead.model_validate(await service.replace(user.id, data, ctx))


@router.patch(
    "",
    response_model=PreferencesRead,
    summary="Partially update preferences",
    responses=VALIDATION_RESPONSES,
)
async def update_preferences(
    data: PreferencesUpdate,
    user: CurrentUser,
    service: PreferenceServiceDep,
    ctx: RequestContextDep,
) -> PreferencesRead:
    return PreferencesRead.model_validate(await service.update(user.id, data, ctx))
