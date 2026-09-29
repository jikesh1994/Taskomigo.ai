"""Domain exceptions mapped to consistent HTTP error responses."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code: int = 400
    code: str = "bad_request"
    default_message: str = "Request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.default_message
        if code:
            self.code = code
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_failed"
    default_message = "Authentication failed."

    def __init__(self, message: str | None = None, **kwargs: Any) -> None:
        kwargs.setdefault("headers", {"WWW-Authenticate": "Bearer"})
        super().__init__(message, **kwargs)


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"
    default_message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    default_message = "Resource not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    default_message = "Resource conflicts with existing state."


class DomainValidationError(AppError):
    status_code = 422
    code = "validation_error"
    default_message = "Request validation failed."


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"
    default_message = "The uploaded file is too large."


class UnsupportedMediaTypeError(AppError):
    status_code = 415
    code = "unsupported_media_type"
    default_message = "This file type isn't supported."


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"
    default_message = "The service is temporarily unavailable. Please try again."


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    default_message = "Too many requests. Please try again later."


class ConfigurationError(RuntimeError):
    """Raised when the service is misconfigured (never shown to API clients)."""
