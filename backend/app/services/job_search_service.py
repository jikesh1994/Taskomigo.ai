"""Job search: start runs (API) and execute them (worker).

A run fetches every enabled source concurrently, normalizes the postings into `jobs`
(one row per platform posting, shared by all users), marks postings that disappeared
from their board as closed, and scores the open jobs for the user.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, DomainValidationError
from app.core.logging import get_logger
from app.core.security import utc_now
from app.jobs.extract import EXTRACTOR_VERSION, extract_facts
from app.jobs.matching import norm
from app.jobs.providers import JobSearchProvider, ProviderError
from app.jobs.types import NormalizedJob
from app.models.enums import AnalysisStatus, SearchRunStatus
from app.models.job import Job, JobSource, SearchRun
from app.repositories.job_repository import JobRepository
from app.services.job_match_service import JobMatchService

logger = get_logger(__name__)

# A queued/running run older than this is treated as dead (worker crashed) and ignored.
STALE_RUN_AFTER = timedelta(minutes=15)
# Descriptions are stored as plain text; bound them so one odd posting can't bloat rows.
MAX_DESCRIPTION_CHARS = 60_000


def dedupe_key(company: str, title: str, location: str | None) -> str:
    return f"{norm(company)}|{norm(title)}|{norm(location)}"[:400]


def content_hash(job: NormalizedJob) -> str:
    parts = (
        job.title,
        job.location or "",
        job.description,
        job.workplace.value,
        job.employment_type.value if job.employment_type else "",
        f"{job.salary_min}-{job.salary_max}-{job.salary_currency}",
    )
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


class JobSearchService:
    """API side: start a run and report on it."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = JobRepository(session)

    async def start(self, user_id: uuid.UUID) -> SearchRun:
        sources = await self.repo.list_sources(user_id, enabled_only=True)
        if not sources:
            raise DomainValidationError(
                "Add at least one company job board before searching.", code="no_sources"
            )
        if await self.repo.active_run(user_id, utc_now() - STALE_RUN_AFTER):
            raise ConflictError("A search is already running.", code="search_in_progress")
        run = SearchRun(
            id=uuid.uuid4(),
            user_id=user_id,
            status=SearchRunStatus.QUEUED,
            sources_total=len(sources),
            source_errors=[],
        )
        self.repo.add(run)
        await self.session.commit()
        return run

    async def mark_dispatch_failed(self, run: SearchRun) -> SearchRun:
        run.status = SearchRunStatus.FAILED
        run.error = "The search couldn't be started. Please try again."
        run.finished_at = utc_now()
        await self.session.commit()
        return run


@dataclass
class _Fetched:
    source: JobSource
    jobs: list[NormalizedJob] | None
    error: ProviderError | None = None


