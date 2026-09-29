"""Exception handlers producing a single error envelope:

{"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger("app.errors")


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": getattr(request.state, "request_id", None),
        }
    }
    return JSONResponse(jsonable_encoder(body), status_code=status_code, headers=headers)


def _sanitize_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop `input` and `ctx`: they can echo submitted values such as passwords."""
    return [
        {
            "field": ".".join(str(p) for p in err.get("loc", ())),
            "message": err.get("msg"),
            "type": err.get("type"),
        }
        for err in errors
    ]


async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("app_error", code=exc.code, message=exc.message)
    return _error_response(
        request, exc.status_code, exc.code, exc.message, exc.details, exc.headers
    )


async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        request,
        422,
        "validation_error",
        "Request validation failed.",
        _sanitize_validation_errors(list(exc.errors())),
    )


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return _error_response(
        request, exc.status_code, code, str(exc.detail), headers=getattr(exc, "headers", None)
    )


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", path=request.url.path)
    return _error_response(request, 500, "internal_error", "An unexpected error occurred.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_handler)
