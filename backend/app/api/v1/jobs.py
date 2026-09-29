from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response, status

from app.api.deps import (
    CurrentUser,
    JobDispatcherDep,
    JobMatchServiceDep,
    JobSearchServiceDep,
    JobServiceDep,
    JobSourceServiceDep,
    RequestContextDep,
    SessionDep,
)
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.enums import WorkplaceType
from app.repositories.job_repository import JobRepository
from app.schemas.common import (
    AUTH_RESPONSES,
    NOT_FOUND_RESPONSES,
    VALIDATION_RESPONSES,
    ErrorResponse,
)
from app.schemas.job import (
    CatalogEntryRead,
    JobDetail,
    JobList,
    JobSourceCreate,
    JobSourceRead,
    JobSourceUpdate,
    JobStats,
    JobStatusUpdate,
    JobTab,
    RematchResult,
    SearchRunRead,
)

logger = get_logger(__name__)

sources_router = APIRouter(prefix="/job-sources", tags=["jobs"], responses=AUTH_RESPONSES)
router = APIRouter(prefix="/jobs", tags=["jobs"], responses=AUTH_RESPONSES)


# ------------------------------------------------------------------ sources


@sources_router.get("", response_model=list[JobSourceRead], summary="Your company job boards")
async def list_sources(user: CurrentUser, service: JobSourceServiceDep) -> list[JobSourceRead]:
    return [JobSourceRead.model_validate(s) for s in await service.list_for_user(user.id)]


@sources_router.get(
    "/catalog",
    response_model=list[CatalogEntryRead],
    summary="Suggested companies with public job boards",
)
async def source_catalog(user: CurrentUser, service: JobSourceServiceDep) -> list[CatalogEntryRead]:
    return [
        CatalogEntryRead(
            platform=item.entry.platform,
            board=item.entry.board,
            company=item.entry.company,
            added=item.added,
        )
        for item in await service.catalog(user.id)
    ]


@sources_router.post(
    "",
    response_model=JobSourceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a company job board",
    description="Greenhouse and Lever public job boards are supported. The board is "
    "checked live before it's saved.",
    responses={
        409: {"model": ErrorResponse, "description": "Already added, or the limit reached"},
        503: {"model": ErrorResponse, "description": "The job platform couldn't be reached"},
        **VALIDATION_RESPONSES,
    },
)
async def add_source(
    data: JobSourceCreate, user: CurrentUser, service: JobSourceServiceDep, ctx: RequestContextDep
) -> JobSourceRead:
    return JobSourceRead.model_validate(await service.add(user.id, data.source, ctx))


@sources_router.patch(
    "/{source_id}",
    response_model=JobSourceRead,
    summary="Turn a job board on or off for searches",
    responses={**NOT_FOUND_RESPONSES, **VALIDATION_RESPONSES},
)
async def update_source(
    source_id: uuid.UUID, data: JobSourceUpdate, user: CurrentUser, service: JobSourceServiceDep
) -> JobSourceRead:
    return JobSourceRead.model_validate(await service.set_enabled(user.id, source_id, data.enabled))


@sources_router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove a job board",
    description="Its jobs leave your lists, except ones you saved.",
    responses=NOT_FOUND_RESPONSES,
)
async def delete_source(
    source_id: uuid.UUID, user: CurrentUser, service: JobSourceServiceDep, ctx: RequestContextDep
) -> Response:
    await service.delete(user.id, source_id, ctx)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ search


@router.post(
    "/search",
    response_model=SearchRunRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Search your job boards for new jobs",
    description="Runs in the background: poll `GET /jobs/search/{run_id}` until `status` "
    "is `succeeded` or `failed`.",
    responses={
        409: {"model": ErrorResponse, "description": "A search is already running"},
        **VALIDATION_RESPONSES,
    },
)
async def start_search(
    user: CurrentUser,
    service: JobSearchServiceDep,
    dispatcher: JobDispatcherDep,
    session: SessionDep,
) -> SearchRunRead:
    run = await service.start(user.id)
    try:
        await dispatcher.search(run.id)
    except Exception:
        logger.exception("job_search_dispatch_failed", run_id=str(run.id))
        run = await service.mark_dispatch_failed(run)
    fresh = await JobRepository(session).get_run(user.id, run.id)
    return SearchRunRead.model_validate(fresh or run)


