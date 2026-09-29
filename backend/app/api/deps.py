"""FastAPI dependencies: settings, DB session, Redis, auth, rate limits, services."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError, RateLimitedError
from app.core.logging import get_logger
from app.core.login_throttle import LoginThrottle
from app.core.rate_limit import RateLimiter
from app.core.security import decode_access_token
from app.jobs.providers import JobSearchProvider
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import RequestContext
from app.services.auth_service import AuthService
from app.services.job_dispatch import JobDispatcher
from app.services.job_match_service import JobMatchService
from app.services.job_search_service import JobSearchService
from app.services.job_service import JobService
from app.services.job_source_service import JobSourceService
from app.services.preference_service import PreferenceService
from app.services.profile_service import ProfileService
from app.services.resume_dispatch import ParseDispatcher
from app.services.resume_review_service import ResumeReviewService
from app.services.resume_service import ResumeService
from app.services.user_service import UserService
from app.storage import ObjectStorage

logger = get_logger(__name__)

_bearer = HTTPBearer(auto_error=False, description="JWT access token from /auth/login")


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Request-scoped session. Services commit explicitly; anything uncommitted is
    rolled back when the request ends (including on errors)."""
    async with request.app.state.db.session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_client_ip(request: Request) -> str | None:
    # Behind a proxy, run uvicorn with --proxy-headers/--forwarded-allow-ips so
    # request.client reflects the real client.
    return request.client.host if request.client else None


def get_request_context(request: Request) -> RequestContext:
    return RequestContext(
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]


async def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Not authenticated.", code="not_authenticated")
    payload = decode_access_token(credentials.credentials, settings)
    user = await UserRepository(session).get_by_id(payload.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Invalid access token.", code="invalid_token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    async def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise PermissionDeniedError()
        return user

    return dependency


def rate_limit(bucket: str) -> Callable[..., Awaitable[None]]:
    """Per-client-IP fixed-window limit using the auth rate-limit settings."""

    async def dependency(request: Request, redis: RedisDep, settings: SettingsDep) -> None:
        limiter = RateLimiter(redis)
        identifier = get_client_ip(request) or "unknown"
        result = await limiter.hit(
            bucket,
            identifier,
            limit=settings.rate_limit_auth_requests,
            window_seconds=settings.rate_limit_auth_window_seconds,
        )
        if not result.allowed:
            logger.warning("rate_limited", bucket=bucket, client_ip=identifier)
            raise RateLimitedError(headers={"Retry-After": str(result.retry_after_seconds)})

    return dependency


def get_auth_service(session: SessionDep, settings: SettingsDep, redis: RedisDep) -> AuthService:
    throttle = LoginThrottle(
        redis,
        max_failures=settings.login_max_failures_per_account,
        window_seconds=settings.login_failure_window_seconds,
    )
    return AuthService(session, settings, throttle)


def get_user_service(session: SessionDep, settings: SettingsDep) -> UserService:
    return UserService(session, settings)


def get_profile_service(session: SessionDep) -> ProfileService:
    return ProfileService(session)


def get_preference_service(session: SessionDep, settings: SettingsDep) -> PreferenceService:
    return PreferenceService(session, settings)


def get_storage(request: Request) -> ObjectStorage:
    return request.app.state.storage


def get_parse_dispatcher(request: Request) -> ParseDispatcher:
    return request.app.state.parse_dispatcher


def get_resume_service(
    session: SessionDep,
    settings: SettingsDep,
    storage: Annotated[ObjectStorage, Depends(get_storage)],
) -> ResumeService:
    return ResumeService(session, settings, storage)


ResumeServiceDep = Annotated[ResumeService, Depends(get_resume_service)]


def get_resume_review_service(
    session: SessionDep, resumes: ResumeServiceDep
) -> ResumeReviewService:
    return ResumeReviewService(session, resumes)


ParseDispatcherDep = Annotated[ParseDispatcher, Depends(get_parse_dispatcher)]
ResumeReviewServiceDep = Annotated[ResumeReviewService, Depends(get_resume_review_service)]

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
PreferenceServiceDep = Annotated[PreferenceService, Depends(get_preference_service)]


def get_job_providers(request: Request) -> dict[str, JobSearchProvider]:
    return request.app.state.job_providers


def get_job_dispatcher(request: Request) -> JobDispatcher:
    return request.app.state.job_dispatcher


def get_job_source_service(
    session: SessionDep,
    settings: SettingsDep,
    providers: Annotated[dict[str, JobSearchProvider], Depends(get_job_providers)],
) -> JobSourceService:
    return JobSourceService(session, settings, providers)


def get_job_search_service(session: SessionDep) -> JobSearchService:
    return JobSearchService(session)


def get_job_match_service(session: SessionDep) -> JobMatchService:
    return JobMatchService(session)


def get_job_service(session: SessionDep) -> JobService:
    return JobService(session)


JobDispatcherDep = Annotated[JobDispatcher, Depends(get_job_dispatcher)]
JobSourceServiceDep = Annotated[JobSourceService, Depends(get_job_source_service)]
JobSearchServiceDep = Annotated[JobSearchService, Depends(get_job_search_service)]
JobMatchServiceDep = Annotated[JobMatchService, Depends(get_job_match_service)]
JobServiceDep = Annotated[JobService, Depends(get_job_service)]
