from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from httpx import AsyncClient

from app.ai.llm.base import LLMNotConfiguredError, LLMUnavailableError
from app.core.config import Settings
from tests.conftest import RegisteredUser, RegisterFn
from tests.resume_fixtures import ScriptedLLM, make_blank_pdf, make_docx, make_pdf, parsed_resume

RESUMES = "/api/v1/resumes"
PDF = "application/pdf"


async def upload(
    client: AsyncClient,
    user: RegisteredUser,
    data: bytes | None = None,
    *,
    filename: str = "Priya_Sharma_Resume.pdf",
    name: str | None = None,
) -> Any:
    form = {"name": name} if name else None
    return await client.post(
        RESUMES,
        headers=user.headers,
        files={"file": (filename, data if data is not None else make_pdf(), PDF)},
        data=form,
    )


# ------------------------------------------------------------------ upload + parse


async def test_upload_parses_and_grounds(
    client: AsyncClient, user: RegisteredUser, llm: ScriptedLLM
) -> None:
    response = await upload(client, user)
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["name"] == "Priya Sharma Resume"  # from the filename
    assert body["file_type"] == "pdf"
    assert body["is_default"] is True  # first resume
    assert body["parse_status"] == "parsed"
    assert body["parser"] == "scripted:test-model"

    detail = (await client.get(f"{RESUMES}/{body['id']}", headers=user.headers)).json()
    assert detail["parsed"]["skills"][0] == {
        "name": "Python",
        "years": 7.0,
        "evidence": "Python - 7 years",
    }
    assert detail["pending_review"] > 0
    # The model saw the extracted resume text, wrapped as data.
    assert "<resume>" in llm.prompts[0] and "Acme Fintech" in llm.prompts[0]


async def test_docx_upload_works(client: AsyncClient, user: RegisteredUser) -> None:
    response = await upload(client, user, make_docx(), filename="cv.docx")
    assert response.status_code == 202
    assert response.json()["file_type"] == "docx"
    assert response.json()["parse_status"] == "parsed"


async def test_fabricated_values_never_reach_stored_data(
    client: AsyncClient, user: RegisteredUser, llm: ScriptedLLM
) -> None:
    llm.result = parsed_resume(
        skills=[
            {"name": "Python", "years": 7, "evidence": "Python - 7 years"},
            {"name": "Rust", "years": 9, "evidence": "Rust - 9 years"},
        ]
    )
    resume_id = (await upload(client, user)).json()["id"]
    detail = (await client.get(f"{RESUMES}/{resume_id}", headers=user.headers)).json()
    assert [s["name"] for s in detail["parsed"]["skills"]] == ["Python"]


async def test_download_returns_the_original_bytes(
    client: AsyncClient, user: RegisteredUser
) -> None:
    original = make_pdf()
    resume_id = (await upload(client, user, original, filename="My CV (2026).pdf")).json()["id"]
    response = await client.get(f"{RESUMES}/{resume_id}/file", headers=user.headers)
    assert response.status_code == 200
    assert response.content == original
    assert response.headers["content-type"] == PDF
    assert "My%20CV%20%282026%29.pdf" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "private, no-store"


async def test_stored_file_is_encrypted(
    client: AsyncClient, user: RegisteredUser, settings: Settings
) -> None:
    await upload(client, user)
    stored = [p for p in Path(settings.storage_local_path).rglob("*") if p.is_file()]
    assert len(stored) == 1
    assert not stored[0].read_bytes().startswith(b"%PDF")


# ------------------------------------------------------------------ validation


async def test_rejects_non_documents_by_content(client: AsyncClient, user: RegisteredUser) -> None:
    response = await upload(client, user, b"MZ\x90\x00 an executable", filename="resume.pdf")
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


async def test_rejects_empty_and_oversized(
    client: AsyncClient, user: RegisteredUser, settings: Settings
) -> None:
    empty = await upload(client, user, b"")
    assert empty.status_code == 422 and empty.json()["error"]["code"] == "file_empty"

    too_big = b"%PDF-1.7\n" + b"0" * settings.resume_max_bytes
    response = await upload(client, user, too_big)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


async def test_rejects_duplicates_and_enforces_limit(
    client: AsyncClient, user: RegisteredUser, settings: Settings
) -> None:
    assert (await upload(client, user)).status_code == 202
    duplicate = await upload(client, user)
    assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "resume_duplicate"

    settings.resume_max_per_user = 2
    assert (await upload(client, user, make_docx())).status_code == 202
    third = await upload(client, user, make_pdf(["Another", "resume text"] * 30))
    assert third.status_code == 409 and third.json()["error"]["code"] == "resume_limit_reached"


# ------------------------------------------------------------------ failures


