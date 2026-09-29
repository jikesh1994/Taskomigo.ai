"""AI analysis of one job posting. Runs in the worker; cached on the job for all users."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.jobs.analyzer import PROMPT, JobAnalyzer
from app.ai.llm.base import LLMError, LLMProvider
from app.core.logging import get_logger
from app.core.security import ensure_aware, utc_now
from app.models.enums import AnalysisStatus
from app.models.job import Job
from app.repositories.job_repository import JobRepository

logger = get_logger(__name__)

# A pending/processing analysis older than this is assumed lost and may be requested again.
STALE_ANALYSIS_AFTER = timedelta(minutes=10)


def analysis_is_current(job: Job) -> bool:
    return job.analysis_status is AnalysisStatus.DONE and job.analysis_prompt_version == PROMPT.id


def analysis_in_flight(job: Job) -> bool:
    if job.analysis_status not in (AnalysisStatus.PENDING, AnalysisStatus.PROCESSING):
        return False
    return ensure_aware(job.updated_at) > utc_now() - STALE_ANALYSIS_AFTER


async def analyze_job(
    session: AsyncSession, provider: LLMProvider, job_id: uuid.UUID
) -> Job | None:
    """Idempotent: a job already analysed with the current prompt is left alone."""
    job = await JobRepository(session).get_job(job_id)
    if job is None:
        return None
    if analysis_is_current(job):
        return job
    job.analysis_status = AnalysisStatus.PROCESSING
    await session.commit()
    log = logger.bind(job_id=str(job.id))
    try:
        outcome = await JobAnalyzer(provider).analyze(
            title=job.title, company=job.company, location=job.location, description=job.description
        )
    except LLMError as exc:
        job.analysis_status = AnalysisStatus.FAILED
        job.analysis_error = exc.message[:300]
        log.warning("job_analysis_failed", code=exc.code, detail=exc.detail)
    except Exception:
        job.analysis_status = AnalysisStatus.FAILED
        job.analysis_error = "Something went wrong while analysing this job. Please try again."
        log.exception("job_analysis_crashed")
    else:
        job.analysis = outcome.analysis.model_dump(mode="json") | {"analyzer": outcome.analyzer}
        job.analysis_prompt_version = outcome.prompt_id
        job.analysis_status = AnalysisStatus.DONE
        job.analysis_error = None
        job.analyzed_at = utc_now()
        log.info(
            "job_analyzed",
            requirements=len(outcome.analysis.requirements),
            downgraded=outcome.analysis.downgraded,
        )
    await session.commit()
    return job
