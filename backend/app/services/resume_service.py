"""Resume uploads and management. Parsing runs separately (see resume_parsing_service)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import PurePath

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    DomainValidationError,
    NotFoundError,
    PayloadTooLargeError,
    ServiceUnavailableError,
    UnsupportedMediaTypeError,
)
from app.core.logging import get_logger
from app.documents.extraction import CONTENT_TYPES, DocumentType, detect_type
from app.models.enums import ResumeFileType, ResumeParseStatus
from app.models.resume import Resume
from app.repositories.resume_repository import ResumeRepository
from app.schemas.resume import ResumeUpdate
from app.services.audit_service import AuditService, RequestContext
from app.storage import ObjectNotFoundError, ObjectStorage, StorageError

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ResumeFile:
    filename: str
    content_type: str
    data: bytes


def storage_key(user_id: uuid.UUID, resume_id: uuid.UUID) -> str:
    # No filename in the key: object names shouldn't carry personal data.
    return f"resumes/{user_id}/{resume_id}"


def clean_filename(filename: str | None) -> str:
    """The base name only, without control characters, for display and downloads."""
    name = PurePath((filename or "").replace("\\", "/")).name
    name = "".join(
        ch for ch in unicodedata.normalize("NFC", name) if unicodedata.category(ch)[0] != "C"
    )
    return name.strip()[:255] or "resume"


def default_display_name(filename: str) -> str:
    stem = re.sub(r"[_\-]+", " ", PurePath(filename).stem).strip()
    return (stem or "My resume")[:120]


class ResumeService:
    def __init__(self, session: AsyncSession, settings: Settings, storage: ObjectStorage) -> None:
        self.session = session
        self.settings = settings
        self.storage = storage
        self.repo = ResumeRepository(session)
        self.audit = AuditService(session)

    # ------------------------------------------------------------------ upload

    async def upload(
        self, user_id: uuid.UUID, file: ResumeFile, name: str | None, ctx: RequestContext
    ) -> Resume:
        size = len(file.data)
        limit_mb = self.settings.resume_max_bytes / (1024 * 1024)
        if size == 0:
            raise DomainValidationError("The uploaded file is empty.", code="file_empty")
        if size > self.settings.resume_max_bytes:
            raise PayloadTooLargeError(
                f"Resumes can be at most {limit_mb:g} MB.", code="file_too_large"
            )
        doc_type = detect_type(file.data)
        if doc_type is None:
            raise UnsupportedMediaTypeError(
                "Please upload a PDF or Word (.docx) file.", code="unsupported_file_type"
            )
        existing = await self.repo.count_for_user(user_id)
        if existing >= self.settings.resume_max_per_user:
            raise ConflictError(
                f"You can keep up to {self.settings.resume_max_per_user} resumes. "
                "Delete one to upload another.",
                code="resume_limit_reached",
            )
        digest = hashlib.sha256(file.data).hexdigest()
        duplicate = await self.repo.find_duplicate(user_id, digest)
        if duplicate is not None:
            raise ConflictError(
                f"You've already uploaded this file as “{duplicate.name}”.", code="resume_duplicate"
            )

        filename = clean_filename(file.filename)
        resume_id = uuid.uuid4()
        key = storage_key(user_id, resume_id)
        resume = Resume(
            id=resume_id,
            user_id=user_id,
            name=(name or "").strip()[:120] or default_display_name(filename),
            original_filename=filename,
            file_type=ResumeFileType(doc_type.value),
            size_bytes=size,
            sha256=digest,
            storage_key=key,
            is_default=existing == 0,  # the first resume becomes the default
            parse_status=ResumeParseStatus.PENDING,
            review_decisions={},
        )

        try:
            await self.storage.put(key, file.data, content_type=CONTENT_TYPES[doc_type])
        except StorageError as exc:
            logger.error("resume_store_failed", error=str(exc))
            raise ServiceUnavailableError("We couldn't save your file. Please try again.") from exc

        self.repo.add(resume)
        self.audit.record(
            "resume.upload",
            user_id=user_id,
            entity="resume",
            entity_id=resume_id,
            context=ctx,
            details={"file_type": doc_type.value, "size_bytes": size},
        )
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            await self._delete_object_quietly(key)
            raise
        return resume

    # ------------------------------------------------------------------ read

    async def list_for_user(self, user_id: uuid.UUID) -> list[Resume]:
        return await self.repo.list_for_user(user_id)

    async def get(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
        resume = await self.repo.get_for_user(user_id, resume_id)
        if resume is None:
            raise NotFoundError("Resume not found.")
        return resume

    async def download(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> tuple[Resume, bytes, str]:
        resume = await self.get(user_id, resume_id)
        try:
            data = await self.storage.get(resume.storage_key)
        except ObjectNotFoundError as exc:
            logger.error("resume_object_missing", resume_id=str(resume.id))
            raise NotFoundError("The file for this resume is missing.") from exc
        except StorageError as exc:
            raise ServiceUnavailableError("We couldn't load your file. Please try again.") from exc
        return resume, data, CONTENT_TYPES[DocumentType(resume.file_type.value)]

    # ------------------------------------------------------------------ write

    async def update(
        self, user_id: uuid.UUID, resume_id: uuid.UUID, data: ResumeUpdate, ctx: RequestContext
    ) -> Resume:
        resume = await self.get(user_id, resume_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            return resume
        if changes.get("is_default") and not resume.is_default:
            # Unset the old default first so the one-default-per-user index holds.
            await self.repo.clear_default(user_id)
            await self.session.flush()
            resume.is_default = True
        if "name" in changes:
            resume.name = changes["name"]
        self.audit.record(
            "resume.update",
            user_id=user_id,
            entity="resume",
            entity_id=resume.id,
            context=ctx,
            details={"fields": sorted(changes)},
        )
        await self.session.commit()
        await self.session.refresh(resume)
        return resume

    async def request_reparse(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
        resume = await self.get(user_id, resume_id)
        if resume.parse_status is ResumeParseStatus.PROCESSING:
            raise ConflictError(
                "This resume is being processed right now.", code="resume_processing"
            )
        resume.parse_status = ResumeParseStatus.PENDING
        resume.parse_error = None
        resume.parse_error_code = None
        await self.session.commit()
        return resume

    async def reload(self, resume: Resume) -> Resume:
        """Re-read after parsing, which may have run in another session (inline dispatch)."""
        await self.session.refresh(resume)
        return resume

    async def mark_dispatch_failed(self, resume: Resume) -> Resume:
        """The parse job couldn't be queued; say so instead of leaving it 'pending' forever."""
        await self.session.refresh(resume)
        if resume.parse_status is ResumeParseStatus.PENDING:
            resume.parse_status = ResumeParseStatus.FAILED
            resume.parse_error_code = "queue_unavailable"
            resume.parse_error = "We couldn't start reading your resume. Please try again."
            await self.session.commit()
        return resume

    async def delete(self, user_id: uuid.UUID, resume_id: uuid.UUID, ctx: RequestContext) -> None:
        resume = await self.get(user_id, resume_id)
        # Delete the file first: a failure leaves the record so the user can retry, rather
        # than an orphaned copy of their resume nobody can find.
        try:
            await self.storage.delete(resume.storage_key)
        except StorageError as exc:
            raise ServiceUnavailableError(
                "We couldn't delete your file. Please try again."
            ) from exc
        was_default = resume.is_default
        await self.repo.delete(resume)
        await self.session.flush()
        if was_default:
            replacement = await self.repo.newest_for_user(user_id)
            if replacement is not None:
                replacement.is_default = True
        self.audit.record(
            "resume.delete", user_id=user_id, entity="resume", entity_id=resume_id, context=ctx
        )
        await self.session.commit()

    async def _delete_object_quietly(self, key: str) -> None:
        try:
            await self.storage.delete(key)
        except StorageError:
            logger.error("resume_orphan_cleanup_failed", key=key)
