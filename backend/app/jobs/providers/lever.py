"""Lever public Postings API: https://github.com/lever/postings-api"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

import httpx

from app.jobs.html_text import html_to_text
from app.jobs.providers.base import get_json
from app.jobs.types import NormalizedJob, SearchQuery, WorkplaceType
from app.models.enums import EmploymentType

DEFAULT_BASE_URL = "https://api.lever.co"
_URL = re.compile(r"^(?:https?://)?jobs(?:\.eu)?\.lever\.co/(?P<token>[A-Za-z0-9_.-]+)", re.I)
_TOKEN = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,79}$")

# Long text fields, kept out of `raw` (the description already holds them as plain text).
_TEXT_FIELDS = frozenset(
    {
        "description", "descriptionPlain", "lists", "additional", "additionalPlain", "opening",
        "openingPlain", "descriptionBody", "descriptionBodyPlain",
    }
)  # fmt: skip

_WORKPLACE = {
    "remote": WorkplaceType.REMOTE,
    "hybrid": WorkplaceType.HYBRID,
    "onsite": WorkplaceType.ONSITE,
    "on-site": WorkplaceType.ONSITE,
}
_COMMITMENT = (
    ("intern", EmploymentType.INTERNSHIP),
    ("part", EmploymentType.PART_TIME),
    ("contract", EmploymentType.CONTRACT),
    ("temp", EmploymentType.TEMPORARY),
    ("freelance", EmploymentType.FREELANCE),
    ("full", EmploymentType.FULL_TIME),
    ("permanent", EmploymentType.FULL_TIME),
)


def _employment(commitment: str | None) -> EmploymentType | None:
    value = (commitment or "").casefold()
    return next((t for key, t in _COMMITMENT if key in value), None)


def _ms(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC) if value else None
    except (TypeError, ValueError, OverflowError):
        return None


class LeverProvider:
    platform = "lever"
    display_name = "Lever"

    def __init__(self, client: httpx.AsyncClient, base_url: str = DEFAULT_BASE_URL) -> None:
        self._client = client
        self._base = base_url.rstrip("/")

    def supports(self, source: str) -> str | None:
        source = source.strip()
        match = _URL.match(source)
        if match:
            return match.group("token").lower()
        prefixed = re.match(r"^lever:(?P<token>\S+)$", source, re.IGNORECASE)
        return prefixed.group("token").lower() if prefixed else None

    @staticmethod
    def valid_token(token: str) -> bool:
        return bool(_TOKEN.match(token))

    async def search(self, board: str, query: SearchQuery | None = None) -> list[NormalizedJob]:
        payload = await get_json(
            self._client, f"{self._base}/v0/postings/{board}", params={"mode": "json"}
        )
        jobs = [self.normalize_job(raw, board) for raw in payload or []]
        return [j for j in jobs if query is None or query.matches(j)]

    async def get_job(self, board: str, external_id: str) -> NormalizedJob | None:
        raw = await get_json(self._client, f"{self._base}/v0/postings/{board}/{external_id}")
        return self.normalize_job(raw, board) if raw else None

    async def company_name(self, board: str) -> str:
        # Lever has no board-metadata endpoint; the token is the company's slug.
        await self.search(board)  # raises BoardNotFoundError if the board doesn't exist
        return board.replace("-", " ").title()

    def normalize_job(self, raw: dict[str, Any], board: str) -> NormalizedJob:
        categories = raw.get("categories") or {}
        sections = [raw.get("descriptionPlain") or html_to_text(raw.get("description"))]
        for item in raw.get("lists") or []:
            heading = (item.get("text") or "").strip()
            body = html_to_text(item.get("content"))
            sections.append(f"{heading}\n{body}" if heading else body)
        sections.append(raw.get("additionalPlain") or html_to_text(raw.get("additional")))
        salary = raw.get("salaryRange") or {}
        annual = (salary.get("interval") or "per-year-salary").startswith("per-year")
        trimmed = {k: v for k, v in raw.items() if k not in _TEXT_FIELDS}
        return NormalizedJob(
            platform=self.platform,
            external_id=str(raw["id"]),
            board=board,
            company=board.replace("-", " ").title(),
            title=(raw.get("text") or "").strip(),
            location=(categories.get("location") or "").strip() or None,
            workplace=_WORKPLACE.get(
                (raw.get("workplaceType") or "").casefold(), WorkplaceType.UNKNOWN
            ),
            employment_type=_employment(categories.get("commitment")),
            description="\n\n".join(s for s in sections if s).strip(),
            application_url=raw.get("hostedUrl") or raw.get("applyUrl") or "",
            posted_at=_ms(raw.get("createdAt")),
            updated_at=_ms(raw.get("updatedAt")) or _ms(raw.get("createdAt")),
            department=categories.get("team") or categories.get("department"),
            salary_min=int(salary["min"]) if annual and salary.get("min") else None,
            salary_max=int(salary["max"]) if annual and salary.get("max") else None,
            salary_currency=(salary.get("currency") or None) if annual and salary else None,
            raw=trimmed,
        )
