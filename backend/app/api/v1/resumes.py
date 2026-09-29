from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Response, UploadFile, status

from app.ai.resume.schema import ParsedResume
from app.api.deps import (
    CurrentUser,
    ParseDispatcherDep,
    RequestContextDep,
    ResumeReviewServiceDep,
    ResumeServiceDep,
    SettingsDep,
)
from app.core.logging import get_logger
from app.models.resume import Resume
from app.schemas.common import (
    AUTH_RESPONSES,
    NOT_FOUND_RESPONSES,
    VALIDATION_RESPONSES,
    ErrorResponse,
)
from app.schemas.resume import (
    ResumeDetail,
    ResumeRead,
    ResumeReview,
    ResumeUpdate,
    ReviewApplyRequest,
    ReviewApplyResult,
)
from app.services.resume_service import ResumeFile, ResumeService

logger = get_logger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"], responses=AUTH_RESPONSES)

_UPLOAD_ERRORS = {
    409: {
        "model": ErrorResponse,
        "description": "Duplicate file, or the per-user resume limit reached",
    },
    413: {"model": ErrorResponse, "description": "File larger than the upload limit"},
    415: {
        "model": ErrorResponse,
        "description": "Not a PDF or DOCX (checked by content, not name)",
    },
    **VALIDATION_RESPONSES,
}


def _read(resume: Resume, pending: int = 0) -> ResumeRead:
    return ResumeRead.model_validate(resume).model_copy(update={"pending_review": pending})


async def _dispatch(
    resume: Resume, dispatcher: ParseDispatcherDep, service: ResumeService
) -> Resume:
    try:
        await dispatcher.dispatch(resume.id)
    except Exception:
        logger.exception("resume_dispatch_failed", resume_id=str(resume.id))
        return await service.mark_dispatch_failed(resume)
    return await service.reload(resume)


@router.post(
    "",
    response_model=ResumeRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a resume",
    description="Accepts PDF or DOCX. The file is stored encrypted and parsed in the "
    "background: poll `GET /resumes/{id}` until `parse_status` is `parsed` or `failed`.",
    responses=_UPLOAD_ERRORS,
)
async def upload_resume(
    user: CurrentUser,
    service: ResumeServiceDep,
    dispatcher: ParseDispatcherDep,
    settings: SettingsDep,
    ctx: RequestContextDep,
    file: Annotated[UploadFile, File(description="PDF or DOCX")],
    name: Annotated[str | None, Form(max_length=120)] = None,
) -> ResumeRead:
    # Read one byte past the limit so oversized files are detected without reading all of it.
    data = await file.read(settings.resume_max_bytes + 1)
    resume = await service.upload(
        user.id,
        ResumeFile(filename=file.filename or "", content_type=file.content_type or "", data=data),
        name,
        ctx,
    )
    return _read(await _dispatch(resume, dispatcher, service))


@router.get("", response_model=list[ResumeRead], summary="List your resumes")
async def list_resumes(
    user: CurrentUser, service: ResumeServiceDep, review: ResumeReviewServiceDep
) -> list[ResumeRead]:
    resumes = await service.list_for_user(user.id)
    pending = await review.pending_counts(user, resumes)
    return [_read(r, pending.get(r.id, 0)) for r in resumes]


@router.get(
    "/{resume_id}",
    response_model=ResumeDetail,
    summary="Get a resume and its parsed data",
    responses=NOT_FOUND_RESPONSES,
)
async def get_resume(
    resume_id: uuid.UUID,
    user: CurrentUser,
    service: ResumeServiceDep,
    review: ResumeReviewServiceDep,
) -> ResumeDetail:
    resume = await service.get(user.id, resume_id)
    pending = (await review.pending_counts(user, [resume])).get(resume.id, 0)
    parsed = ParsedResume.model_validate(resume.parsed_data) if resume.parsed_data else None
    return ResumeDetail(**_read(resume, pending).model_dump(), parsed=parsed)


@router.patch(
    "/{resume_id}",
    response_model=ResumeRead,
    summary="Rename a resume or make it the default",
    responses={**NOT_FOUND_RESPONSES, **VALIDATION_RESPONSES},
)
async def update_resume(
    resume_id: uuid.UUID,
    data: ResumeUpdate,
    user: CurrentUser,
    service: ResumeServiceDep,
    ctx: RequestContextDep,
) -> ResumeRead:
    return _read(await service.update(user.id, resume_id, data, ctx))


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a resume and its stored file",
    responses=NOT_FOUND_RESPONSES,
)
async def delete_resume(
    resume_id: uuid.UUID, user: CurrentUser, service: ResumeServiceDep, ctx: RequestContextDep
) -> Response:
    await service.delete(user.id, resume_id, ctx)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{resume_id}/file",
    summary="Download the original file",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}, **NOT_FOUND_RESPONSES},
)
async def download_resume(
    resume_id: uuid.UUID, user: CurrentUser, service: ResumeServiceDep
) -> Response:
    resume, data, content_type = await service.download(user.id, resume_id)
    filename = quote(resume.original_filename)
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "private, no-store",
        },
    )


@router.post(
    "/{resume_id}/parse",
    response_model=ResumeRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Parse the resume again",
    description="Use after a failure (for example once AI is configured).",
    responses={
        **NOT_FOUND_RESPONSES,
        409: {"model": ErrorResponse, "description": "Already processing"},
    },
)
async def reparse_resume(
    resume_id: uuid.UUID,
    user: CurrentUser,
    service: ResumeServiceDep,
    dispatcher: ParseDispatcherDep,
) -> ResumeRead:
    resume = await service.request_reparse(user.id, resume_id)
    return _read(await _dispatch(resume, dispatcher, service))


@router.get(
    "/{resume_id}/review",
    response_model=ResumeReview,
    summary="Differences between the resume and your profile",
    description="Conflicts (both have a value and they differ) and additions (the resume "
    "has something the profile lacks). Nothing is applied until you decide.",
    responses=NOT_FOUND_RESPONSES,
)
async def get_review(
    resume_id: uuid.UUID, user: CurrentUser, review: ResumeReviewServiceDep
) -> ResumeReview:
    return await review.review(user, resume_id)


@router.post(
    "/{resume_id}/review",
    response_model=ReviewApplyResult,
    summary="Apply review decisions to your profile",
    responses={**NOT_FOUND_RESPONSES, **VALIDATION_RESPONSES},
)
async def apply_review(
    resume_id: uuid.UUID,
    data: ReviewApplyRequest,
    user: CurrentUser,
    review: ResumeReviewServiceDep,
    ctx: RequestContextDep,
) -> ReviewApplyResult:
    return await review.apply(user, resume_id, data.decisions, ctx)
