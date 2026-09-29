"""The user's view of jobs: lists, detail, status changes, analysis requests and stats."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import utc_now
from app.jobs.extract import JobFacts
from app.jobs.matching import normalize_weights
from app.models.enums import AnalysisStatus, JobMatchStatus
from app.models.job import Job, JobMatch
from app.repositories.job_repository import JobRepository, MatchTab
from app.repositories.preferences_repository import PreferencesRepository
from app.repositories.resume_repository import ResumeRepository
from app.schemas.job import (
    JobDetail,
    JobFactsRead,
    JobList,
    JobStats,
    JobSummary,
    JobTabCounts,
    MatchScores,
    RecommendedResume,
    SearchRunRead,
    analysis_or_none,
)
from app.services.job_analysis_service import analysis_in_flight, analysis_is_current

NOT_FOUND = "Job not found."


def _summary(match: JobMatch, job: Job, min_score: int) -> JobSummary:
    return JobSummary(
        id=job.id,
        platform=job.platform,
        company=job.company,
        title=job.title,
        location=job.location,
        workplace=job.workplace,
        employment_type=job.employment_type,
        department=job.department,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        posted_at=job.posted_at,
        first_seen_at=job.first_seen_at,
        is_active=job.is_active,
        application_url=job.application_url,
        overall_match=match.overall_match,
        scores=MatchScores(
            skills=match.skills_match,
            experience=match.experience_match,
            location=match.location_match,
            salary=match.salary_match,
            preferences=match.preference_match,
            other=match.other_match,
        ),
        reasons=match.reasons,
        missing_requirements=match.missing_requirements,
        concerns=match.concerns,
        excluded_reason=match.excluded_reason,
        below_min_score=match.overall_match < min_score,
        status=match.status,
    )


class JobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = JobRepository(session)

    async def _preferences(self, user_id: uuid.UUID) -> tuple[int, dict[str, int]]:
        preferences = await PreferencesRepository(self.session).get_for_user(user_id)
        if preferences is None:
            return 60, normalize_weights(None)
        return preferences.min_match_score, normalize_weights(preferences.match_weights)

    async def list_jobs(
        self,
        user_id: uuid.UUID,
        *,
        tab: MatchTab,
        query: str | None,
        workplace: str | None,
        sort: Literal["score", "newest"],
        limit: int,
        offset: int,
    ) -> JobList:
        min_score, _ = await self._preferences(user_id)
        rows, total = await self.repo.list_matches(
            user_id,
            tab=tab,
            min_score=min_score,
            query=query,
            workplace=workplace,
            sort=sort,
            limit=limit,
            offset=offset,
        )
        counts = await self.repo.tab_counts(user_id, min_score)
        return JobList(
            items=[_summary(m, j, min_score) for m, j in rows],
            total=total,
            counts=JobTabCounts(**counts),
            min_match_score=min_score,
        )

    async def _get(self, user_id: uuid.UUID, job_id: uuid.UUID) -> tuple[JobMatch, Job]:
        # Only jobs the user has a match for are visible to them.
        found = await self.repo.get_match(user_id, job_id)
        if found is None:
            raise NotFoundError(NOT_FOUND)
        return found

    async def detail(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobDetail:
        match, job = await self._get(user_id, job_id)
        min_score, weights = await self._preferences(user_id)
        recommended = None
        if match.recommended_resume_id:
            resume = await ResumeRepository(self.session).get_for_user(
                user_id, match.recommended_resume_id
            )
            if resume is not None:
                recommended = RecommendedResume(
                    id=resume.id, name=resume.name, reason=match.resume_reason
                )
        facts = JobFacts.from_dict(job.facts) if job.facts else JobFacts()
        return JobDetail(
            **_summary(match, job, min_score).model_dump(),
            description=job.description,
            notes=match.notes,
            facts=JobFactsRead(**facts.to_dict()),  # type: ignore[arg-type]
            weights=weights,
            min_match_score=min_score,
            recommended_resume=recommended,
            computed_at=match.computed_at,
            closed_at=job.closed_at,
            # An analysis made with an older prompt counts as not analysed.
            analysis_status=(
                job.analysis_status
                if job.analysis_status is not AnalysisStatus.DONE or analysis_is_current(job)
                else AnalysisStatus.NONE
            ),
            analysis=analysis_or_none(job.analysis) if analysis_is_current(job) else None,
            analysis_error=job.analysis_error,
            analyzed_at=job.analyzed_at,
        )

    async def set_status(
        self, user_id: uuid.UUID, job_id: uuid.UUID, status: JobMatchStatus
    ) -> JobDetail:
        match, _ = await self._get(user_id, job_id)
        match.status = status
        await self.session.commit()
        return await self.detail(user_id, job_id)

    async def request_analysis(self, user_id: uuid.UUID, job_id: uuid.UUID) -> tuple[Job, bool]:
        """Mark the job for analysis; returns (job, whether a task must be dispatched)."""
        _, job = await self._get(user_id, job_id)
        if analysis_is_current(job) or analysis_in_flight(job):
            return job, False
        job.analysis_status = AnalysisStatus.PENDING
        job.analysis_error = None
        await self.session.commit()
        return job, True

    async def mark_analysis_dispatch_failed(self, job: Job) -> None:
        job.analysis_status = AnalysisStatus.FAILED
        job.analysis_error = "The analysis couldn't be started. Please try again."
        await self.session.commit()

    async def stats(self, user_id: uuid.UUID) -> JobStats:
        min_score, _ = await self._preferences(user_id)
        counts = await self.repo.tab_counts(user_id, min_score)
        last = await self.repo.latest_run(user_id)
        return JobStats(
            sources=await self.repo.count_sources(user_id),
            matches=counts["matches"],
            saved=counts["saved"],
            new_this_week=await self.repo.new_matches_since(
                user_id, utc_now() - timedelta(days=7), min_score
            ),
            last_search=SearchRunRead.model_validate(last) if last else None,
        )
