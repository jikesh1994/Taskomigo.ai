from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import SkillProficiency

if TYPE_CHECKING:
    from app.models.profile import ProfessionalProfile


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("profile_id", "normalized_name"),)

    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("professional_profiles.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    # Lower-cased, whitespace-collapsed name used for uniqueness and job matching.
    normalized_name: Mapped[str] = mapped_column(String(100))
    years: Mapped[float | None] = mapped_column()
    proficiency: Mapped[SkillProficiency | None] = mapped_column(str_enum(SkillProficiency, 16))

    profile: Mapped[ProfessionalProfile] = relationship(back_populates="skills", lazy="raise")
