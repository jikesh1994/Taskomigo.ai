"""The company job boards a user searches."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import (
    ConflictError,
    DomainValidationError,
    NotFoundError,
    ServiceUnavailableError,
)
from app.jobs.catalog import CATALOG, CatalogEntry
from app.jobs.providers import BoardNotFoundError, JobSearchProvider, ProviderError, parse_source
from app.models.job import JobSource
from app.repositories.job_repository import JobRepository
from app.services.audit_service import AuditService, RequestContext

UNSUPPORTED_SOURCE = (
    "Paste a Greenhouse or Lever careers link (for example "
    "https://boards.greenhouse.io/stripe or https://jobs.lever.co/spotify)."
)


@dataclass(frozen=True, slots=True)
class CatalogItem:
    entry: CatalogEntry
    added: bool


class JobSourceService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        providers: dict[str, JobSearchProvider],
    ) -> None:
        self.session = session
        self.settings = settings
        self.providers = providers
        self.repo = JobRepository(session)
        self.audit = AuditService(session)

    async def list_for_user(self, user_id: uuid.UUID) -> list[JobSource]:
        return await self.repo.list_sources(user_id)

    async def catalog(self, user_id: uuid.UUID) -> list[CatalogItem]:
        added = {(s.platform, s.board) for s in await self.repo.list_sources(user_id)}
        return [CatalogItem(e, (e.platform, e.board) in added) for e in CATALOG]

    async def add(self, user_id: uuid.UUID, source: str, ctx: RequestContext) -> JobSource:
        parsed = parse_source(self.providers, source)
        if parsed is None:
            raise DomainValidationError(UNSUPPORTED_SOURCE, code="unsupported_source")
        platform, board = parsed
        provider = self.providers[platform]
        if not provider.valid_token(board):
            raise DomainValidationError(UNSUPPORTED_SOURCE, code="unsupported_source")
        if await self.repo.find_source(user_id, platform, board):
            raise ConflictError("You've already added this job board.", code="source_exists")
        if await self.repo.count_sources(user_id) >= self.settings.job_max_sources_per_user:
            raise ConflictError(
                f"You can add up to {self.settings.job_max_sources_per_user} job boards.",
                code="source_limit",
            )

        known = next((e for e in CATALOG if (e.platform, e.board) == (platform, board)), None)
        try:
            # Validates that the board exists before we save it.
            company = await provider.company_name(board)
        except BoardNotFoundError as exc:
            raise DomainValidationError(
                f"We couldn't find a {provider.display_name} job board called “{board}”.",
                code="source_not_found",
            ) from exc
        except ProviderError as exc:
            raise ServiceUnavailableError(
                f"{provider.display_name} couldn't be reached. Please try again.",
                code="source_unreachable",
            ) from exc
        if known:
            company = known.company

        item = JobSource(
            id=uuid.uuid4(),
            user_id=user_id,
            platform=platform,
            board=board,
            company_name=company[:200] or board,
            enabled=True,
        )
        self.repo.add(item)
        self.audit.record(
            "job_source.add",
            user_id=user_id,
            entity="job_source",
            entity_id=item.id,
            context=ctx,
            details={"platform": platform, "board": board},
        )
        await self.session.commit()
        return item

    async def set_enabled(
        self, user_id: uuid.UUID, source_id: uuid.UUID, enabled: bool
    ) -> JobSource:
        item = await self._get(user_id, source_id)
        item.enabled = enabled
        await self.session.commit()
        return item

    async def delete(self, user_id: uuid.UUID, source_id: uuid.UUID, ctx: RequestContext) -> None:
        item = await self._get(user_id, source_id)
        await self.repo.delete_unsaved_matches_for_board(user_id, item.platform, item.board)
        await self.repo.delete_source(item)
        self.audit.record(
            "job_source.delete",
            user_id=user_id,
            entity="job_source",
            entity_id=item.id,
            context=ctx,
            details={"platform": item.platform, "board": item.board},
        )
        await self.session.commit()

    async def _get(self, user_id: uuid.UUID, source_id: uuid.UUID) -> JobSource:
        item = await self.repo.get_source(user_id, source_id)
        if item is None:
            raise NotFoundError("Job source not found.")
        return item
