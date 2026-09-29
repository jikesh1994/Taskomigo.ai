from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError, DomainValidationError
from app.core.security import hash_password, utc_now, verify_password
from app.models.user import User
from app.repositories.token_repository import RefreshTokenRepository
from app.schemas.auth import ChangePasswordRequest
from app.schemas.user import UserUpdate
from app.services.audit_service import AuditService, RequestContext
from app.services.validation import ensure_password_policy


class InvalidCurrentPasswordError(AppError):
    status_code = 400
    code = "invalid_current_password"
    default_message = "Current password is incorrect."


class UserService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.tokens = RefreshTokenRepository(session)
        self.audit = AuditService(session)

    async def update_me(self, user: User, data: UserUpdate, ctx: RequestContext) -> User:
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(user, field, value)
        if changes:
            self.audit.record(
                "user.update",
                user_id=user.id,
                entity="user",
                entity_id=user.id,
                context=ctx,
                details={"fields": sorted(changes)},
            )
            await self.session.commit()
        return user

    async def complete_onboarding(self, user: User, ctx: RequestContext) -> User:
        """Idempotent: the first completion time is kept."""
        if user.onboarding_completed_at is None:
            user.onboarding_completed_at = utc_now()
            self.audit.record(
                "user.onboarding_complete",
                user_id=user.id,
                entity="user",
                entity_id=user.id,
                context=ctx,
            )
            await self.session.commit()
        return user

    async def change_password(
        self, user: User, data: ChangePasswordRequest, ctx: RequestContext
    ) -> None:
        if not verify_password(data.current_password, user.password_hash):
            raise InvalidCurrentPasswordError()
        ensure_password_policy(data.new_password, self.settings, field="new_password")
        if data.new_password == data.current_password:
            raise DomainValidationError("New password must differ from the current password.")

        user.password_hash = hash_password(data.new_password)
        # Sign out every other session.
        await self.tokens.revoke_all_for_user(user.id, utc_now())
        self.audit.record(
            "user.password_change", user_id=user.id, entity="user", entity_id=user.id, context=ctx
        )
        await self.session.commit()
