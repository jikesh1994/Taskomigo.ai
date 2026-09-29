from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import Database
from app.models import AuditLog, JobPreferences, ProfessionalProfile, User
from app.models.enums import AuditResult
from tests.conftest import DEFAULT_PASSWORD, RegisteredUser, RegisterFn

AUTH = "/api/v1/auth"


async def test_register_creates_user_profile_and_preferences(
    client: AsyncClient, database: Database
) -> None:
    response = await client.post(
        f"{AUTH}/register",
        json={
            "email": "Ada@Example.com",
            "password": DEFAULT_PASSWORD,
            "first_name": "Ada",
            "last_name": "Lovelace",
            "timezone": "Europe/London",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["role"] == "user"
    assert "password" not in response.text and "password_hash" not in response.text

    cookie = response.headers["set-cookie"]
    assert (
        "refresh_token=" in cookie and "HttpOnly" in cookie and "samesite=strict" in cookie.lower()
    )

    async with database.session_factory() as session:
        user = (await session.execute(select(User))).scalar_one()
        assert user.password_hash.startswith("$argon2id$")
        assert (await session.execute(select(ProfessionalProfile))).scalar_one().user_id == user.id
        assert (await session.execute(select(JobPreferences))).scalar_one().user_id == user.id


async def test_register_duplicate_email_is_case_insensitive(
    client: AsyncClient, register_user: RegisterFn
) -> None:
    await register_user("dup@example.com")
    response = await client.post(
        f"{AUTH}/register",
        json={
            "email": "DUP@example.com",
            "password": DEFAULT_PASSWORD,
            "first_name": "A",
            "last_name": "B",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


async def test_register_weak_password_rejected(client: AsyncClient) -> None:
    response = await client.post(
        f"{AUTH}/register",
        json={
            "email": "weak@example.com",
            "password": "short",
            "first_name": "A",
            "last_name": "B",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_validation_errors_never_echo_passwords(client: AsyncClient) -> None:
    secret = "MySuperSecret-999"
    response = await client.post(
        f"{AUTH}/register", json={"email": "not-an-email", "password": secret, "first_name": "A"}
    )
    assert response.status_code == 422
    assert secret not in response.text
    fields = {e["field"] for e in response.json()["error"]["details"]}
    assert "body.email" in fields and "body.last_name" in fields


async def test_login_success_and_failure_messages_match(
    client: AsyncClient, user: RegisteredUser
) -> None:
    ok = await client.post(
        f"{AUTH}/login", json={"email": user.email.upper(), "password": user.password}
    )
    assert ok.status_code == 200
    assert ok.json()["user"]["id"] == user.id

    wrong_password = await client.post(
        f"{AUTH}/login", json={"email": user.email, "password": "nope-12345"}
    )
    unknown_user = await client.post(
        f"{AUTH}/login", json={"email": "ghost@example.com", "password": "nope-12345"}
    )
    for response in (wrong_password, unknown_user):
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"
        assert response.json()["error"]["code"] == "invalid_credentials"
    assert wrong_password.json()["error"]["message"] == unknown_user.json()["error"]["message"]


async def test_login_audited_without_secrets(
    client: AsyncClient, user: RegisteredUser, database: Database
) -> None:
    await client.post(f"{AUTH}/login", json={"email": user.email, "password": "wrong-pass-1"})
    await client.post(f"{AUTH}/login", json={"email": user.email, "password": user.password})
    async with database.session_factory() as session:
        rows = (
            (await session.execute(select(AuditLog).where(AuditLog.action == "auth.login")))
            .scalars()
            .all()
        )
    results = sorted(r.result for r in rows)
    assert results == sorted([AuditResult.FAILURE, AuditResult.SUCCESS])
    for row in rows:
        assert row.ip_address == "203.0.113.10"
        assert "wrong-pass-1" not in str(row.details) and user.password not in str(row.details)


async def test_inactive_user_cannot_login_or_use_token(
    client: AsyncClient, user: RegisteredUser, database: Database
) -> None:
    async with database.session_factory() as session:
        db_user = (await session.execute(select(User))).scalar_one()
        db_user.is_active = False
        await session.commit()
    login = await client.post(
        f"{AUTH}/login", json={"email": user.email, "password": user.password}
    )
    assert login.status_code == 401
    me = await client.get("/api/v1/users/me", headers=user.headers)
    assert me.status_code == 401


async def test_refresh_rotates_tokens(client: AsyncClient, user: RegisteredUser) -> None:
    response = await client.post(f"{AUTH}/refresh", json={"refresh_token": user.refresh_token})
    assert response.status_code == 200
    body = response.json()
    assert body["refresh_token"] != user.refresh_token
    me = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200

    # The new token works once more.
    again = await client.post(f"{AUTH}/refresh", json={"refresh_token": body["refresh_token"]})
    assert again.status_code == 200


async def test_refresh_token_reuse_revokes_entire_session(
    client: AsyncClient, user: RegisteredUser, database: Database
) -> None:
    rotated = await client.post(f"{AUTH}/refresh", json={"refresh_token": user.refresh_token})
    new_token = rotated.json()["refresh_token"]

    # An attacker replays the old token.
    replay = await client.post(f"{AUTH}/refresh", json={"refresh_token": user.refresh_token})
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "refresh_token_reused"

    # The legitimate user's newer token is now revoked too.
    legit = await client.post(f"{AUTH}/refresh", json={"refresh_token": new_token})
    assert legit.status_code == 401

    async with database.session_factory() as session:
        actions = (await session.execute(select(AuditLog.action))).scalars().all()
    assert "auth.refresh_token_reuse" in actions


async def test_refresh_via_cookie(client: AsyncClient, register_user: RegisterFn) -> None:
    await register_user()  # client cookie jar now holds the refresh cookie
    response = await client.post(f"{AUTH}/refresh")
    assert response.status_code == 200


async def test_refresh_requires_token(client: AsyncClient) -> None:
    missing = await client.post(f"{AUTH}/refresh")
    assert missing.status_code == 401
    bogus = await client.post(f"{AUTH}/refresh", json={"refresh_token": "x" * 40})
    assert bogus.status_code == 401
    assert bogus.json()["error"]["code"] == "invalid_refresh_token"


async def test_logout_revokes_refresh_token(client: AsyncClient, user: RegisteredUser) -> None:
    response = await client.post(f"{AUTH}/logout", json={"refresh_token": user.refresh_token})
    assert response.status_code == 204
    client.cookies.clear()
    after = await client.post(f"{AUTH}/refresh", json={"refresh_token": user.refresh_token})
    assert after.status_code == 401
    # Idempotent
    assert (
        await client.post(f"{AUTH}/logout", json={"refresh_token": user.refresh_token})
    ).status_code == 204


async def test_protected_route_requires_valid_token(client: AsyncClient) -> None:
    missing = await client.get("/api/v1/users/me")
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "not_authenticated"
    bad = await client.get("/api/v1/users/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "invalid_token"
