from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.user import Name, Phone, Timezone, UserRead

PASSWORD_MAX_LENGTH = 128


def validate_password_strength(password: str, min_length: int = 10) -> str:
    """Length-first policy (NIST 800-63B) plus a minimal character mix."""
    if len(password) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters long.")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters long.")
    if password.strip() != password:
        raise ValueError("Password must not start or end with whitespace.")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one letter and one digit.")
    return password


def normalize_email(value: str) -> str:
    return value.strip().lower()


class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "email": "ada@example.com",
                    "password": "correct-horse-42",
                    "first_name": "Ada",
                    "last_name": "Lovelace",
                    "timezone": "Europe/London",
                }
            ]
        },
    )

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    first_name: Name
    last_name: Name
    phone: Phone | None = None
    timezone: Timezone = "UTC"

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return normalize_email(value)


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [{"email": "ada@example.com", "password": "correct-horse-42"}]
        },
    )

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return normalize_email(value)


class RefreshRequest(BaseModel):
    """The refresh token may come from this body or from the httpOnly cookie."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: str | None = Field(default=None, min_length=16, max_length=512)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105
    expires_in: int = Field(description="Access-token lifetime in seconds")
    refresh_expires_at: datetime


class AuthResponse(TokenResponse):
    user: UserRead