@router.get(
    "/search/latest",
    response_model=SearchRunRead | None,
    summary="Your most recent search",
)
async def latest_search(user: CurrentUser, session: SessionDep) -> SearchRunRead | None:
    run = await JobRepository(session).latest_run(user.id)
    return SearchRunRead.model_validate(run) if run else None


@router.get(
    "/search/{run_id}",
    response_model=SearchRunRead,
    summary="Progress of a search",
    responses=NOT_FOUND_RESPONSES,
)
async def get_search(run_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> SearchRunRead:
    run = await JobRepository(session).get_run(user.id, run_id)
    if run is None:
        raise NotFoundError("Search not found.")
    return SearchRunRead.model_validate(run)


@router.post(
    "/rematch",
    response_model=RematchResult,
    summary="Re-score open jobs",
    description="Use after editing your profile, skills or preferences. No new fetching.",
)
async def rematch(user: CurrentUser, service: JobMatchServiceDep) -> RematchResult:
    return RematchResult(matched=await service.rematch(user.id))


@router.get("/stats", response_model=JobStats, summary="Job counts for the dashboard")
async def job_stats(user: CurrentUser, service: JobServiceDep) -> JobStats:
    return await service.stats(user.id)


# ------------------------------------------------------------------ jobs


@router.get(
    "",
    response_model=JobList,
    summary="Your matched jobs",
    description="`matches`: open jobs that pass your filters and minimum score. "
    "`hidden`: open jobs a filter removed or that scored below your minimum (with the "
    "reason). Match scores describe fit with your own profile and preferences; they "
    "are not a prediction of interviews or offers.",
)
async def list_jobs(
    user: CurrentUser,
    service: JobServiceDep,
    tab: JobTab = "matches",
    q: Annotated[str | None, Query(max_length=100)] = None,
    workplace: WorkplaceType | None = None,
    sort: Literal["score", "newest"] = "score",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> JobList:
    return await service.list_jobs(
        user.id,
        tab=tab,
        query=q or None,
        workplace=workplace.value if workplace else None,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{job_id}",
    response_model=JobDetail,
    summary="A job, its match breakdown and analysis",
    responses=NOT_FOUND_RESPONSES,
)
async def get_job(job_id: uuid.UUID, user: CurrentUser, service: JobServiceDep) -> JobDetail:
    return await service.detail(user.id, job_id)


@router.patch(
    "/{job_id}",
    response_model=JobDetail,
    summary="Save, skip or restore a job",
    responses={**NOT_FOUND_RESPONSES, **VALIDATION_RESPONSES},
)
async def update_job(
    job_id: uuid.UUID, data: JobStatusUpdate, user: CurrentUser, service: JobServiceDep
) -> JobDetail:
    return await service.set_status(user.id, job_id, data.status)


@router.post(
    "/{job_id}/analyze",
    response_model=JobDetail,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Analyse the job description with AI",
    description="Runs in the background and is cached per job. Each requirement is "
    "marked `explicit` (quoted from the posting) or `inferred`.",
    responses=NOT_FOUND_RESPONSES,
)
async def analyze_job(
    job_id: uuid.UUID, user: CurrentUser, service: JobServiceDep, dispatcher: JobDispatcherDep
) -> JobDetail:
    job, dispatch = await service.request_analysis(user.id, job_id)
    if dispatch:
        try:
            await dispatcher.analyze(job.id)
        except Exception:
            logger.exception("job_analysis_dispatch_failed", job_id=str(job.id))
            await service.mark_analysis_dispatch_failed(job)
    return await service.detail(user.id, job_id)
