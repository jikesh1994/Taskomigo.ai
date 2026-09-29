from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import ResumeFileType, ResumeParseStatus


class Resume(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An uploaded resume. The file itself lives in object storage, encrypted."""

    __tablename__ = "resumes"
    __table_args__ = (
        # At most one default resume per user, enforced by the database.
        Index(
            "uq_resumes_user_default",
            "user_id",
            unique=True,
            postgresql_where=text("is_default"),
            sqlite_where=text("is_default = 1"),
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[ResumeFileType] = mapped_column(str_enum(ResumeFileType, 8))
    size_bytes: Mapped[int] = mapped_column()
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(300), unique=True)
    is_default: Mapped[bool] = mapped_column(default=False)

    parse_status: Mapped[ResumeParseStatus] = mapped_column(
        str_enum(ResumeParseStatus, 16), default=ResumeParseStatus.PENDING
    )
    parse_error_code: Mapped[str | None] = mapped_column(String(64))
    parse_error: Mapped[str | None] = mapped_column(String(500))
    parsed_text: Mapped[str | None] = mapped_column(Text)
    # ParsedResume (app/ai/resume/schema.py), grounded against parsed_text.
    parsed_data: Mapped[dict[str, Any] | None] = mapped_column()
    parser: Mapped[str | None] = mapped_column(String(120))  # "<provider>:<model>"
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    parsed_at: Mapped[datetime | None] = mapped_column()
    # Review decisions already taken for this resume: {review_item_id: action}.
    review_decisions: Mapped[dict[str, Any]] = mapped_column(default=dict)
