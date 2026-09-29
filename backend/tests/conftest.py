"""Test fixtures.

Tests run against SQLite by default for speed. Set TEST_DATABASE_URL to a
PostgreSQL URL (postgresql+asyncpg://...) to run the same suite against Postgres.
Redis is replaced by fakeredis.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.database import Database
from app.main import create_app
from app.models import Base
from tests.job_fixtures import FakeBoards
from tests.resume_fixtures import ScriptedLLM

DEFAULT_PASSWORD = "correct-horse-42"


def make_settings(tmp_path: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "environment": "test",
        "database_url": os.environ.get(
            "TEST_DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
        ),
        "redis_url": "redis://fake:6379/0",
        "secret_key": "test-secret-key-" + "x" * 32,
        "jwt_secret": "test-jwt-secret-" + "y" * 32,
        "encryption_keys": Fernet.generate_key().decode(),
        "log_json": False,
        "log_level": "WARNING",
        "rate_limit_auth_requests": 1000,
        "storage_local_path": str(tmp_path / "uploads"),
        "resume_parse_inline": True,
        "job_tasks_inline": True,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest_asyncio.fixture
async def database(settings: Settings) -> AsyncIterator[Database]:
    db = Database(settings.database_url)
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield db
    await db.dispose()


@pytest_asyncio.fixture
async def fake_redis() -> AsyncIterator[FakeAsyncRedis]:
    redis = FakeAsyncRedis(decode_responses=True)
    yield redis
    await redis.flushall()
    await redis.aclose()


@pytest.fixture
def llm() -> ScriptedLLM:
    """The AI model for API tests: returns a scripted parse of tests.resume_fixtures."""
    return ScriptedLLM()


@pytest.fixture
def fake_boards() -> FakeBoards:
    """Greenhouse/Lever job boards served in-process (see tests.job_fixtures)."""
    return FakeBoards()


@pytest_asyncio.fixture
async def app(
    settings: Settings,
    database: Database,
    fake_redis: FakeAsyncRedis,
    llm: ScriptedLLM,
    fake_boards: FakeBoards,
) -> AsyncIterator[FastAPI]:
    async with httpx.AsyncClient(transport=fake_boards.transport()) as job_client:
        yield create_app(
            settings, database=database, redis=fake_redis, llm=llm, job_http_client=job_client
        )


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app, client=("203.0.113.10", 51000))
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@dataclass
class RegisteredUser:
    id: str
    email: str
    password: str
    access_token: str
    refresh_token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}


RegisterFn = Callable[..., Awaitable[RegisteredUser]]


@pytest.fixture
def register_user(client: AsyncClient) -> RegisterFn:
    counter = {"n": 0}

    async def _register(
        email: str | None = None, password: str = DEFAULT_PASSWORD
    ) -> RegisteredUser:
        counter["n"] += 1
        email = email or f"user{counter['n']}@example.com"
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "first_name": "Test",
                "last_name": f"User{counter['n']}",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        return RegisteredUser(
            id=body["user"]["id"],
            email=email.lower(),
            password=password,
            access_token=body["access_token"],
            refresh_token=body["refresh_token"],
        )

    return _register


@pytest_asyncio.fixture
async def user(register_user: RegisterFn) -> RegisteredUser:
    return await register_user()
