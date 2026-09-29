"""Shared schema building blocks."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, ClassVar, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    TypeAdapter,
    model_validator,
)

from app.core.security import ensure_aware

# Response timestamps always carry an explicit UTC offset. SQLite returns naive
# values; clients would otherwise parse them as local time.
UtcDatetime = Annotated[datetime, AfterValidator(ensure_aware)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PatchModel(BaseModel):
    """Base for PATCH bodies: omitted fields are untouched, and an explicit `null`
    is rejected for fields whose column is NOT NULL."""

    model_config = ConfigDict(extra="forbid")
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_explicit_nulls(self) -> Self:
        bad = sorted(
            name
            for name in self.model_fields_set & self.non_nullable_fields
            if getattr(self, name) is None
        )
        if bad:
            raise ValueError(f"These fields cannot be null: {', '.join(bad)}")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class ErrorBody(BaseModel):
    code: str = Field(examples=["not_found"])
    message: str = Field(examples=["Resource not found."])
    details: Any | None = None
    request_id: str | None = Field(default=None, examples=["5f1c2b0e9d7a4c3e8b6a1f2d3c4b5a69"])


class ErrorResponse(BaseModel):
    error: ErrorBody


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _normalize_str_list(values: list[str]) -> list[str]:
    """Trim, drop empties and de-duplicate case-insensitively, preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        item = " ".join(raw.split())
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result


_HTTP_URL = TypeAdapter(HttpUrl)


def _validate_http_url(value: str | None) -> str | None:
    """Validate as an http(s) URL but keep it as a plain string (it's stored as VARCHAR)."""
    value = _strip_or_none(value)
    return None if value is None else str(_HTTP_URL.validate_python(value))


def _bounded(max_length: int) -> Any:
    return Annotated[
        Annotated[str, StringConstraints(max_length=max_length)] | None,
        AfterValidator(_strip_or_none),
    ]


# Optional free text: trimmed, empty string becomes None.
Text50 = _bounded(50)
Text200 = _bounded(200)
Text255 = _bounded(255)
Text5000 = _bounded(5_000)
Text10000 = _bounded(10_000)
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
StringList = Annotated[
    list[Annotated[str, StringConstraints(max_length=200)]],
    Field(max_length=50),
    AfterValidator(_normalize_str_list),
]
CurrencyCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{3}$")
]
UrlStr = Annotated[
    Annotated[str, StringConstraints(max_length=500)] | None,
    AfterValidator(_validate_http_url),
    Field(json_schema_extra={"format": "uri"}),
]

# Standard error responses documented on routes.
AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing, invalid or expired access token"},
}
NOT_FOUND_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Resource not found (or not owned by you)"},
}
VALIDATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {"model": ErrorResponse, "description": "Validation error"},
}
