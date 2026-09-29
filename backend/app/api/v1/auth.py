from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status

from app.api.deps import AuthServiceDep, RequestContextDep, SettingsDep, rate_limit
from app.core.config import Settings
from app.schemas.auth import AuthResponse, LoginRequest, RefreshRequest, RegisterRequest
from app.schemas.common import ErrorResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthResult

router = APIRouter(prefix="/auth", tags=["auth"])

_RATE_LIMITED = {
    429: {
        "model": ErrorResponse,
        "description": "Too many requests from this client (`rate_limited`) or, on login, "
        "too many failed attempts for this account (`login_throttled`)",
    }
}
_UNAUTHORIZED = {401: {"model": ErrorResponse, "description": "Invalid credentials or token"}}


def _set_refresh_cookie(response: Response, settings: Settings, result: AuthResult) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=result.tokens.refresh_token,
        expires=result.tokens.refresh_expires_at,
        httponly=True,
        secure=settings.is_production,
        samesite="strict",
        path=f"{settings.api_v1_prefix}/auth",
    )


def _to_response(result: AuthResult) -> AuthResponse:
    return AuthResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=result.tokens.expires_in,
        refresh_expires_at=result.tokens.refresh_expires_at,
        user=UserRead.model_validate(result.user),
    )


def _refresh_token_from(
    request: Request, body: RefreshRequest | None, settings: Settings
) -> str | None:
    if body is not None and body.refresh_token:
        return body.refresh_token
    return request.cookies.get(settings.refresh_cookie_name)


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    description="Creates the user with an empty profile and default job preferences, "
    "then signs them in.",
    responses={
        409: {"model": ErrorResponse, "description": "Email already registered"},
        **_RATE_LIMITED,
    },
    dependencies=[Depends(rate_limit("auth:register"))],
)
async def register(
    data: RegisterRequest,
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
    ctx: RequestContextDep,
) -> AuthResponse:
    result = await service.register(data, ctx)
    _set_refresh_cookie(response, settings, result)
    return _to_response(result)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Sign in with email and password",
    responses={**_UNAUTHORIZED, **_RATE_LIMITED},
    dependencies=[Depends(rate_limit("auth:login"))],
)
async def login(
    data: LoginRequest,
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
    ctx: RequestContextDep,
) -> AuthResponse:
    result = await service.login(data, ctx)
    _set_refresh_cookie(response, settings, result)
    return _to_response(result)


@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Rotate the refresh token and issue a new access token",
    description="Accepts the refresh token in the body or in the httpOnly cookie. Each "
    "refresh token works once. Reusing one revokes the whole session.",
    responses={**_UNAUTHORIZED, **_RATE_LIMITED},
    dependencies=[Depends(rate_limit("auth:refresh"))],
)
async def refresh(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    settings: SettingsDep,
    ctx: RequestContextDep,
    body: Annotated[RefreshRequest | None, Body()] = None,
) -> AuthResponse:
    result = await service.refresh(_refresh_token_from(request, body, settings), ctx)
    _set_refresh_cookie(response, settings, result)
    return _to_response(result)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current session",
    response_class=Response,
)
async def logout(
    request: Request,
    service: AuthServiceDep,
    settings: SettingsDep,
    ctx: RequestContextDep,
    body: Annotated[RefreshRequest | None, Body()] = None,
) -> Response:
    await service.logout(_refresh_token_from(request, body, settings), ctx)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.refresh_cookie_name, path=f"{settings.api_v1_prefix}/auth")
    return response
