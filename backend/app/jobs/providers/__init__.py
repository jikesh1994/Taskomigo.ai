"""Platform adapters. Adding a platform = one module implementing JobSearchProvider."""

from app.jobs.providers.base import BoardNotFoundError, JobSearchProvider, ProviderError
from app.jobs.providers.registry import get_provider, parse_source, supported_platforms

__all__ = [
    "BoardNotFoundError",
    "JobSearchProvider",
    "ProviderError",
    "get_provider",
    "parse_source",
    "supported_platforms",
]
