from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import DomainValidationError
from app.models.preferences import JobPreferences
from app.repositories.preferences_repository import PreferencesRepository
from app.schemas.preferences import (
    PreferencesReplace,
    PreferencesUpdate,
    check_preference_consistency,
)
from app.services.audit_service import AuditService, RequestContext
from app.services.validation import run_invariant

# Changes to these settings alter how autonomously the agent acts, so they are audited
# with their new values.
_AUTONOMY_FIELDS = frozenset(
    {"auto_fill_enabled", "auto_answer_enabled", "review_before_submit", "auto_submit_enabled"}
)


class PreferenceService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.repo = PreferencesRepository(session)
        self.audit = AuditService(session)

    async def get(self, user_id: uuid.UUID) -> JobPreferences:
        preferences = await self.repo.get_for_user(user_id)
        if preferences is None:
            preferences = JobPreferences(id=uuid.uuid4(), user_id=user_id)
            self.repo.add(preferences)
            await self.session.commit()
        return preferences

    async def replace(
        self, user_id: uuid.UUID, data: PreferencesReplace, ctx: RequestContext
    ) -> JobPreferences:
        return await self._apply(user_id, data.model_dump(mode="json"), ctx)

    async def update(
        self, user_id: uuid.UUID, data: PreferencesUpdate, ctx: RequestContext
    ) -> JobPreferences:
        return await self._apply(user_id, data.model_dump(mode="json", exclude_unset=True), ctx)

    async def _apply(
        self, user_id: uuid.UUID, changes: dict[str, Any], ctx: RequestContext
    ) -> JobPreferences:
        preferences = await self.get(user_id)
        merged = {
            field: changes.get(field, getattr(preferences, field))
            for field in (
                "min_salary",
                "salary_currency",
                "review_before_submit",
                "auto_submit_enabled",
                "max_applications_per_day",
                "max_concurrent_browser_sessions",
                "max_retries_per_application",
            )
        }
        run_invariant(
            check_preference_consistency,
            min_salary=merged["min_salary"],
            salary_currency=merged["salary_currency"],
            review_before_submit=merged["review_before_submit"],
            auto_submit_enabled=merged["auto_submit_enabled"],
            field="preferences",
        )
        self._enforce_platform_caps(merged)

        for field, value in changes.items():
            setattr(preferences, field, value)
        if changes:
            self.audit.record(
                "preferences.update",
                user_id=user_id,
                entity="job_preferences",
                entity_id=preferences.id,
                context=ctx,
                details={
                    "fields": sorted(changes),
                    "autonomy": {k: v for k, v in changes.items() if k in _AUTONOMY_FIELDS},
                },
            )
            await self.session.commit()
        return preferences

    def _enforce_platform_caps(self, merged: dict[str, Any]) -> None:
        caps = {
            "max_applications_per_day": self.settings.max_applications_per_day_cap,
            "max_concurrent_browser_sessions": self.settings.max_concurrent_browser_sessions_cap,
            "max_retries_per_application": self.settings.max_retries_per_application_cap,
        }
        violations = [
            {"field": field, "message": f"must be at most {cap}"}
            for field, cap in caps.items()
            if merged[field] > cap
        ]
        if violations:
            raise DomainValidationError("Preference exceeds platform limits.", details=violations)
