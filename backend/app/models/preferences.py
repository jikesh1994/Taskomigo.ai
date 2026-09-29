from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class JobPreferences(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Job-search criteria and agent behaviour settings for a user."""

    __tablename__ = "job_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )

    # Search criteria
    keywords: Mapped[list[str]] = mapped_column(default=list)
    employment_types: Mapped[list[str]] = mapped_column(default=list)
    excluded_companies: Mapped[list[str]] = mapped_column(default=list)
    excluded_industries: Mapped[list[str]] = mapped_column(default=list)
    min_salary: Mapped[int | None] = mapped_column()
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    remote_only: Mapped[bool] = mapped_column(default=False)
    min_match_score: Mapped[int] = mapped_column(default=60)
    # Matching weights {skills, experience, location, salary, preferences, other};
    # empty means the defaults in app/jobs/matching.py.
    match_weights: Mapped[dict[str, int]] = mapped_column(default=dict)

    # Agent behaviour
    max_applications_per_day: Mapped[int] = mapped_column(default=20)
    max_concurrent_browser_sessions: Mapped[int] = mapped_column(default=2)
    max_retries_per_application: Mapped[int] = mapped_column(default=2)
    auto_fill_enabled: Mapped[bool] = mapped_column(default=True)
    auto_answer_enabled: Mapped[bool] = mapped_column(default=True)
    review_before_submit: Mapped[bool] = mapped_column(default=True)
    # Only for routine applications; sensitive/legal steps always require approval.
    auto_submit_enabled: Mapped[bool] = mapped_column(default=False)

    user: Mapped[User] = relationship(back_populates="preferences", lazy="raise")
