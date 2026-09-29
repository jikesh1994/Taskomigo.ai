from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import RemotePreference

if TYPE_CHECKING:
    from app.models.education import Education
    from app.models.experience import Experience
    from app.models.skill import Skill
    from app.models.user import User


class ProfessionalProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Verified professional facts. The AI may only use information stored here,
    in approved resumes, or in answers the user explicitly approved."""

    __tablename__ = "professional_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    headline: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    years_of_experience: Mapped[float | None] = mapped_column()
    current_title: Mapped[str | None] = mapped_column(String(200))
    current_company: Mapped[str | None] = mapped_column(String(200))
    preferred_titles: Mapped[list[str]] = mapped_column(default=list)
    preferred_locations: Mapped[list[str]] = mapped_column(default=list)
    remote_preference: Mapped[RemotePreference] = mapped_column(
        str_enum(RemotePreference, 16), default=RemotePreference.ANY
    )
    # Annual amounts in whole units of `currency`.
    expected_salary_min: Mapped[int | None] = mapped_column()
    expected_salary_max: Mapped[int | None] = mapped_column()
    currency: Mapped[str | None] = mapped_column(String(3))
    notice_period_days: Mapped[int | None] = mapped_column()
    work_authorization: Mapped[str | None] = mapped_column(String(255))
    # None means "unknown": the agent must ask the user rather than guess.
    sponsorship_required: Mapped[bool | None] = mapped_column()
    willing_to_relocate: Mapped[bool | None] = mapped_column()
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))

    user: Mapped[User] = relationship(back_populates="profile", lazy="raise")
    experiences: Mapped[list[Experience]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="Experience.start_date.desc()",
    )
    education: Mapped[list[Education]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="Education.start_date.desc()",
    )
    skills: Mapped[list[Skill]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="Skill.normalized_name",
    )
