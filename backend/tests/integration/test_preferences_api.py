from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import Database
from app.models import AuditLog
from tests.conftest import RegisteredUser

PREFS = "/api/v1/preferences"


async def test_defaults_are_safe(client: AsyncClient, user: RegisteredUser) -> None:
    body = (await client.get(PREFS, headers=user.headers)).json()
    assert body["review_before_submit"] is True
    assert body["auto_submit_enabled"] is False
    assert body["max_applications_per_day"] == 20
    assert body["max_concurrent_browser_sessions"] == 2
    assert body["max_retries_per_application"] == 2


async def test_put_and_patch(client: AsyncClient, user: RegisteredUser) -> None:
    put = await client.put(
        PREFS,
        headers=user.headers,
        json={
            "keywords": ["python", "django"],
            "employment_types": ["full_time", "contract"],
            "excluded_companies": ["BadCo"],
            "min_salary": 2500000,
            "salary_currency": "INR",
            "remote_only": True,
            "min_match_score": 70,
        },
    )
    assert put.status_code == 200, put.text
    assert put.json()["employment_types"] == ["full_time", "contract"]

    patch = await client.patch(PREFS, headers=user.headers, json={"min_match_score": 80})
    body = patch.json()
    assert body["min_match_score"] == 80
    assert body["keywords"] == ["python", "django"]


async def test_auto_submit_consistency_checked_after_merge(
    client: AsyncClient, user: RegisteredUser, database: Database
) -> None:
    # review_before_submit is still true in the stored record.
    bad = await client.patch(PREFS, headers=user.headers, json={"auto_submit_enabled": True})
    assert bad.status_code == 422

    ok = await client.patch(
        PREFS,
        headers=user.headers,
        json={"auto_submit_enabled": True, "review_before_submit": False},
    )
    assert ok.status_code == 200

    async with database.session_factory() as session:
        entry = (
            await session.execute(select(AuditLog).where(AuditLog.action == "preferences.update"))
        ).scalar_one()
    assert entry.details["autonomy"] == {"auto_submit_enabled": True, "review_before_submit": False}


async def test_platform_caps_enforced(client: AsyncClient, user: RegisteredUser) -> None:
    response = await client.patch(
        PREFS,
        headers=user.headers,
        json={"max_applications_per_day": 10_000, "max_concurrent_browser_sessions": 50},
    )
    assert response.status_code == 422
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert fields == {"max_applications_per_day", "max_concurrent_browser_sessions"}
