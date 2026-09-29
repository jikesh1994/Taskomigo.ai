from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, str_enum
from app.models.enums import (
    AnalysisStatus,
    EmploymentType,
    JobMatchStatus,
    SearchRunStatus,
    WorkplaceType,
)


class JobSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A company job board a user searches (e.g. Greenhouse board "stripe")."""

    __tablename__ = "job_sources"
    __table_args__ = (UniqueConstraint("user_id", "platform", "board"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(32))
    board: Mapped[str] = mapped_column(String(80))
    company_name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column()
    last_job_count: Mapped[int | None] = mapped_column()
    last_error: Mapped[str | None] = mapped_column(String(300))


class Job(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A public job posting, shared by every user whose sources include its board."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("platform", "external_id"),
        Index("ix_jobs_board", "platform", "board"),
    )

    platform: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(128))
    board: Mapped[str] = mapped_column(String(80))
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(300))
    workplace: Mapped[WorkplaceType] = mapped_column(
        str_enum(WorkplaceType, 16), default=WorkplaceType.UNKNOWN
    )
    employment_type: Mapped[EmploymentType | None] = mapped_column(str_enum(EmploymentType, 16))
    department: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    application_url: Mapped[str] = mapped_column(String(1000))
    salary_min: Mapped[int | None] = mapped_column()
    salary_max: Mapped[int | None] = mapped_column()
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    posted_at: Mapped[datetime | None] = mapped_column()
    source_updated_at: Mapped[datetime | None] = mapped_column()
    first_seen_at: Mapped[datetime] = mapped_column()
    last_seen_at: Mapped[datetime] = mapped_column()
    # False once the posting disappears from its board (filled or withdrawn).
    is_active: Mapped[bool] = mapped_column(default=True)
    closed_at: Mapped[datetime | None] = mapped_column()
    # Same company + title + location across platforms → treated as one job.
    dedupe_key: Mapped[str] = mapped_column(String(400), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    # Deterministic JD facts (app/jobs/extract.py JobFacts), recomputed when content changes.
    facts: Mapped[dict[str, Any]] = mapped_column(default=dict)
    raw: Mapped[dict[str, Any]] = mapped_column(default=dict)

    # Optional AI analysis (app/ai/jobs), shared by all users.
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        str_enum(AnalysisStatus, 16), default=AnalysisStatus.NONE
    )
    analysis: Mapped[dict[str, Any] | None] = mapped_column()
    analysis_error: Mapped[str | None] = mapped_column(String(300))
    analysis_prompt_version: Mapped[str | None] = mapped_column(String(64))
    analyzed_at: Mapped[datetime | None] = mapped_column()
    expires_at: Mapped[datetime | None] = mapped_column()


class JobMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """How well one job fits one user. Scores explain fit; they don't predict hiring."""

    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id"),
        Index("ix_job_matches_user_overall", "user_id", "overall_match"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    skills_match: Mapped[int] = mapped_column()
    experience_match: Mapped[int] = mapped_column()
    location_match: Mapped[int] = mapped_column()
    salary_match: Mapped[int] = mapped_column()
    preference_match: Mapped[int] = mapped_column()
    other_match: Mapped[int] = mapped_column()
    overall_match: Mapped[int] = mapped_column()
    reasons: Mapped[list[str]] = mapped_column(default=list)
    missing_requirements: Mapped[list[str]] = mapped_column(default=list)
    concerns: Mapped[list[str]] = mapped_column(default=list)
    notes: Mapped[list[str]] = mapped_column(default=list)
    # Set when a hard filter hides the job (excluded company, remote-only, ...).
    excluded_reason: Mapped[str | None] = mapped_column(String(300))
    recommended_resume_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL")
    )
    resume_reason: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[JobMatchStatus] = mapped_column(
        str_enum(JobMatchStatus, 16), default=JobMatchStatus.NEW
    )
    computed_at: Mapped[datetime] = mapped_column()


class SearchRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "search_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[SearchRunStatus] = mapped_column(
        str_enum(SearchRunStatus, 16), default=SearchRunStatus.QUEUED
    )
    started_at: Mapped[datetime | None] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column()
    sources_total: Mapped[int] = mapped_column(default=0)
    sources_done: Mapped[int] = mapped_column(default=0)
    jobs_fetched: Mapped[int] = mapped_column(default=0)
    jobs_new: Mapped[int] = mapped_column(default=0)
    jobs_closed: Mapped[int] = mapped_column(default=0)
    matches: Mapped[int] = mapped_column(default=0)
    # [{"source": "Stripe", "message": "..."}], user-safe messages only.
    source_errors: Mapped[list[dict[str, str]]] = mapped_column(default=list)
    error: Mapped[str | None] = mapped_column(Text)
