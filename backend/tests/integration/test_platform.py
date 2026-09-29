"""Cross-cutting behaviour: health, rate limiting, RBAC, request IDs, headers, errors."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

from fakeredis import FakeAsyncRedis
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update

from app.api.deps import require_role
from app.core.database import Database
from app.main import create_app
from app.models import User
from app.models.enums import UserRole
from tests.conftest import RegisteredUser, make_settings


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_ok(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


async def test_readiness_reports_redis_failure(app: FastAPI, client: AsyncClient) -> None:
    app.state.redis.ping = AsyncMock(side_effect=ConnectionError("down"))
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "ok", "redis": "fail"}


async def test_auth_endpoints_are_rate_limited(tmp_path: Path, database: Database) -> None:
    settings = make_settings(tmp_path, rate_limit_auth_requests=3)
    app = create_app(settings, database=database, redis=FakeAsyncRedis(decode_responses=True))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"email": "x@example.com", "password": "whatever-123"}
        statuses = [
            (await client.post("/api/v1/auth/login", json=payload)).status_code for _ in range(4)
        ]
        assert statuses == [401, 401, 401, 429]
        limited = await client.post("/api/v1/auth/login", json=payload)
        assert limited.json()["error"]["code"] == "rate_limited"
        assert int(limited.headers["retry-after"]) >= 1
        # Buckets are independent per endpoint.
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401


async def test_failed_logins_are_throttled_per_account(tmp_path: Path, database: Database) -> None:
    settings = make_settings(tmp_path, login_max_failures_per_account=3)
    app = create_app(settings, database=database, redis=FakeAsyncRedis(decode_responses=True))
    register = {"email": "victim@example.com", "password": "correct-horse-42"}
    register |= {"first_name": "V", "last_name": "Ictim"}

    async def login(email: str, password: str, ip: str) -> tuple[int, str | None]:
        # A different client IP per attempt, as in password spraying: the per-IP limit
        # alone would never trigger.
        transport = ASGITransport(app=app, client=(ip, 50000))
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login", json={"email": email, "password": password}
            )
            code = response.json()["error"]["code"] if response.status_code >= 400 else None
            return response.status_code, code

    transport = ASGITransport(app=app, client=("198.51.100.1", 50000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.post("/api/v1/auth/register", json=register)).status_code == 201

    results = [
        await login("victim@example.com", "wrong-guess-1", f"203.0.113.{i}") for i in range(4)
    ]
    assert results == [(401, "invalid_credentials")] * 3 + [(429, "login_throttled")]
    # Throttled even with the right password (no oracle), and case-insensitively.
    assert await login("VICTIM@example.com", "correct-horse-42", "192.0.2.9") == (
        429,
        "login_throttled",
    )
    # Other accounts are unaffected, and unknown emails behave identically.
    assert (await login("nobody@example.com", "x-1234567890", "192.0.2.10"))[0] == 401


async def test_successful_login_resets_failure_count(tmp_path: Path, database: Database) -> None:
    settings = make_settings(tmp_path, login_max_failures_per_account=3)
    app = create_app(settings, database=database, redis=FakeAsyncRedis(decode_responses=True))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = {"email": "a@example.com", "password": "correct-horse-42"}
        await client.post(
            "/api/v1/auth/register", json=body | {"first_name": "A", "last_name": "B"}
        )
        wrong = body | {"password": "wrong-guess-1"}
        for _ in range(2):
            assert (await client.post("/api/v1/auth/login", json=wrong)).status_code == 401
        assert (await client.post("/api/v1/auth/login", json=body)).status_code == 200
        for _ in range(2):
            assert (await client.post("/api/v1/auth/login", json=wrong)).status_code == 401
        assert (await client.post("/api/v1/auth/login", json=body)).status_code == 200


async def test_require_role(
    app: FastAPI, client: AsyncClient, user: RegisteredUser, database: Database
) -> None:
    @app.get("/test-admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
    async def admin_only() -> dict[str, bool]:
        return {"ok": True}

    denied = await client.get("/test-admin-only", headers=user.headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "permission_denied"

    async with database.session_factory() as session:
        await session.execute(update(User).values(role=UserRole.ADMIN))
        await session.commit()
    allowed = await client.get("/test-admin-only", headers=user.headers)
    assert allowed.status_code == 200


async def test_request_id_propagation_and_security_headers(client: AsyncClient) -> None:
    generated = await client.get("/health/live")
    assert len(generated.headers["x-request-id"]) == 32
    assert generated.headers["x-content-type-options"] == "nosniff"
    assert generated.headers["x-frame-options"] == "DENY"
    assert "strict-transport-security" not in generated.headers  # only in production

    echoed = await client.get("/health/live", headers={"X-Request-ID": "client-req-12345"})
    assert echoed.headers["x-request-id"] == "client-req-12345"

    unsafe = await client.get("/health/live", headers={"X-Request-ID": "bad id\nwith newline"})
    assert unsafe.headers["x-request-id"] != "bad id\nwith newline"


async def test_error_envelope_includes_request_id(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/does-not-exist", headers={"X-Request-ID": "trace-abcdef12"}
    )
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["request_id"] == "trace-abcdef12"


async def test_unhandled_exceptions_return_generic_500(tmp_path: Path, database: Database) -> None:
    app = create_app(make_settings(tmp_path), database=database, redis=FakeAsyncRedis())

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("internal detail that must not leak")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/boom", headers={"Origin": "http://localhost:3000", "X-Request-ID": "trace-boom-123"}
        )
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["request_id"] == "trace-boom-123"
    assert "internal detail" not in response.text
    # The browser can only read the error (not a "network error") if CORS headers are set.
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["x-content-type-options"] == "nosniff"


async def test_openapi_documents_auth_and_errors(client: AsyncClient) -> None:
    spec = (await client.get("/openapi.json")).json()
    assert "HTTPBearer" in spec["components"]["securitySchemes"]
    assert "ErrorResponse" in spec["components"]["schemas"]
    me = spec["paths"]["/api/v1/users/me"]["get"]
    assert "401" in me["responses"]
    assert (await client.get("/docs")).status_code == 200
    assert (await client.get("/redoc")).status_code == 200
