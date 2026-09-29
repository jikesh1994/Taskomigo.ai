"""Helpers that turn schema-level invariant failures into API validation errors."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.config import Settings
from app.core.exceptions import DomainValidationError
from app.schemas.auth import validate_password_strength


def run_invariant(
    check: Callable[..., None], *args: Any, field: str | None = None, **kwargs: Any
) -> None:
    try:
        check(*args, **kwargs)
    except ValueError as exc:
        raise DomainValidationError(
            str(exc), details=[{"field": field, "message": str(exc)}]
        ) from exc


def ensure_password_policy(password: str, settings: Settings, *, field: str = "password") -> None:
    run_invariant(validate_password_strength, password, settings.password_min_length, field=field)
