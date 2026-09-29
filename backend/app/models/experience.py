from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import EmploymentType

if TYPE_CHECKING:
    from app.models.profile import ProfessionalProfile


class Experience(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "experiences"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("professional_profiles.id", ondelete="CASCADE"), index=True
    )
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    employment_type: Mapped[EmploymentType | None] = mapped_column(str_enum(EmploymentType, 16))
    start_date: Mapped[date] = mapped_column()
    end_date: Mapped[date | None] = mapped_column()
    is_current: Mapped[bool] = mapped_column(default=False)
    description: Mapped[str | None] = mapped_column(Text)
    technologies: Mapped[list[str]] = mapped_column(default=list)

    profile: Mapped[ProfessionalProfile] = relationship(back_populates="experiences", lazy="raise")
