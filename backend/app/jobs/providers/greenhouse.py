"""Greenhouse public Job Board API: https://developers.greenhouse.io/job-board.html"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

from app.jobs.html_text import html_to_text
from app.jobs.providers.base import get_json
from app.jobs.types import NormalizedJob, SearchQuery, WorkplaceType

DEFAULT_BASE_URL = "https://boards-api.greenhouse.io"
_URL = re.compile(
    r"^(?:https?://)?(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?"
    r"(?P<token>[A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_TOKEN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,79}$")


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


class GreenhouseProvider:
    platform = "greenhouse"
    display_name = "Greenhouse"

    def __init__(self, client: httpx.AsyncClient, base_url: str = DEFAULT_BASE_URL) -> None:
        self._client = client
        self._base = base_url.rstrip("/")

    def supports(self, source: str) -> str | None:
        source = source.strip()
        match = _URL.match(source)
        if match:
            return match.group("token").lower()
        prefixed = re.match(r"^greenhouse:(?P<token>\S+)$", source, re.IGNORECASE)
        return prefixed.group("token").lower() if prefixed else None

    @staticmethod
    def valid_token(token: str) -> bool:
        return bool(_TOKEN.match(token))

    async def search(self, board: str, query: SearchQuery | None = None) -> list[NormalizedJob]:
        payload = await get_json(
            self._client, f"{self._base}/v1/boards/{board}/jobs", params={"content": "true"}
        )
        jobs = [self.normalize_job(raw, board) for raw in payload.get("jobs", [])]
        return [j for j in jobs if query is None or query.matches(j)]

    async def get_job(self, board: str, external_id: str) -> NormalizedJob | None:
        raw = await get_json(self._client, f"{self._base}/v1/boards/{board}/jobs/{external_id}")
        return self.normalize_job(raw, board) if raw else None

    async def company_name(self, board: str) -> str:
        payload = await get_json(self._client, f"{self._base}/v1/boards/{board}")
        return (payload.get("name") or board).strip()

    def normalize_job(self, raw: dict[str, Any], board: str) -> NormalizedJob:
        location = ((raw.get("location") or {}).get("name") or "").strip() or None
        departments = raw.get("departments") or []
        trimmed = {k: v for k, v in raw.items() if k not in ("content", "data_compliance")}
        return NormalizedJob(
            platform=self.platform,
            external_id=str(raw["id"]),
            board=board,
            company=(raw.get("company_name") or board).strip(),
            title=(raw.get("title") or "").strip(),
            location=location,
            # Greenhouse has no workplace field; extract.py reads location/description.
            workplace=WorkplaceType.UNKNOWN,
            employment_type=None,
            description=html_to_text(raw.get("content"), escaped=True),
            application_url=raw.get("absolute_url") or "",
            posted_at=_dt(raw.get("first_published")),
            updated_at=_dt(raw.get("updated_at")),
            department=departments[0].get("name") if departments else None,
            raw=trimmed,
        )
