from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import RegisteredUser

PROFILE = "/api/v1/profile"


async def test_new_user_has_empty_profile(client: AsyncClient, user: RegisteredUser) -> None:
    response = await client.get(PROFILE, headers=user.headers)
    assert response.status_code == 200
    body = response.json()
    assert body["remote_preference"] == "any"
    assert body["experiences"] == [] and body["skills"] == [] and body["education"] == []
    assert body["sponsorship_required"] is None


async def test_put_replaces_and_patch_merges(client: AsyncClient, user: RegisteredUser) -> None:
    put = await client.put(
        PROFILE,
        headers=user.headers,
        json={
            "headline": "Senior Python Engineer",
            "years_of_experience": 7,
            "preferred_titles": ["Backend Engineer"],
            "remote_preference": "remote",
            "expected_salary_min": 3000000,
            "expected_salary_max": 4500000,
            "currency": "inr",
            "github_url": "https://github.com/ada",
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["currency"] == "INR"
    assert body["github_url"] == "https://github.com/ada"

    patch = await client.patch(PROFILE, headers=user.headers, json={"current_company": "Acme"})
    assert patch.status_code == 200
    body = patch.json()
    assert body["current_company"] == "Acme"
    assert body["headline"] == "Senior Python Engineer"  # untouched

    # PUT resets omitted fields.
    reset = await client.put(PROFILE, headers=user.headers, json={"headline": "Only this"})
    assert reset.json()["current_company"] is None
    assert reset.json()["remote_preference"] == "any"


async def test_patch_salary_validated_against_stored_values(
    client: AsyncClient, user: RegisteredUser
) -> None:
    await client.patch(
        PROFILE,
        headers=user.headers,
        json={"expected_salary_min": 100, "expected_salary_max": 200, "currency": "USD"},
    )
    bad = await client.patch(PROFILE, headers=user.headers, json={"expected_salary_min": 500})
    assert bad.status_code == 422
    assert "must not exceed" in bad.json()["error"]["message"]


async def test_experience_crud(client: AsyncClient, user: RegisteredUser) -> None:
    created = await client.post(
        f"{PROFILE}/experiences",
        headers=user.headers,
        json={
            "company": "Acme",
            "title": "Backend Engineer",
            "start_date": "2019-04-01",
            "end_date": "2022-06-30",
            "technologies": ["Python", "Django", "python"],
        },
    )
    assert created.status_code == 201, created.text
    exp = created.json()
    assert exp["technologies"] == ["Python", "Django"]

    # Marking as current clears end_date automatically.
    updated = await client.patch(
        f"{PROFILE}/experiences/{exp['id']}", headers=user.headers, json={"is_current": True}
    )
    assert updated.status_code == 200
    assert updated.json()["end_date"] is None and updated.json()["is_current"] is True

    invalid = await client.patch(
        f"{PROFILE}/experiences/{exp['id']}", headers=user.headers, json={"end_date": "2018-01-01"}
    )
    assert invalid.status_code == 422

    listing = await client.get(f"{PROFILE}/experiences", headers=user.headers)
    assert [e["id"] for e in listing.json()] == [exp["id"]]
    profile = await client.get(PROFILE, headers=user.headers)
    assert len(profile.json()["experiences"]) == 1

    deleted = await client.delete(f"{PROFILE}/experiences/{exp['id']}", headers=user.headers)
    assert deleted.status_code == 204
    missing = await client.delete(f"{PROFILE}/experiences/{exp['id']}", headers=user.headers)
    assert missing.status_code == 404


async def test_education_crud(client: AsyncClient, user: RegisteredUser) -> None:
    created = await client.post(
        f"{PROFILE}/education",
        headers=user.headers,
        json={
            "institution": "IIT",
            "degree": "B.Tech",
            "field_of_study": "CS",
            "start_date": "2012-07-01",
            "end_date": "2016-05-01",
        },
    )
    assert created.status_code == 201
    edu_id = created.json()["id"]
    updated = await client.patch(
        f"{PROFILE}/education/{edu_id}", headers=user.headers, json={"grade": "8.9 CGPA"}
    )
    assert updated.json()["grade"] == "8.9 CGPA"
    bad = await client.patch(
        f"{PROFILE}/education/{edu_id}", headers=user.headers, json={"end_date": "2010-01-01"}
    )
    assert bad.status_code == 422
    assert (
        await client.delete(f"{PROFILE}/education/{edu_id}", headers=user.headers)
    ).status_code == 204


async def test_skills_are_unique_case_insensitively(
    client: AsyncClient, user: RegisteredUser
) -> None:
    first = await client.post(
        f"{PROFILE}/skills",
        headers=user.headers,
        json={"name": "Python", "years": 7, "proficiency": "expert"},
    )
    assert first.status_code == 201
    dup = await client.post(f"{PROFILE}/skills", headers=user.headers, json={"name": "  python "})
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "skill_exists"

    second = await client.post(f"{PROFILE}/skills", headers=user.headers, json={"name": "Django"})
    rename_clash = await client.patch(
        f"{PROFILE}/skills/{second.json()['id']}", headers=user.headers, json={"name": "PYTHON"}
    )
    assert rename_clash.status_code == 409

    rename_ok = await client.patch(
        f"{PROFILE}/skills/{second.json()['id']}",
        headers=user.headers,
        json={"name": "Django REST", "years": 4},
    )
    assert rename_ok.status_code == 200
    names = [
        s["name"] for s in (await client.get(f"{PROFILE}/skills", headers=user.headers)).json()
    ]
    assert names == ["Django REST", "Python"]
