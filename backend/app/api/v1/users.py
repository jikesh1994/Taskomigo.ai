from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, RequestContextDep, UserServiceDep
from app.schemas.auth import ChangePasswordRequest
from app.schemas.common import AUTH_RESPONSES, VALIDATION_RESPONSES, ErrorResponse
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"], responses=AUTH_RESPONSES)


@router.get("/me", response_model=UserRead, summary="Get the signed-in user")
async def get_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update personal information",
    responses=VALIDATION_RESPONSES,
)
async def update_me(
    data: UserUpdate, user: CurrentUser, service: UserServiceDep, ctx: RequestContextDep
) -> UserRead:
    return UserRead.model_validate(await service.update_me(user, data, ctx))


@router.post(
    "/me/onboarding/complete",
    response_model=UserRead,
    summary="Mark onboarding as complete",
    description="Idempotent. Calling it again keeps the original completion time.",
)
async def complete_onboarding(
    user: CurrentUser, service: UserServiceDep, ctx: RequestContextDep
) -> UserRead:
    return UserRead.model_validate(await service.complete_onboarding(user, ctx))


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Change password (signs out all sessions)",
    responses={
        400: {"model": ErrorResponse, "description": "Current password incorrect"},
        **VALIDATION_RESPONSES,
    },
)
async def change_password(
    data: ChangePasswordRequest, user: CurrentUser, service: UserServiceDep, ctx: RequestContextDep
) -> Response:
    await service.change_password(user, data, ctx)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