async def test_ai_not_configured_is_a_clear_failure_that_can_be_retried(
    client: AsyncClient, user: RegisteredUser, llm: ScriptedLLM
) -> None:
    llm.error = LLMNotConfiguredError(
        "AI features aren't set up yet, so this couldn't be processed."
    )
    body = (await upload(client, user)).json()
    assert body["parse_status"] == "failed"
    assert body["parse_error_code"] == "ai_not_configured"
    assert "aren't set up" in body["parse_error"]

    llm.error = None
    retried = await client.post(f"{RESUMES}/{body['id']}/parse", headers=user.headers)
    assert retried.status_code == 202
    assert retried.json()["parse_status"] == "parsed"


async def test_ai_outage_failure_message(
    client: AsyncClient, user: RegisteredUser, llm: ScriptedLLM
) -> None:
    llm.error = LLMUnavailableError(
        "The AI service is busy right now. Please try again in a few minutes."
    )
    body = (await upload(client, user)).json()
    assert body["parse_status"] == "failed" and body["parse_error_code"] == "ai_unavailable"


async def test_scanned_pdf_explains_no_text(
    client: AsyncClient, user: RegisteredUser, llm: ScriptedLLM
) -> None:
    body = (await upload(client, user, make_blank_pdf())).json()
    assert body["parse_status"] == "failed"
    assert body["parse_error_code"] == "no_text"
    assert "scanned" in body["parse_error"]
    assert llm.prompts == []  # no AI call for an empty document


async def test_queue_outage_marks_resume_failed(
    client: AsyncClient, user: RegisteredUser, app: Any
) -> None:
    class BrokenDispatcher:
        async def dispatch(self, resume_id: Any) -> None:
            raise ConnectionError("broker down")

    app.state.parse_dispatcher = BrokenDispatcher()
    body = (await upload(client, user)).json()
    assert body["parse_status"] == "failed" and body["parse_error_code"] == "queue_unavailable"


# ------------------------------------------------------------------ manage


async def test_default_switching_rename_and_delete(
    client: AsyncClient, user: RegisteredUser, settings: Settings
) -> None:
    first = (await upload(client, user, name="Backend")).json()
    second = (
        await upload(client, user, make_docx(), filename="general.docx", name="General")
    ).json()
    assert second["is_default"] is False

    made_default = await client.patch(
        f"{RESUMES}/{second['id']}",
        headers=user.headers,
        json={"is_default": True, "name": "General CV"},
    )
    assert made_default.json()["is_default"] is True and made_default.json()["name"] == "General CV"
    listing = (await client.get(RESUMES, headers=user.headers)).json()
    assert [r["id"] for r in listing] == [second["id"], first["id"]]  # default first
    assert [r["is_default"] for r in listing] == [True, False]

    # Deleting the default promotes the remaining resume and removes the stored file.
    assert (
        await client.delete(f"{RESUMES}/{second['id']}", headers=user.headers)
    ).status_code == 204
    remaining = (await client.get(RESUMES, headers=user.headers)).json()
    assert [(r["id"], r["is_default"]) for r in remaining] == [(first["id"], True)]
    assert len([p for p in Path(settings.storage_local_path).rglob("*") if p.is_file()]) == 1


async def test_cannot_unset_default_directly(client: AsyncClient, user: RegisteredUser) -> None:
    resume_id = (await upload(client, user)).json()["id"]
    response = await client.patch(
        f"{RESUMES}/{resume_id}", headers=user.headers, json={"is_default": False}
    )
    assert response.status_code == 422


async def test_resumes_are_private(client: AsyncClient, register_user: RegisterFn) -> None:
    owner = await register_user()
    other = await register_user()
    resume_id = (await upload(client, owner)).json()["id"]

    for method, path in [
        ("GET", f"{RESUMES}/{resume_id}"),
        ("GET", f"{RESUMES}/{resume_id}/file"),
        ("GET", f"{RESUMES}/{resume_id}/review"),
        ("POST", f"{RESUMES}/{resume_id}/parse"),
        ("DELETE", f"{RESUMES}/{resume_id}"),
    ]:
        response = await client.request(method, path, headers=other.headers)
        assert response.status_code == 404, (method, path)
    assert (await client.get(RESUMES, headers=other.headers)).json() == []
    assert (await client.get(RESUMES)).status_code == 401


# ------------------------------------------------------------------ review


@pytest.fixture
async def profile_user(client: AsyncClient, user: RegisteredUser) -> RegisteredUser:
    """A user whose profile disagrees with the resume on a couple of points."""
    await client.patch(
        "/api/v1/profile",
        headers=user.headers,
        json={"years_of_experience": 5, "current_title": "Backend Engineer"},
    )
    await client.post(
        "/api/v1/profile/skills", headers=user.headers, json={"name": "Python", "years": 5}
    )
    return user


