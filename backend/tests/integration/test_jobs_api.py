from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from app.core.database import Database
from app.jobs.extract import EXTRACTOR_VERSION
from app.models.job import Job
from tests.conftest import RegisteredUser, RegisterFn
from tests.job_fixtures import FakeBoards
from tests.resume_fixtures import ScriptedLLM

API = "/api/v1"


async def _profile(client: AsyncClient, user: RegisteredUser, **overrides: Any) -> None:
    profile = {
        "years_of_experience": 7,
        "preferred_titles": ["Backend Engineer", "Software Engineer"],
        "preferred_locations": ["Bengaluru"],
        "remote_preference": "remote",
        **overrides,
    }
    response = await client.patch(f"{API}/profile", json=profile, headers=user.headers)
    assert response.status_code == 200, response.text
    for name, years in (("Python", 6), ("postgres", None), ("Docker", 3)):
        response = await client.post(
            f"{API}/profile/skills", json={"name": name, "years": years}, headers=user.headers
        )
        assert response.status_code == 201, response.text


async def _add_sources(client: AsyncClient, user: RegisteredUser) -> list[dict[str, Any]]:
    added = []
    for source in ("https://boards.greenhouse.io/acme", "https://jobs.lever.co/globex"):
        response = await client.post(
            f"{API}/job-sources", json={"source": source}, headers=user.headers
        )
        assert response.status_code == 201, response.text
        added.append(response.json())
    return added


async def _search(client: AsyncClient, user: RegisteredUser) -> dict[str, Any]:
    response = await client.post(f"{API}/jobs/search", headers=user.headers)
    assert response.status_code == 202, response.text
    return response.json()


