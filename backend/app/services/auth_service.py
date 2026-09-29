"""Registration, login, refresh-token rotation and logout."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import NoReturn

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, ConflictError, RateLimitedError
from app.core.login_throttle import LoginThrottle
from app.core.security import (
    burn_password_check,
    create_access_token,
    ensure_aware,
    generate_refresh_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    utc_now,
    verify_password,
)
from app.models.enums import AuditResult
from app.models.preferences import JobPreferences
from app.models.profile import ProfessionalProfile
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.audit_service import AuditService, RequestContext
from app.services.validation import ensure_password_policy

INVALID_CREDENTIALS_MESSAGE = "Invalid email or password."


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int
    refresh_expires_at: datetime


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: User
    tokens: IssuedTokens


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        login_throttle: LoginThrottle | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.login_throttle = login_throttle
        self.users = UserRepository(session)
        self.tokens = RefreshTokenRepository(session)
        self.audit = AuditService(session)

    # ------------------------------------------------------------------ register

    async def register(self, data: RegisterRequest, ctx: RequestContext) -> AuthResult:
        ensure_password_policy(data.password, self.settings)
        if await self.users.email_exists(data.email):
            raise ConflictError("An account with this email already exists.", code="email_taken")

        user = User(
            id=uuid.uuid4(),
            email=data.email,
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            timezone=data.timezone,
        )
        self.users.add(user)
        self.session.add(ProfessionalProfile(user_id=user.id))
        self.session.add(JobPreferences(user_id=user.id))
        try:
            await self.session.flush()
        except IntegrityError as exc:  # concurrent registration with the same email
            await self.session.rollback()
            raise ConflictError(
                "An account with this email already exists.", code="email_taken"
            ) from exc

        tokens = self._issue_tokens(user, ctx)
        self.audit.record(
            "auth.register", user_id=user.id, entity="user", entity_id=user.id, context=ctx
        )
        await self.session.commit()
        return AuthResult(user=user, tokens=tokens)

    # ------------------------------------------------------------------ login

    async def login(self, data: LoginRequest, ctx: RequestContext) -> AuthResult:
        # Checked before the password so a throttled account gives no password oracle.
        await self._ensure_login_allowed(data.email, ctx)
        user = await self.users.get_by_email(data.email)
        if user is None:
            burn_password_check(data.password)
            await self._fail_login(data.email, None, ctx, reason="unknown_email")
        if not verify_password(data.password, user.password_hash):
            await self._fail_login(data.email, user.id, ctx, reason="bad_password")
        if not user.is_active:
            await self._fail_login(data.email, user.id, ctx, reason="inactive_user")

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(data.password)
        user.last_login_at = utc_now()
        tokens = self._issue_tokens(user, ctx)
        self.audit.record(
            "auth.login", user_id=user.id, entity="user", entity_id=user.id, context=ctx
        )
        await self.session.commit()
        if self.login_throttle is not None:
            await self.login_throttle.reset(data.email)
        return AuthResult(user=user, tokens=tokens)

    async def _ensure_login_allowed(self, email: str, ctx: RequestContext) -> None:
        if self.login_throttle is None:
            return
        try:
            await self.login_throttle.ensure_allowed(email)
        except RateLimitedError:
            self.audit.record(
                "auth.login",
                result=AuditResult.FAILURE,
                context=ctx,
                details={"reason": "account_throttled"},
            )
            await self.session.commit()
            raise

    async def _fail_login(
        self, email: str, user_id: uuid.UUID | None, ctx: RequestContext, *, reason: str
    ) -> NoReturn:
        if self.login_throttle is not None:
            await self.login_throttle.record_failure(email)
        self.audit.record(
            "auth.login",
            result=AuditResult.FAILURE,
            user_id=user_id,
            context=ctx,
            details={"reason": reason},
        )
        await self.session.commit()
        # Same message for every reason so accounts cannot be enumerated.
        raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE, code="invalid_credentials")

    # ------------------------------------------------------------------ refresh

    async def refresh(self, raw_token: str | None, ctx: RequestContext) -> AuthResult:
        if not raw_token:
            raise AuthenticationError("Refresh token is required.", code="invalid_refresh_token")
        current = await self.tokens.get_by_hash(hash_token(raw_token))
        if current is None:
            raise AuthenticationError("Invalid refresh token.", code="invalid_refresh_token")

        now = utc_now()
        if current.revoked_at is not None:
            await self._handle_reuse(current, ctx, now)
        if ensure_aware(current.expires_at) <= now:
            raise AuthenticationError("Refresh token has expired.", code="refresh_token_expired")

        user = await self.users.get_by_id(current.user_id)
        if user is None or not user.is_active:
            await self.tokens.revoke_family(current.family_id, now)
            await self.session.commit()
            raise AuthenticationError("Invalid refresh token.", code="invalid_refresh_token")

        new_id = uuid.uuid4()
        # Atomic compare-and-set: exactly one concurrent request can rotate a token.
        if not await self.tokens.mark_rotated(current.id, now, replaced_by_id=new_id):
            await self._handle_reuse(current, ctx, now)

        tokens = self._issue_tokens(user, ctx, family_id=current.family_id, token_id=new_id)
        await self.session.commit()
        return AuthResult(user=user, tokens=tokens)

    async def _handle_reuse(
        self, token: RefreshToken, ctx: RequestContext, now: datetime
    ) -> NoReturn:
        """A rotated token was presented again: assume theft, revoke the whole session."""
        await self.tokens.revoke_family(token.family_id, now)
        self.audit.record(
            "auth.refresh_token_reuse",
            result=AuditResult.FAILURE,
            user_id=token.user_id,
            entity="refresh_token_family",
            entity_id=token.family_id,
            context=ctx,
        )
        await self.session.commit()
        raise AuthenticationError(
            "Refresh token has already been used. Please sign in again.",
            code="refresh_token_reused",
        )

    # ------------------------------------------------------------------ logout

    async def logout(self, raw_token: str | None, ctx: RequestContext) -> None:
        """Revoke the session that owns this refresh token. Idempotent."""
        if not raw_token:
            return
        token = await self.tokens.get_by_hash(hash_token(raw_token))
        if token is None:
            return
        await self.tokens.revoke_family(token.family_id, utc_now())
        self.audit.record("auth.logout", user_id=token.user_id, context=ctx)
        await self.session.commit()

    # ------------------------------------------------------------------ helpers

    def _issue_tokens(
        self,
        user: User,
        ctx: RequestContext,
        *,
        family_id: uuid.UUID | None = None,
        token_id: uuid.UUID | None = None,
    ) -> IssuedTokens:
        access_token, expires_in = create_access_token(user.id, user.role.value, self.settings)
        raw_refresh = generate_refresh_token()
        refresh_expires_at = utc_now() + timedelta(days=self.settings.refresh_token_ttl_days)
        self.tokens.add(
            RefreshToken(
                id=token_id or uuid.uuid4(),
                user_id=user.id,
                token_hash=hash_token(raw_refresh),
                family_id=family_id or uuid.uuid4(),
                expires_at=refresh_expires_at,
                user_agent=(ctx.user_agent or "")[:255] or None,
            )
        )
        return IssuedTokens(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=expires_in,
            refresh_expires_at=refresh_expires_at,
        )