async def test_review_lists_conflicts_and_additions(
    client: AsyncClient, profile_user: RegisteredUser
) -> None:
    resume_id = (await upload(client, profile_user)).json()["id"]
    items = (
        await client.get(f"{RESUMES}/{resume_id}/review", headers=profile_user.headers)
    ).json()["items"]
    by_field: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_field.setdefault(item["field"], []).append(item)

    python = by_field["skill.years"][0]
    assert python["kind"] == "conflict"
    assert python["profile_value"] == "5 years" and python["resume_value"] == "7 years"
    assert (
        python["question"]
        == "Profile and resume contain different experience values. Which should be used?"
    )
    assert python["evidence"] == "Python - 7 years"

    assert by_field["years_of_experience"][0]["kind"] == "conflict"
    assert by_field["current_title"][0]["resume_value"] == "Senior Backend Engineer"
    assert {i["resume_value"] for i in by_field["skill.add"]} == {"Django (5 years)", "AWS"}
    assert len(by_field["experience.add"]) == 2
    assert (
        by_field["education.add"][0]["resume_value"]
        == "B.Tech, Computer Science, NIT Trichy (2018)"
    )
    assert {i["field"] for i in items} >= {"link.linkedin", "link.github", "headline", "summary"}


async def test_applying_decisions_updates_profile_only_where_chosen(
    client: AsyncClient, profile_user: RegisteredUser
) -> None:
    headers = profile_user.headers
    resume_id = (await upload(client, profile_user)).json()["id"]
    items = (await client.get(f"{RESUMES}/{resume_id}/review", headers=headers)).json()["items"]
    pick = {i["field"] + ":" + i["resume_value"]: i["id"] for i in items}

    decisions = [
        {"id": pick["skill.years:7 years"], "action": "use_resume"},
        {"id": pick["years_of_experience:7 years"], "action": "keep_profile"},
        {"id": pick["skill.add:Django (5 years)"], "action": "add"},
        {"id": pick["skill.add:AWS"], "action": "skip"},
        {
            "id": next(v for k, v in pick.items() if k.startswith("experience.add:Senior")),
            "action": "add",
        },
        {"id": pick["education.add:B.Tech, Computer Science, NIT Trichy (2018)"], "action": "add"},
    ]
    result = (
        await client.post(
            f"{RESUMES}/{resume_id}/review", headers=headers, json={"decisions": decisions}
        )
    ).json()
    assert result["applied"] == 4 and result["skipped"] == 2 and result["errors"] == []
    remaining_ids = {i["id"] for i in result["review"]["items"]}
    assert not remaining_ids & {d["id"] for d in decisions}  # decided items don't come back

    profile = (await client.get("/api/v1/profile", headers=headers)).json()
    skills = {s["name"]: s["years"] for s in profile["skills"]}
    assert skills == {"Python": 7.0, "Django": 5.0}  # AWS skipped
    assert profile["years_of_experience"] == 5.0  # kept the profile value
    [experience] = profile["experiences"]
    assert experience["company"] == "Acme Fintech" and experience["is_current"] is True
    assert experience["start_date"] == "2021-06-01"
    [education] = profile["education"]
    assert education["institution"] == "NIT Trichy" and education["end_date"] == "2018-01-01"

    # Unknown or already-decided ids are ignored rather than applied twice.
    again = await client.post(
        f"{RESUMES}/{resume_id}/review", headers=headers, json={"decisions": decisions}
    )
    assert again.json()["applied"] == 0


async def test_review_requires_a_parsed_resume(
    client: AsyncClient, user: RegisteredUser, llm: ScriptedLLM
) -> None:
    llm.error = LLMNotConfiguredError("not configured")
    resume_id = (await upload(client, user)).json()["id"]
    assert (await client.get(f"{RESUMES}/{resume_id}/review", headers=user.headers)).json()[
        "items"
    ] == []
    response = await client.post(
        f"{RESUMES}/{resume_id}/review",
        headers=user.headers,
        json={"decisions": [{"id": "x", "action": "add"}]},
    )
    assert response.status_code == 409


async def test_reparse_resets_review_decisions(
    client: AsyncClient, profile_user: RegisteredUser
) -> None:
    headers = profile_user.headers
    resume_id = (await upload(client, profile_user)).json()["id"]
    items = (await client.get(f"{RESUMES}/{resume_id}/review", headers=headers)).json()["items"]
    await client.post(
        f"{RESUMES}/{resume_id}/review",
        headers=headers,
        json={"decisions": [{"id": i["id"], "action": "skip"} for i in items]},
    )
    assert (await client.get(f"{RESUMES}/{resume_id}/review", headers=headers)).json()[
        "items"
    ] == []
    # Parsing again is a no-op for an already-parsed resume (idempotent)...
    reparsed = await client.post(f"{RESUMES}/{resume_id}/parse", headers=headers)
    assert reparsed.json()["parse_status"] == "parsed"