async def _jobs(client: AsyncClient, user: RegisteredUser, **params: Any) -> dict[str, Any]:
    response = await client.get(f"{API}/jobs", params=params, headers=user.headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_sources_validate_and_dedupe(client: AsyncClient, user: RegisteredUser) -> None:
    sources = await _add_sources(client, user)
    assert [(s["platform"], s["board"], s["company_name"]) for s in sources] == [
        ("greenhouse", "acme", "Acme"),
        ("lever", "globex", "Globex"),
    ]
    again = await client.post(
        f"{API}/job-sources", json={"source": "greenhouse:ACME"}, headers=user.headers
    )
    assert again.status_code == 409 and again.json()["error"]["code"] == "source_exists"
    missing = await client.post(
        f"{API}/job-sources", json={"source": "greenhouse:nope"}, headers=user.headers
    )
    assert missing.status_code == 422 and missing.json()["error"]["code"] == "source_not_found"
    linkedin = await client.post(
        f"{API}/job-sources",
        json={"source": "https://www.linkedin.com/jobs/view/1"},
        headers=user.headers,
    )
    assert linkedin.status_code == 422
    assert linkedin.json()["error"]["code"] == "unsupported_source"

    catalog = (await client.get(f"{API}/job-sources/catalog", headers=user.headers)).json()
    assert any(c["board"] == "stripe" and not c["added"] for c in catalog)


async def test_search_needs_sources(client: AsyncClient, user: RegisteredUser) -> None:
    response = await client.post(f"{API}/jobs/search", headers=user.headers)
    assert response.status_code == 422 and response.json()["error"]["code"] == "no_sources"


async def test_search_match_and_triage(
    client: AsyncClient, user: RegisteredUser, fake_boards: FakeBoards
) -> None:
    await _profile(client, user)
    await _add_sources(client, user)
    run = await _search(client, user)
    assert run["status"] == "succeeded"
    assert (run["sources_total"], run["sources_done"], run["jobs_fetched"]) == (2, 2, 5)
    assert run["jobs_new"] == 5 and run["matches"] == 5

    listing = await _jobs(client, user)
    titles = [j["title"] for j in listing["items"]]
    assert titles[0] == "Senior Backend Engineer"
    assert "Account Executive" not in titles  # filtered: unrelated title
    top = listing["items"][0]
    assert top["overall_match"] >= 70
    assert "Python required: on your profile (you have 6 years)" in top["reasons"]
    assert "PostgreSQL required: on your profile" in top["reasons"]  # "postgres" canonicalised
    assert "Kubernetes" in top["missing_requirements"]
    assert listing["counts"]["matches"] == listing["total"]

    hidden = await _jobs(client, user, tab="hidden")
    sales = next(j for j in hidden["items"] if j["title"] == "Account Executive")
    assert sales["excluded_reason"] == "Title doesn't match your target roles"

    detail = (await client.get(f"{API}/jobs/{top['id']}", headers=user.headers)).json()
    assert detail["facts"]["min_years"] == 5
    assert detail["facts"]["salary_currency"] == "INR"
    assert detail["facts"]["sponsorship"] is None
    assert detail["weights"]["skills"] == 40
    assert "• Strong Python and PostgreSQL skills" in detail["description"]
    assert detail["analysis_status"] == "none" and detail["analysis"] is None

    saved = await client.patch(
        f"{API}/jobs/{top['id']}", json={"status": "saved"}, headers=user.headers
    )
    assert saved.status_code == 200 and saved.json()["status"] == "saved"
    assert [j["id"] for j in (await _jobs(client, user, tab="saved"))["items"]] == [top["id"]]
    assert top["id"] not in [j["id"] for j in (await _jobs(client, user))["items"]]

    # Searching again keeps the user's decisions and finds nothing new.
    again = await _search(client, user)
    assert again["jobs_new"] == 0 and again["jobs_closed"] == 0
    assert (await _jobs(client, user, tab="saved"))["total"] == 1

    # A withdrawn posting is closed and leaves the lists (a saved one stays, marked closed).
    fake_boards.remove_job("greenhouse:acme", 101)
    fake_boards.remove_job("greenhouse:acme", 102)
    closed = await _search(client, user)
    assert closed["jobs_closed"] == 2
    saved_list = (await _jobs(client, user, tab="saved"))["items"]
    assert saved_list[0]["is_active"] is False
    assert "Frontend Engineer" not in [j["title"] for j in (await _jobs(client, user))["items"]]

    stats = (await client.get(f"{API}/jobs/stats", headers=user.headers)).json()
    assert stats["sources"] == 2 and stats["saved"] == 1
    assert stats["last_search"]["status"] == "succeeded"


async def test_preferences_and_weights_drive_rematch(
    client: AsyncClient, user: RegisteredUser
) -> None:
    await _profile(client, user)
    await _add_sources(client, user)
    await _search(client, user)
    before = {j["title"]: j for j in (await _jobs(client, user))["items"]}

    bad = await client.patch(
        f"{API}/preferences", json={"match_weights": {"luck": 5}}, headers=user.headers
    )
    assert bad.status_code == 422
    response = await client.patch(
        f"{API}/preferences",
        json={"remote_only": True, "match_weights": {"skills": 100, "experience": 0}},
        headers=user.headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["match_weights"] == {"skills": 100, "experience": 0}

    rematch = await client.post(f"{API}/jobs/rematch", headers=user.headers)
    assert rematch.status_code == 200 and rematch.json()["matched"] == 5
    after = {j["title"]: j for j in (await _jobs(client, user))["items"]}
    assert "Frontend Engineer" not in after  # on-site in Bengaluru; remote only now
    backend = after["Senior Backend Engineer"]
    assert backend["scores"] == before["Senior Backend Engineer"]["scores"]
    assert backend["overall_match"] != before["Senior Backend Engineer"]["overall_match"]


async def test_failed_sources_are_reported(
    client: AsyncClient, user: RegisteredUser, fake_boards: FakeBoards
) -> None:
    await _profile(client, user)
    await _add_sources(client, user)
    fake_boards.failing.add("lever:globex")
    run = await _search(client, user)
    assert run["status"] == "succeeded"
    assert run["source_errors"] == [
        {"source": "Globex", "message": "The job board returned an error."}
    ]
    sources = (await client.get(f"{API}/job-sources", headers=user.headers)).json()
    assert {s["board"]: s["last_error"] for s in sources}["globex"]

    fake_boards.failing.add("greenhouse:acme")
    failed = await _search(client, user)
    assert failed["status"] == "failed" and "None of your job boards" in failed["error"]


async def test_ai_analysis_is_grounded_and_cached(
    client: AsyncClient, user: RegisteredUser, llm: ScriptedLLM
) -> None:
    await _profile(client, user)
    await _add_sources(client, user)
    await _search(client, user)
    job = next(
        j for j in (await _jobs(client, user))["items"] if j["title"] == "Senior Backend Engineer"
    )
    response = await client.post(f"{API}/jobs/{job['id']}/analyze", headers=user.headers)
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["analysis_status"] == "done"
    requirements = {r["text"]: r for r in body["analysis"]["requirements"]}
    assert requirements["Computer science degree"]["basis"] == "inferred"
    assert requirements["Python and PostgreSQL"]["basis"] == "explicit"
    assert body["analysis"]["work_authorization"]["basis"] == "unknown"

    calls = len(llm.prompts)
    await client.post(f"{API}/jobs/{job['id']}/analyze", headers=user.headers)
    assert len(llm.prompts) == calls  # cached per job
    assert "<job_posting>" in llm.prompts[-1]


async def test_tenant_isolation(
    client: AsyncClient, user: RegisteredUser, register_user: RegisterFn
) -> None:
    await _profile(client, user)
    sources = await _add_sources(client, user)
    run = await _search(client, user)
    job_id = (await _jobs(client, user))["items"][0]["id"]

    other = await register_user()
    for method, url in (
        ("GET", f"{API}/jobs/{job_id}"),
        ("PATCH", f"{API}/jobs/{job_id}"),
        ("POST", f"{API}/jobs/{job_id}/analyze"),
        ("GET", f"{API}/jobs/search/{run['id']}"),
        ("PATCH", f"{API}/job-sources/{sources[0]['id']}"),
        ("DELETE", f"{API}/job-sources/{sources[0]['id']}"),
    ):
        body = {"status": "saved"} if "jobs/" in url else {"enabled": False}
        response = await client.request(
            method, url, headers=other.headers, json=body if method == "PATCH" else None
        )
        assert response.status_code == 404, (method, url, response.text)
    assert (await _jobs(client, other))["total"] == 0


async def test_removing_a_source_keeps_saved_jobs(
    client: AsyncClient, user: RegisteredUser
) -> None:
    await _profile(client, user)
    sources = await _add_sources(client, user)
    await _search(client, user)
    items = (await _jobs(client, user))["items"]
    acme = [j for j in items if j["company"] == "Acme"]
    await client.patch(
        f"{API}/jobs/{acme[0]['id']}", json={"status": "saved"}, headers=user.headers
    )

    response = await client.delete(f"{API}/job-sources/{sources[0]['id']}", headers=user.headers)
    assert response.status_code == 204
    remaining = (await _jobs(client, user))["items"]
    assert all(j["company"] != "Acme" for j in remaining)
    assert (await _jobs(client, user, tab="saved"))["items"][0]["id"] == acme[0]["id"]


@pytest.mark.parametrize("tab", ["matches", "saved", "skipped", "hidden"])
async def test_list_filters_are_accepted(
    client: AsyncClient, user: RegisteredUser, tab: str
) -> None:
    body = await _jobs(client, user, tab=tab, q="engineer", workplace="remote", sort="newest")
    assert body["items"] == [] and body["min_match_score"] == 60


async def test_extractor_upgrade_refreshes_facts_but_keeps_analysis(
    client: AsyncClient, user: RegisteredUser, database: Database
) -> None:
    await _profile(client, user)
    await _add_sources(client, user)
    await _search(client, user)
    job = next(
        j for j in (await _jobs(client, user))["items"] if j["title"] == "Senior Backend Engineer"
    )
    await client.post(f"{API}/jobs/{job['id']}/analyze", headers=user.headers)
    async with database.session_factory() as session:
        row = await session.get(Job, uuid.UUID(job["id"]))
        assert row is not None and row.facts["extractor_version"] == EXTRACTOR_VERSION
        row.facts = {**row.facts, "extractor_version": 0, "min_years": 99}
        await session.commit()

    await _search(client, user)
    detail = (await client.get(f"{API}/jobs/{job['id']}", headers=user.headers)).json()
    assert detail["facts"]["min_years"] == 5
    assert detail["analysis_status"] == "done" and detail["analysis"] is not None
