"""A user must never be able to read or modify another user's data."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import RegisterFn

PROFILE = "/api/v1/profile"


async def test_users_cannot_touch_each_others_profile_items(
    client: AsyncClient, register_user: RegisterFn
) -> None:
    alice = await register_user("alice@example.com")
    bob = await register_user("bob@example.com")

    exp = (
        await client.post(
            f"{PROFILE}/experiences",
            headers=alice.headers,
            json={"company": "Alice Corp", "title": "CTO", "start_date": "2020-01-01"},
        )
    ).json()
    edu = (
        await client.post(
            f"{PROFILE}/education",
            headers=alice.headers,
            json={"institution": "MIT", "degree": "PhD"},
        )
    ).json()
    skill = (
        await client.post(f"{PROFILE}/skills", headers=alice.headers, json={"name": "Rust"})
    ).json()

    for path in (f"experiences/{exp['id']}", f"education/{edu['id']}", f"skills/{skill['id']}"):
        patch = await client.patch(f"{PROFILE}/{path}", headers=bob.headers, json={})
        delete = await client.delete(f"{PROFILE}/{path}", headers=bob.headers)
        # 404 (not 403) so the existence of other users' records is not revealed.
        assert patch.status_code == 404, path
        assert delete.status_code == 404, path

    bob_profile = (await client.get(PROFILE, headers=bob.headers)).json()
    assert bob_profile["experiences"] == [] and bob_profile["skills"] == []
    assert (await client.get(f"{PROFILE}/experiences", headers=bob.headers)).json() == []

    alice_profile = (await client.get(PROFILE, headers=alice.headers)).json()
    assert len(alice_profile["experiences"]) == 1
    assert len(alice_profile["education"]) == 1
    assert len(alice_profile["skills"]) == 1


async def test_preferences_are_per_user(client: AsyncClient, register_user: RegisterFn) -> None:
    alice = await register_user()
    bob = await register_user()
    await client.patch("/api/v1/preferences", headers=alice.headers, json={"keywords": ["python"]})
    assert (await client.get("/api/v1/preferences", headers=bob.headers)).json()["keywords"] == []
