from __future__ import annotations

import uuid
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.models.enums import UserRole
from app.schemas.common import ORMModel, UtcDatetime


def _validate_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown timezone: {value!r}") from exc
    return value


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9 ()\-]{6,32}$")]
Timezone = Annotated[str, StringConstraints(max_length=64), AfterValidator(_validate_timezone)]


class UserRead(ORMModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    timezone: str
    role: UserRole
    is_active: bool
    onboarding_completed_at: UtcDatetime | None
    created_at: UtcDatetime


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: Name | None = None
    last_name: Name | None = None
    phone: Phone | None = None
    timezone: Timezone | None = Field(default=None, examples=["Asia/Kolkata"])
