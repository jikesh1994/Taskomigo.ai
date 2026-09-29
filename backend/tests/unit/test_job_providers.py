from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio

from app.ai.jobs.analyzer import ground_analysis
from app.jobs.html_text import html_to_text
from app.jobs.providers import BoardNotFoundError, ProviderError, parse_source
from app.jobs.providers.base import get_json
from app.jobs.providers.greenhouse import GreenhouseProvider
from app.jobs.providers.lever import LeverProvider
from app.jobs.types import SearchQuery, WorkplaceType
from app.models.enums import EmploymentType
from tests.job_fixtures import BACKEND_JD, FakeBoards, job_analysis


@pytest_asyncio.fixture
async def client() -> AsyncIterator[tuple[httpx.AsyncClient, FakeBoards]]:
    boards = FakeBoards()
    async with httpx.AsyncClient(transport=boards.transport()) as http:
        yield http, boards


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("https://boards.greenhouse.io/Stripe", ("greenhouse", "stripe")),
        ("https://job-boards.eu.greenhouse.io/acme/jobs/123", ("greenhouse", "acme")),
        ("boards.greenhouse.io/embed/job_board?for=figma", ("greenhouse", "figma")),
        ("greenhouse:discord", ("greenhouse", "discord")),
        ("https://jobs.lever.co/spotify/abc-123", ("lever", "spotify")),
        ("https://jobs.eu.lever.co/zeta", ("lever", "zeta")),
        ("lever:cred", ("lever", "cred")),
        ("https://www.linkedin.com/jobs/view/123", None),
        ("stripe", None),
    ],
)
def test_parse_source(source: str, expected: tuple[str, str] | None) -> None:
    http = httpx.AsyncClient()
    providers = {"greenhouse": GreenhouseProvider(http), "lever": LeverProvider(http)}
    assert parse_source(providers, source) == expected  # type: ignore[arg-type]


async def test_greenhouse_normalizes_jobs(client: tuple[httpx.AsyncClient, FakeBoards]) -> None:
    http, _ = client
    provider = GreenhouseProvider(http, "https://boards-api.greenhouse.io")
    jobs = await provider.search("acme")
    assert len(jobs) == 3
    job = jobs[0]
    assert (job.platform, job.external_id, job.board) == ("greenhouse", "101", "acme")
    assert job.company == "Acme" and job.title == "Senior Backend Engineer"
    assert job.location == "Remote - India" and job.department == "Engineering"
    assert job.application_url == "https://boards.greenhouse.io/acme/jobs/101"
    assert "• Strong Python and PostgreSQL skills" in job.description
    assert "<" not in job.description and "&lt;" not in job.description
    assert job.posted_at is not None and job.posted_at.utcoffset() is not None
    assert "content" not in job.raw  # the long HTML isn't kept twice
    assert await provider.company_name("acme") == "Acme"
    only_sales = await provider.search("acme", SearchQuery(keywords=("revenue",)))
    assert [j.title for j in only_sales] == ["Account Executive"]


async def test_lever_normalizes_jobs(client: tuple[httpx.AsyncClient, FakeBoards]) -> None:
    http, _ = client
    provider = LeverProvider(http, "https://api.lever.co")
    jobs = await provider.search("globex")
    python, staff = jobs
    assert python.external_id == "a1b2c3" and python.company == "Globex"
    assert python.employment_type is EmploymentType.FULL_TIME
    assert python.workplace is WorkplaceType.ONSITE
    assert "Requirements" in python.description and "• SQL" in python.description
    assert python.application_url == "https://jobs.lever.co/globex/a1b2c3"  # the posting page
    assert staff.workplace is WorkplaceType.REMOTE
    assert await provider.company_name("globex") == "Globex"


async def test_errors_are_user_safe(client: tuple[httpx.AsyncClient, FakeBoards]) -> None:
    http, boards = client
    provider = GreenhouseProvider(http, "https://boards-api.greenhouse.io")
    with pytest.raises(BoardNotFoundError):
        await provider.search("nope")
    boards.failing.add("greenhouse:acme")
    with pytest.raises(ProviderError) as exc:
        await provider.search("acme")
    assert exc.value.message == "The job board returned an error."


async def test_timeouts_and_bad_json() -> None:
    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as http:
        with pytest.raises(ProviderError, match="too long"):
            await get_json(http, "https://example.test/x")

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"<html>"))
    ) as http:
        with pytest.raises(ProviderError, match="unreadable"):
            await get_json(http, "https://example.test/x")


def test_analysis_grounding_downgrades_unsupported_evidence() -> None:
    posting = "Senior Backend Engineer\n" + html_to_text(BACKEND_JD)
    analysis = ground_analysis(job_analysis(), posting)
    by_text = {r.text: r for r in analysis.requirements}
    assert by_text["Python and PostgreSQL"].basis == "explicit"
    degree = by_text["Computer science degree"]
    assert (degree.basis, degree.evidence) == ("inferred", "")
    assert by_text["Payments domain knowledge"].evidence == ""  # inferred items carry no quote
    assert analysis.downgraded == 1
    assert (
        "Manage a team of twelve engineers across three continents" not in analysis.responsibilities
    )
    assert "Own our PostgreSQL data model" in analysis.responsibilities
    assert analysis.seniority.basis == "explicit"
    assert analysis.work_authorization.value == "unknown"
