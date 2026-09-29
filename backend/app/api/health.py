from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.core.logging import get_logger

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger(__name__)

CHECK_TIMEOUT_SECONDS = 3.0


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    checks: dict[str, Literal["ok", "fail"]]


@router.get("/live", response_model=LivenessResponse, summary="Process is running")
async def live() -> LivenessResponse:
    return LivenessResponse()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Dependencies are reachable",
    responses={503: {"model": ReadinessResponse, "description": "A dependency is down"}},
)
async def ready(request: Request) -> JSONResponse:
    checks = {
        "database": await _check(_ping_database(request), "database"),
        "redis": await _check(_ping_redis(request), "redis"),
    }
    healthy = all(v == "ok" for v in checks.values())
    body = ReadinessResponse(status="ok" if healthy else "unavailable", checks=checks)
    return JSONResponse(body.model_dump(), status_code=200 if healthy else 503)


async def _ping_database(request: Request) -> None:
    async with request.app.state.db.engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def _ping_redis(request: Request) -> None:
    await request.app.state.redis.ping()


async def _check(coro: object, name: str) -> Literal["ok", "fail"]:
    try:
        await asyncio.wait_for(coro, timeout=CHECK_TIMEOUT_SECONDS)  # type: ignore[arg-type]
    except Exception as exc:
        logger.warning("readiness_check_failed", check=name, error=type(exc).__name__)
        return "fail"
    return "ok"
