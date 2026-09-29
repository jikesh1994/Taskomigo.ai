from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import utc_now
from app.models.base import Base, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import AuditResult


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Append-only security/audit trail. Metadata is redacted before storage."""

    __tablename__ = "audit_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[AuditResult] = mapped_column(str_enum(AuditResult, 16))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    # "metadata" is reserved on declarative classes, hence the attribute name.
    details: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, index=True)
