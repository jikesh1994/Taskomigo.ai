"""Structured JSON logging with request context and secret redaction."""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from typing import Any

import structlog

REDACTED = "[REDACTED]"

_SENSITIVE_EXACT = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "session",
        "encrypted_session_reference",
        "jwt",
        "otp",
        "mfa_code",
    }
)
_SENSITIVE_FRAGMENTS = ("password", "secret", "token", "cookie", "api_key", "apikey", "credential")


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return lowered in _SENSITIVE_EXACT or any(f in lowered for f in _SENSITIVE_FRAGMENTS)


def redact(value: Any) -> Any:
    """Recursively replace values stored under sensitive keys."""
    if isinstance(value, Mapping):
        return {
            k: (REDACTED if isinstance(k, str) and is_sensitive_key(k) else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [redact(v) for v in value]
    return value


def _redact_processor(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return redact(event_dict)


def configure_logging(level: str = "INFO", *, json_output: bool = True) -> None:
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_processor,
    ]
    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    renderer: Any = (
        structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())

    # Route third-party loggers through our formatter; drop uvicorn's duplicate access log.
    for name in ("uvicorn", "uvicorn.error", "celery"):
        lib_logger = logging.getLogger(name)
        lib_logger.handlers = []
        lib_logger.propagate = True
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
