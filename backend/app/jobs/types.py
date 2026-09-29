from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.models.enums import EmploymentType, WorkplaceType

__all__ = ["NormalizedJob", "SearchQuery", "WorkplaceType"]


@dataclass(slots=True)
class NormalizedJob:
    """The common shape every platform adapter returns."""

    platform: str
    external_id: str
    board: str  # the source's board token (e.g. "stripe")
    company: str
    title: str
    location: str | None
    workplace: WorkplaceType
    employment_type: EmploymentType | None
    description: str  # plain text
    application_url: str
    posted_at: datetime | None
    updated_at: datetime | None
    department: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)  # trimmed original payload


@dataclass(frozen=True, slots=True)
class SearchQuery:
    """Optional narrowing applied at fetch time (matching does the real ranking)."""

    keywords: tuple[str, ...] = ()

    def matches(self, job: NormalizedJob) -> bool:
        if not self.keywords:
            return True
        haystack = f"{job.title}\n{job.description}".casefold()
        return any(k.casefold() in haystack for k in self.keywords)
