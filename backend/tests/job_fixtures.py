"""Fake Greenhouse / Lever job boards, shaped like the real public APIs.

`FakeBoards` is mutable, so tests can post, edit or withdraw jobs between searches.
It serves both an `httpx.MockTransport` (unit/API tests) and plain dicts for the
e2e fake server (tests/fake_llm_server.py).
"""

from __future__ import annotations

import copy
import html
import json
import re
from typing import Any

import httpx

from app.ai.jobs.analyzer import AnalyzedRequirement, JobAnalysisExtraction

BACKEND_JD = """
<h2>About the role</h2>
<p>Acme is hiring a Senior Backend Engineer to build our payments platform.
This is a remote role within India.</p>
<h3>What you'll do</h3>
<ul><li>Design and run Python services on AWS</li><li>Own our PostgreSQL data model</li></ul>
<h3>Requirements</h3>
<ul>
<li>5+ years of experience building backend systems</li>
<li>Strong Python and PostgreSQL skills</li>
<li>Experience with Docker and Kubernetes</li>
</ul>
<h3>Nice to have</h3>
<ul><li>Kafka or RabbitMQ experience is a plus</li></ul>
<h3>Benefits</h3>
<ul><li>Health insurance for you and your family</li></ul>
<p>Compensation: 30 - 45 LPA.</p>
"""

FRONTEND_JD = """
<p>Join our web team as a Frontend Engineer.</p>
<h3>Requirements</h3>
<ul><li>3+ years of experience with React and TypeScript</li><li>CSS and HTML</li></ul>
"""

SALES_JD = """
<p>We need an Account Executive to grow revenue in the Bengaluru market.</p>
<h3>Requirements</h3><ul><li>4+ years of B2B sales experience</li></ul>
"""


def _gh(job_id: int, title: str, location: str, content: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": job_id,
        "internal_job_id": job_id + 1000,
        "title": title,
        "company_name": "Acme",
        "location": {"name": location},
        "absolute_url": f"https://boards.greenhouse.io/acme/jobs/{job_id}",
        "first_published": "2026-09-20T10:00:00-04:00",
        "updated_at": "2026-09-25T10:00:00-04:00",
        "departments": [{"id": 1, "name": "Engineering"}],
        "offices": [],
        "metadata": None,
        "requisition_id": None,
        "data_compliance": [],
        # Greenhouse returns HTML with entities escaped.
        "content": html.escape(content),
        **extra,
    }


def _lever(posting_id: str, title: str, location: str, text: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": posting_id,
        "text": title,
        "categories": {"location": location, "commitment": "Full-time", "team": "Engineering"},
        "workplaceType": extra.pop("workplaceType", "onsite"),
        "descriptionPlain": text,
        "description": f"<p>{html.escape(text)}</p>",
        "lists": extra.pop("lists", []),
        "additionalPlain": "",
        "hostedUrl": f"https://jobs.lever.co/globex/{posting_id}",
        "applyUrl": f"https://jobs.lever.co/globex/{posting_id}/apply",
        "createdAt": 1_758_000_000_000,
        **extra,
    }


def default_boards() -> dict[str, dict[str, Any]]:
    return {
        "greenhouse:acme": {
            "name": "Acme",
            "jobs": [
                _gh(101, "Senior Backend Engineer", "Remote - India", BACKEND_JD),
                _gh(102, "Frontend Engineer", "Bengaluru, India", FRONTEND_JD),
                _gh(103, "Account Executive", "Bengaluru, India", SALES_JD),
            ],
        },
        "lever:globex": {
            "name": "Globex",
            "jobs": [
                _lever(
                    "a1b2c3",
                    "Python Developer",
                    "Pune, India",
                    "Build data pipelines in Python and Airflow. 2+ years of experience required.",
                    lists=[{"text": "Requirements", "content": "<li>Python</li><li>SQL</li>"}],
                ),
                _lever(
                    "d4e5f6",
                    "Staff Software Engineer",
                    "Remote",
                    "Lead our platform team. 8+ years of experience with Go and Kubernetes.",
                    workplaceType="remote",
                ),
            ],
        },
    }


class FakeBoards:
    def __init__(self) -> None:
        self.boards = default_boards()
        self.failing: set[str] = set()  # "platform:board" keys that return 500
        self.requests: list[str] = []

    def board(self, key: str) -> dict[str, Any]:
        return self.boards[key]

    def remove_job(self, key: str, job_id: Any) -> None:
        self.boards[key]["jobs"] = [j for j in self.boards[key]["jobs"] if j["id"] != job_id]

    # ---- responses, shared by the MockTransport and the e2e server

    def respond(self, path: str) -> tuple[int, Any]:
        self.requests.append(path)
        gh = re.fullmatch(r"/v1/boards/([^/]+)(/jobs)?/?", path)
        if gh:
            key = f"greenhouse:{gh.group(1)}"
            if key in self.failing:
                return 500, {"error": "boom"}
            if key not in self.boards:
                return 404, {"status": 404, "error": "Job not found"}
            if gh.group(2):
                return 200, {"jobs": copy.deepcopy(self.boards[key]["jobs"]), "meta": {"total": 0}}
            return 200, {"name": self.boards[key]["name"], "content": ""}
        lever = re.fullmatch(r"/v0/postings/([^/]+)/?", path)
        if lever:
            key = f"lever:{lever.group(1)}"
            if key in self.failing:
                return 500, {"error": "boom"}
            if key not in self.boards:
                return 404, {"ok": False, "error": "Document not found"}
            return 200, copy.deepcopy(self.boards[key]["jobs"])
        return 404, {"error": "not found"}

    def transport(self) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            status, body = self.respond(request.url.path)
            return httpx.Response(
                status,
                content=json.dumps(body).encode(),
                headers={"content-type": "application/json"},
            )

        return httpx.MockTransport(handler)


def job_analysis() -> JobAnalysisExtraction:
    """What a model might return for BACKEND_JD, including one invented 'explicit' item."""
    return JobAnalysisExtraction(
        summary="A senior backend role building Acme's payments platform, remote within India.",
        seniority="senior",
        seniority_basis="explicit",
        seniority_evidence="Senior Backend Engineer",
        requirements=[
            AnalyzedRequirement(
                text="5+ years of backend experience",
                category="experience",
                importance="required",
                basis="explicit",
                evidence="5+ years of experience building backend systems",
            ),
            AnalyzedRequirement(
                text="Python and PostgreSQL",
                category="skill",
                importance="required",
                basis="explicit",
                evidence="Strong Python and PostgreSQL skills",
            ),
            AnalyzedRequirement(
                text="Kafka or RabbitMQ",
                category="skill",
                importance="preferred",
                basis="explicit",
                evidence="Kafka or RabbitMQ experience is a plus",
            ),
            AnalyzedRequirement(  # not in the posting: must be downgraded to inferred
                text="Computer science degree",
                category="education",
                importance="required",
                basis="explicit",
                evidence="BS in Computer Science required",
            ),
            AnalyzedRequirement(
                text="Payments domain knowledge",
                category="other",
                importance="preferred",
                basis="inferred",
                evidence="payments platform",
            ),
        ],
        responsibilities=[
            "Design and run Python services on AWS",
            "Own our PostgreSQL data model",
            "Manage a team of twelve engineers across three continents",  # invented: dropped
        ],
        benefits=["Health insurance for you and your family"],
        work_authorization="unknown",
        work_authorization_basis="unknown",
        work_authorization_evidence="",
    )
