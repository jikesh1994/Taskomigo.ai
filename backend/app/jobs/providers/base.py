from __future__ import annotations

from typing import Any, Protocol

import httpx

from app.jobs.types import NormalizedJob, SearchQuery

USER_AGENT = "TaskomigoJobAgent/0.1 (+https://taskomigo.com; job search on behalf of users)"
MAX_RESPONSE_BYTES = 30 * 1024 * 1024  # a board listing is JSON; anything bigger is wrong


class ProviderError(Exception):
    """A board couldn't be fetched (network, 5xx, bad payload). `message` is user-safe."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class BoardNotFoundError(ProviderError):
    """The board token doesn't exist on the platform."""


class JobSearchProvider(Protocol):
    """One job platform. Every method returns the common `NormalizedJob` model."""

    platform: str
    display_name: str

    def supports(self, source: str) -> str | None:
        """The board token if `source` (a URL or token) belongs to this platform."""
        ...

    async def search(self, board: str, query: SearchQuery | None = None) -> list[NormalizedJob]:
        """All open jobs on the board (optionally narrowed by `query`)."""
        ...

    async def get_job(self, board: str, external_id: str) -> NormalizedJob | None: ...

    def normalize_job(self, raw: dict[str, Any], board: str) -> NormalizedJob: ...

    @staticmethod
    def valid_token(token: str) -> bool: ...

    async def company_name(self, board: str) -> str:
        """The company's display name; raises BoardNotFoundError for unknown boards."""
        ...


async def get_json(
    client: httpx.AsyncClient, url: str, params: dict[str, str] | None = None
) -> Any:
    try:
        response = await client.get(url, params=params, headers={"User-Agent": USER_AGENT})
    except httpx.TimeoutException as exc:
        raise ProviderError("The job board took too long to respond.", detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise ProviderError("The job board couldn't be reached.", detail=str(exc)) from exc
    if response.status_code == 404:
        raise BoardNotFoundError("That job board doesn't exist.", detail=url)
    if response.status_code >= 400:
        raise ProviderError(
            "The job board returned an error.", detail=f"{response.status_code} {url}"
        )
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise ProviderError("The job board's response was too large.", detail=url)
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError("The job board returned an unreadable response.", detail=url) from exc
