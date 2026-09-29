from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.ai.jobs.analyzer import JobAnalysis
from app.models.enums import (
    AnalysisStatus,
    EmploymentType,
    JobMatchStatus,
    SearchRunStatus,
    WorkplaceType,
)
from app.schemas.common import ORMModel, UtcDatetime

# ------------------------------------------------------------------ sources


class JobSourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(
        min_length=2,
        max_length=300,
        description="A careers URL (https://boards.greenhouse.io/stripe, "
        "https://jobs.lever.co/spotify) or `platform:board` (greenhouse:stripe).",
        examples=["https://boards.greenhouse.io/stripe"],
    )


class JobSourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool


class JobSourceRead(ORMModel):
    id: uuid.UUID
    platform: str
    board: str
    company_name: str
    enabled: bool
    last_synced_at: UtcDatetime | None
    last_job_count: int | None
    last_error: str | None


class CatalogEntryRead(BaseModel):
    platform: str
    board: str
    company: str
    added: bool


# ------------------------------------------------------------------ search runs


class SourceErrorRead(BaseModel):
    source: str
    message: str


class SearchRunRead(ORMModel):
    id: uuid.UUID
    status: SearchRunStatus
    started_at: UtcDatetime | None
    finished_at: UtcDatetime | None
    sources_total: int
    sources_done: int
    jobs_fetched: int
    jobs_new: int
    jobs_closed: int
    matches: int
    source_errors: list[SourceErrorRead]
    error: str | None
    created_at: UtcDatetime


# ------------------------------------------------------------------ jobs & matches


class MatchScores(BaseModel):
    skills: int
    experience: int
    location: int
    salary: int
    preferences: int
    other: int


class JobSummary(BaseModel):
    """A job card: the posting's headline facts plus how it fits the user."""

    id: uuid.UUID
    platform: str
    company: str
    title: str
    location: str | None
    workplace: WorkplaceType
    employment_type: EmploymentType | None
    department: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    posted_at: UtcDatetime | None
    first_seen_at: UtcDatetime
    is_active: bool
    application_url: str
    overall_match: int
    scores: MatchScores
    reasons: list[str]
    missing_requirements: list[str]
    concerns: list[str]
    excluded_reason: str | None
    below_min_score: bool
    status: JobMatchStatus


class RecommendedResume(BaseModel):
    id: uuid.UUID
    name: str
    reason: str | None


class JobFactsRead(BaseModel):
    """Deterministic facts read from the posting. `None` means the posting doesn't say."""

    required_skills: list[str]
    preferred_skills: list[str]
    skill_evidence: dict[str, str]
    min_years: float | None
    years_evidence: str | None
    workplace: WorkplaceType
    workplace_evidence: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    salary_evidence: str | None
    sponsorship: bool | None
    sponsorship_evidence: str | None
    employment_type: EmploymentType | None


class JobDetail(JobSummary):
    description: str
    notes: list[str]
    facts: JobFactsRead
    weights: dict[str, int]
    min_match_score: int
    recommended_resume: RecommendedResume | None
    computed_at: UtcDatetime
    closed_at: UtcDatetime | None
    analysis_status: AnalysisStatus
    analysis: JobAnalysis | None
    analysis_error: str | None
    analyzed_at: UtcDatetime | None


class JobTabCounts(BaseModel):
    matches: int
    saved: int
    skipped: int
    hidden: int


class JobList(BaseModel):
    items: list[JobSummary]
    total: int
    counts: JobTabCounts
    min_match_score: int


class JobStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: JobMatchStatus


class RematchResult(BaseModel):
    matched: int


class JobStats(BaseModel):
    sources: int
    matches: int
    saved: int
    new_this_week: int
    last_search: SearchRunRead | None


def analysis_or_none(value: dict[str, Any] | None) -> JobAnalysis | None:
    if not value:
        return None
    return JobAnalysis.model_validate({k: v for k, v in value.items() if k != "analyzer"})


JobTab = Literal["matches", "saved", "skipped", "hidden"]
