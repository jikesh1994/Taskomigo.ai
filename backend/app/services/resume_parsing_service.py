"""Turn a stored resume into structured, grounded data. Runs in the worker."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.base import LLMError, LLMProvider
from app.ai.resume.parser import ResumeParser
from app.core.logging import get_logger
from app.core.security import utc_now
from app.documents.extraction import DocumentError, DocumentType, extract_text
from app.models.enums import ResumeParseStatus
from app.models.resume import Resume
from app.repositories.resume_repository import ResumeRepository
from app.storage import ObjectStorage, StorageError

logger = get_logger(__name__)

# Fewer characters than this after extraction means there is effectively no text layer.
MIN_TEXT_CHARS = 80

NO_TEXT_MESSAGE = (
    "We couldn't find any text in this file. If it's a scanned image, please upload a "
    "text-based PDF or a Word document."
)


async def parse_resume(
    session: AsyncSession,
    storage: ObjectStorage,
    provider: LLMProvider,
    resume_id: uuid.UUID,
    *,
    max_pages: int = 20,
) -> Resume | None:
    """Parse one resume and record the outcome on it.

    Idempotent: a resume that's already parsed is left alone, so a redelivered task
    (acks_late) does no duplicate AI work. Failures are stored on the resume with a
    user-safe message; the user can ask to parse it again.
    """
    repo = ResumeRepository(session)
    resume = await repo.get_by_id(resume_id)
    if resume is None:
        logger.info("resume_parse_skipped_missing", resume_id=str(resume_id))
        return None
    if resume.parse_status is ResumeParseStatus.PARSED:
        return resume

    resume.parse_status = ResumeParseStatus.PROCESSING
    await session.commit()
    log = logger.bind(resume_id=str(resume.id))

    try:
        data = await storage.get(resume.storage_key)
        extracted = extract_text(data, DocumentType(resume.file_type.value), max_pages=max_pages)
        resume.parsed_text = extracted.text
        if len(extracted.text) < MIN_TEXT_CHARS:
            raise DocumentError(NO_TEXT_MESSAGE, code="no_text")
        outcome = await ResumeParser(provider).parse(extracted.text)
    except DocumentError as exc:
        _fail(resume, exc.code, exc.message)
        log.info("resume_parse_failed", code=exc.code)
    except LLMError as exc:
        _fail(resume, exc.code, exc.message)
        log.warning("resume_parse_failed", code=exc.code, detail=exc.detail)
    except StorageError as exc:
        _fail(resume, "storage_unavailable", "We couldn't read your stored file. Please try again.")
        log.error("resume_parse_failed", code="storage_unavailable", detail=str(exc))
    except Exception:
        _fail(
            resume,
            "internal_error",
            "Something went wrong while reading your resume. Please try again.",
        )
        log.exception("resume_parse_crashed")
    else:
        resume.parsed_data = outcome.resume.model_dump(mode="json")
        resume.parser = outcome.parser
        resume.prompt_version = outcome.prompt_id
        resume.parsed_at = utc_now()
        resume.parse_status = ResumeParseStatus.PARSED
        resume.parse_error = None
        resume.parse_error_code = None
        # A new parse invalidates earlier review decisions (item ids depend on content).
        resume.review_decisions = {}
        log.info(
            "resume_parsed",
            parser=outcome.parser,
            skills=len(outcome.resume.skills),
            experiences=len(outcome.resume.experiences),
            removed=len(outcome.removed),
        )
    await session.commit()
    return resume


def _fail(resume: Resume, code: str, message: str) -> None:
    resume.parse_status = ResumeParseStatus.FAILED
    resume.parse_error_code = code
    resume.parse_error = message[:500]
