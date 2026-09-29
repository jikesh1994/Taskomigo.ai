from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import RegisteredUser

USERS = "/api/v1/users"


async def test_get_and_update_me(client: AsyncClient, user: RegisteredUser) -> None:
    me = await client.get(f"{USERS}/me", headers=user.headers)
    assert me.status_code == 200
    assert me.json()["email"] == user.email

    updated = await client.patch(
        f"{USERS}/me",
        headers=user.headers,
        json={"first_name": "Grace", "phone": "+91 98765 43210", "timezone": "Asia/Kolkata"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["first_name"] == "Grace"
    assert body["timezone"] == "Asia/Kolkata"
    assert body["last_name"] == me.json()["last_name"]


async def test_complete_onboarding_is_idempotent(client: AsyncClient, user: RegisteredUser) -> None:
    me = await client.get(f"{USERS}/me", headers=user.headers)
    assert me.json()["onboarding_completed_at"] is None

    first = await client.post(f"{USERS}/me/onboarding/complete", headers=user.headers)
    assert first.status_code == 200
    completed_at = first.json()["onboarding_completed_at"]
    assert completed_at is not None

    second = await client.post(f"{USERS}/me/onboarding/complete", headers=user.headers)
    assert second.json()["onboarding_completed_at"] == completed_at


async def test_onboarding_cannot_be_set_via_update(
    client: AsyncClient, user: RegisteredUser
) -> None:
    response = await client.patch(
        f"{USERS}/me",
        headers=user.headers,
        json={"onboarding_completed_at": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code == 422


async def test_complete_onboarding_requires_auth(client: AsyncClient) -> None:
    response = await client.post(f"{USERS}/me/onboarding/complete")
    assert response.status_code == 401


async def test_cannot_escalate_role_via_update(client: AsyncClient, user: RegisteredUser) -> None:
    response = await client.patch(f"{USERS}/me", headers=user.headers, json={"role": "admin"})
    assert response.status_code == 422


async def test_invalid_timezone_rejected(client: AsyncClient, user: RegisteredUser) -> None:
    response = await client.patch(
        f"{USERS}/me", headers=user.headers, json={"timezone": "Nowhere/City"}
    )
    assert response.status_code == 422


async def test_change_password_revokes_sessions(client: AsyncClient, user: RegisteredUser) -> None:
    wrong = await client.post(
        f"{USERS}/me/password",
        headers=user.headers,
        json={"current_password": "not-it-123", "new_password": "brand-new-pass-7"},
    )
    assert wrong.status_code == 400
    assert wrong.json()["error"]["code"] == "invalid_current_password"

    ok = await client.post(
        f"{USERS}/me/password",
        headers=user.headers,
        json={"current_password": user.password, "new_password": "brand-new-pass-7"},
    )
    assert ok.status_code == 204

    client.cookies.clear()
    refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": user.refresh_token})
    assert refresh.status_code == 401

    old_login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": user.password}
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "brand-new-pass-7"}
    )
    assert new_login.status_code == 200


async def test_change_password_enforces_policy(client: AsyncClient, user: RegisteredUser) -> None:
    response = await client.post(
        f"{USERS}/me/password",
        headers=user.headers,
        json={"current_password": user.password, "new_password": "weak"},
    )
    assert response.status_code == 422
