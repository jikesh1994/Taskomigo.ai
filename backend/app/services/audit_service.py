from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger, redact
from app.models.audit_log import AuditLog
from app.models.enums import AuditResult
from app.repositories.audit_repository import AuditRepository

logger = get_logger("app.audit")


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Client metadata passed from the HTTP layer into services."""

    ip_address: str | None = None
    user_agent: str | None = None


class AuditService:
    """Adds audit entries to the caller's transaction (the caller commits)."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = AuditRepository(session)

    def record(
        self,
        action: str,
        *,
        result: AuditResult = AuditResult.SUCCESS,
        user_id: uuid.UUID | None = None,
        entity: str | None = None,
        entity_id: str | uuid.UUID | None = None,
        context: RequestContext | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        safe_details = redact(details or {})
        self._repo.add(
            AuditLog(
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=str(entity_id) if entity_id is not None else None,
                result=result,
                ip_address=context.ip_address if context else None,
                details=safe_details,
            )
        )
        logger.info(
            "audit",
            action=action,
            result=result.value,
            user_id=str(user_id) if user_id else None,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=safe_details,
        )
