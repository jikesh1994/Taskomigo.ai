from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.preferences import JobPreferences
    from app.models.profile import ProfessionalProfile
    from app.models.refresh_token import RefreshToken


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # Always stored lower-cased; uniqueness is therefore case-insensitive.
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str | None] = mapped_column(String(32))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole, 16), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None] = mapped_column()
    # Set once the user finishes (or explicitly skips the rest of) onboarding.
    onboarding_completed_at: Mapped[datetime | None] = mapped_column()

    profile: Mapped[ProfessionalProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False, lazy="raise"
    )
    preferences: Mapped[JobPreferences | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False, lazy="raise"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="raise"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
