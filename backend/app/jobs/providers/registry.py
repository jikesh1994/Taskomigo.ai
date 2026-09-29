from __future__ import annotations

import httpx

from app.core.config import Settings
from app.jobs.providers.base import JobSearchProvider
from app.jobs.providers.greenhouse import GreenhouseProvider
from app.jobs.providers.lever import LeverProvider


def build_providers(client: httpx.AsyncClient, settings: Settings) -> dict[str, JobSearchProvider]:
    return {
        "greenhouse": GreenhouseProvider(client, settings.greenhouse_api_base),
        "lever": LeverProvider(client, settings.lever_api_base),
    }


def supported_platforms() -> list[str]:
    return ["greenhouse", "lever"]


def get_provider(providers: dict[str, JobSearchProvider], platform: str) -> JobSearchProvider:
    return providers[platform]


def parse_source(providers: dict[str, JobSearchProvider], source: str) -> tuple[str, str] | None:
    """(platform, board token) for a careers URL or "platform:token", else None."""
    for platform, provider in providers.items():
        token = provider.supports(source)
        if token:
            return platform, token
    return None


def new_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.job_fetch_timeout_seconds, connect=10),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )
