"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.ai.llm import LLMProvider, create_llm_provider
from app.api import health
from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import Database
from app.core.logging import configure_logging, get_logger
from app.core.middleware import (
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
    UnhandledErrorMiddleware,
)
from app.core.redis import create_redis
from app.jobs.providers import JobSearchProvider
from app.jobs.providers.registry import build_providers, new_http_client
from app.services.job_dispatch import CeleryJobDispatcher, InlineJobDispatcher, JobDispatcher
from app.services.resume_dispatch import (
    CeleryParseDispatcher,
    InlineParseDispatcher,
    ParseDispatcher,
)
from app.storage import ObjectStorage
from app.storage.factory import create_storage

API_DESCRIPTION = """
Backend for **Taskomigo**, the supervised AI job application agent.

**Authentication:** call `POST /api/v1/auth/login` (or `/register`), then send
`Authorization: Bearer <access_token>`. Access tokens are short-lived. Get a new one
from `POST /api/v1/auth/refresh`. Refresh tokens rotate on every use.

**Errors** always look like this:
`{"error": {"code": "...", "message": "...", "details": ..., "request_id": "..."}}`
"""


def create_app(
    settings: Settings | None = None,
    *,
    database: Database | None = None,
    redis: Redis | None = None,
    storage: ObjectStorage | None = None,
    llm: LLMProvider | None = None,
    parse_dispatcher: ParseDispatcher | None = None,
    job_http_client: httpx.AsyncClient | None = None,
    job_providers: dict[str, JobSearchProvider] | None = None,
    job_dispatcher: JobDispatcher | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)
    logger = get_logger("app")

    # Resources are created eagerly (connections open lazily). The lifespan only
    # disposes them, so the app also works in test transports that skip lifespan.
    db = database or Database(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    redis_client = redis or create_redis(settings.redis_url)
    object_storage = storage or create_storage(settings)
    llm_provider = llm or create_llm_provider(settings)
    dispatcher = parse_dispatcher or (
        InlineParseDispatcher(db, object_storage, llm_provider, max_pages=settings.resume_max_pages)
        if settings.resume_parse_inline
        else CeleryParseDispatcher()
    )
    http_client = job_http_client or new_http_client(settings)
    providers = job_providers or build_providers(http_client, settings)
    jobs_dispatcher = job_dispatcher or (
        InlineJobDispatcher(db, providers, llm_provider, concurrency=settings.job_fetch_concurrency)
        if settings.job_tasks_inline
        else CeleryJobDispatcher()
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info("startup", environment=settings.environment)
        try:
            yield
        finally:
            await db.dispose()
            await redis_client.aclose()
            await http_client.aclose()
            logger.info("shutdown")

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=API_DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.state.settings = settings
    app.state.db = db
    app.state.redis = redis_client
    app.state.storage = object_storage
    app.state.llm = llm_provider
    app.state.parse_dispatcher = dispatcher
    app.state.job_providers = providers
    app.state.job_dispatcher = jobs_dispatcher

    # Middleware runs outermost-last-added: request context wraps everything, and
    # unhandled errors become responses inside CORS so browsers can read them.
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=settings.is_production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app