async def run_search(
    session: AsyncSession,
    providers: dict[str, JobSearchProvider],
    run_id: uuid.UUID,
    *,
    concurrency: int = 4,
) -> SearchRun | None:
    """Execute a queued run. Safe to redeliver: a finished run is left alone."""
    repo = JobRepository(session)
    run = await repo.get_run_by_id(run_id)
    if run is None or run.status in (SearchRunStatus.SUCCEEDED, SearchRunStatus.FAILED):
        return run
    log = logger.bind(run_id=str(run.id), user_id=str(run.user_id))
    run.status = SearchRunStatus.RUNNING
    run.started_at = utc_now()
    await session.commit()

    try:
        sources = await repo.list_sources(run.user_id, enabled_only=True)
        run.sources_total = len(sources)
        await session.commit()

        semaphore = asyncio.Semaphore(concurrency)

        async def fetch(source: JobSource) -> _Fetched:
            provider = providers.get(source.platform)
            if provider is None:
                return _Fetched(source, None, ProviderError("This job board type isn't supported."))
            async with semaphore:
                try:
                    return _Fetched(source, await provider.search(source.board))
                except ProviderError as exc:
                    return _Fetched(source, None, exc)

        # Network in parallel; database writes one source at a time as results arrive.
        errors: list[dict[str, str]] = []
        for next_done in asyncio.as_completed([fetch(s) for s in sources]):
            fetched = await next_done
            source = fetched.source
            source.last_synced_at = utc_now()
            if fetched.jobs is None:
                message = fetched.error.message if fetched.error else "Unknown error."
                source.last_error = message[:300]
                errors.append({"source": source.company_name, "message": message})
                log.warning(
                    "job_source_fetch_failed",
                    platform=source.platform,
                    board=source.board,
                    detail=fetched.error.detail if fetched.error else None,
                )
            else:
                new, closed = await _store(repo, source, fetched.jobs)
                source.last_error = None
                source.last_job_count = len(fetched.jobs)
                run.jobs_fetched += len(fetched.jobs)
                run.jobs_new += new
                run.jobs_closed += closed
            run.sources_done += 1
            run.source_errors = list(errors)
            await session.commit()

        if sources and len(errors) == len(sources):
            run.status = SearchRunStatus.FAILED
            run.error = "None of your job boards could be reached. Please try again later."
        else:
            run.matches = await JobMatchService(session).match_jobs(
                run.user_id,
                await repo.active_jobs_for_boards([(s.platform, s.board) for s in sources]),
            )
            run.status = SearchRunStatus.SUCCEEDED
    except Exception:
        await session.rollback()
        log.exception("job_search_crashed")
        run = await repo.get_run_by_id(run_id)
        if run is None:
            return None
        run.status = SearchRunStatus.FAILED
        run.error = "Something went wrong while searching. Please try again."
    run.finished_at = utc_now()
    await session.commit()
    log.info(
        "job_search_finished",
        status=run.status.value,
        fetched=run.jobs_fetched,
        new=run.jobs_new,
        closed=run.jobs_closed,
        matches=run.matches,
        failed_sources=len(run.source_errors),
    )
    return run


async def _store(
    repo: JobRepository, source: JobSource, fetched: list[NormalizedJob]
) -> tuple[int, int]:
    """Upsert one board's postings; returns (new jobs, closed jobs)."""
    now = utc_now()
    by_id = {job.external_id: job for job in fetched if job.title and job.application_url}
    existing = await repo.jobs_by_external_id(source.platform, list(by_id))
    new = 0
    for external_id, item in by_id.items():
        job = existing.get(external_id)
        digest = content_hash(item)
        if job is None:
            job = Job(
                id=uuid.uuid4(),
                platform=item.platform,
                external_id=external_id,
                first_seen_at=now,
                content_hash="",
            )
            repo.add(job)
            new += 1
        if job.content_hash != digest:
            _apply(job, item, digest)
        elif job.facts.get("extractor_version") != EXTRACTOR_VERSION:
            # Same posting, better extraction rules: refresh the facts only.
            job.facts = _facts(job.title, job.description, item)
        job.last_seen_at = now
        job.is_active = True
        job.closed_at = None

    closed = 0
    for job in await repo.active_jobs_for_board(source.platform, source.board):
        if job.external_id not in by_id:
            job.is_active = False
            job.closed_at = now
            closed += 1
    return new, closed


def _apply(job: Job, item: NormalizedJob, digest: str) -> None:
    description = item.description[:MAX_DESCRIPTION_CHARS]
    job.board = item.board
    job.company = item.company[:200]
    job.title = item.title[:300]
    job.location = item.location[:300] if item.location else None
    job.workplace = item.workplace
    job.employment_type = item.employment_type
    job.department = item.department[:200] if item.department else None
    job.description = description
    job.application_url = item.application_url[:1000]
    job.salary_min = item.salary_min
    job.salary_max = item.salary_max
    job.salary_currency = item.salary_currency
    job.posted_at = item.posted_at
    job.source_updated_at = item.updated_at
    job.raw = item.raw
    job.dedupe_key = dedupe_key(item.company, item.title, item.location)
    job.content_hash = digest
    job.facts = _facts(item.title, description, item)
    # The posting changed, so an earlier AI analysis may no longer be accurate.
    if job.analysis is not None:
        job.analysis_status = AnalysisStatus.NONE
        job.analysis = None
        job.analyzed_at = None


def _facts(title: str, description: str, item: NormalizedJob) -> dict[str, object]:
    facts = extract_facts(
        title=title,
        description=description,
        location=item.location,
        workplace=item.workplace,
        employment_type=item.employment_type,
        salary=(item.salary_min, item.salary_max, item.salary_currency),
    ).to_dict()
    return {**facts, "extractor_version": EXTRACTOR_VERSION}
