"""Job-search data access.

Jobs are public postings shared by all users. Everything a user owns (sources, matches,
search runs) is always queried with their user id, so IDs can't be used across tenants.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Literal

from sqlalchemy import ColumnElement, and_, delete, func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobMatchStatus, SearchRunStatus
from app.models.job import Job, JobMatch, JobSource, SearchRun

MatchTab = Literal["matches", "saved", "skipped", "hidden"]


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, obj: Job | JobMatch | JobSource | SearchRun) -> None:
        self.session.add(obj)

    # ------------------------------------------------------------ sources

    async def list_sources(
        self, user_id: uuid.UUID, *, enabled_only: bool = False
    ) -> list[JobSource]:
        stmt = select(JobSource).where(JobSource.user_id == user_id)
        if enabled_only:
            stmt = stmt.where(JobSource.enabled.is_(True))
        result = await self.session.execute(stmt.order_by(JobSource.company_name))
        return list(result.scalars())

    async def get_source(self, user_id: uuid.UUID, source_id: uuid.UUID) -> JobSource | None:
        result = await self.session.execute(
            select(JobSource).where(JobSource.id == source_id, JobSource.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_source(self, user_id: uuid.UUID, platform: str, board: str) -> JobSource | None:
        result = await self.session.execute(
            select(JobSource).where(
                JobSource.user_id == user_id,
                JobSource.platform == platform,
                JobSource.board == board,
            )
        )
        return result.scalar_one_or_none()

    async def count_sources(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count(JobSource.id)).where(JobSource.user_id == user_id)
        )
        return int(result.scalar_one())

    async def delete_source(self, source: JobSource) -> None:
        await self.session.delete(source)

    async def delete_unsaved_matches_for_board(
        self, user_id: uuid.UUID, platform: str, board: str
    ) -> None:
        """Saved jobs stay; everything else from a removed source goes."""
        job_ids = select(Job.id).where(Job.platform == platform, Job.board == board)
        await self.session.execute(
            delete(JobMatch).where(
                JobMatch.user_id == user_id,
                JobMatch.job_id.in_(job_ids),
                JobMatch.status != JobMatchStatus.SAVED,
            )
        )

    # ------------------------------------------------------------ jobs

    async def jobs_by_external_id(
        self, platform: str, external_ids: Sequence[str]
    ) -> dict[str, Job]:
        if not external_ids:
            return {}
        found: dict[str, Job] = {}
        # Chunk to stay well under bind-parameter limits (SQLite: 32766).
        for start in range(0, len(external_ids), 500):
            chunk = list(external_ids[start : start + 500])
            result = await self.session.execute(
                select(Job).where(Job.platform == platform, Job.external_id.in_(chunk))
            )
            found.update({job.external_id: job for job in result.scalars()})
        return found

    async def active_jobs_for_board(self, platform: str, board: str) -> list[Job]:
        result = await self.session.execute(
            select(Job).where(Job.platform == platform, Job.board == board, Job.is_active.is_(True))
        )
        return list(result.scalars())

    async def active_jobs_for_boards(self, boards: Sequence[tuple[str, str]]) -> list[Job]:
        if not boards:
            return []
        result = await self.session.execute(
            select(Job)
            .where(tuple_(Job.platform, Job.board).in_(list(boards)), Job.is_active.is_(True))
            .order_by(Job.posted_at.desc().nulls_last(), Job.id)
        )
        return list(result.scalars())

    async def get_job(self, job_id: uuid.UUID) -> Job | None:
        return await self.session.get(Job, job_id, populate_existing=True)

    # ------------------------------------------------------------ matches

    async def matches_by_job(self, user_id: uuid.UUID) -> dict[uuid.UUID, JobMatch]:
        result = await self.session.execute(select(JobMatch).where(JobMatch.user_id == user_id))
        return {m.job_id: m for m in result.scalars()}

    async def get_match(self, user_id: uuid.UUID, job_id: uuid.UUID) -> tuple[JobMatch, Job] | None:
        result = await self.session.execute(
            select(JobMatch, Job)
            .join(Job, Job.id == JobMatch.job_id)
            .where(JobMatch.user_id == user_id, JobMatch.job_id == job_id)
            # Inline tasks update rows through another session; always read fresh values.
            .execution_options(populate_existing=True)
        )
        row = result.first()
        return (row[0], row[1]) if row else None

    async def delete_matches(self, user_id: uuid.UUID, job_ids: Sequence[uuid.UUID]) -> None:
        if job_ids:
            await self.session.execute(
                delete(JobMatch).where(
                    JobMatch.user_id == user_id,
                    JobMatch.job_id.in_(list(job_ids)),
                    JobMatch.status == JobMatchStatus.NEW,
                )
            )

    @staticmethod
    def _tab_filter(tab: MatchTab, min_score: int) -> ColumnElement[bool]:
        visible = and_(
            JobMatch.excluded_reason.is_(None),
            JobMatch.overall_match >= min_score,
            Job.is_active.is_(True),
        )
        if tab == "saved":
            return JobMatch.status == JobMatchStatus.SAVED
        if tab == "skipped":
            return JobMatch.status == JobMatchStatus.SKIPPED
        new = JobMatch.status == JobMatchStatus.NEW
        if tab == "matches":
            return and_(new, visible)
        # hidden: filtered out, or below the user's minimum score (closed jobs just drop off)
        return and_(
            new,
            Job.is_active.is_(True),
            or_(JobMatch.excluded_reason.is_not(None), JobMatch.overall_match < min_score),
        )

    async def list_matches(
        self,
        user_id: uuid.UUID,
        *,
        tab: MatchTab,
        min_score: int,
        query: str | None,
        workplace: str | None,
        sort: Literal["score", "newest"],
        limit: int,
        offset: int,
    ) -> tuple[list[tuple[JobMatch, Job]], int]:
        conditions: list[ColumnElement[bool]] = [
            JobMatch.user_id == user_id,
            self._tab_filter(tab, min_score),
        ]
        if query:
            like = f"%{query.strip().lower()}%"
            conditions.append(
                or_(func.lower(Job.title).like(like), func.lower(Job.company).like(like))
            )
        if workplace:
            conditions.append(Job.workplace == workplace)
        base = select(JobMatch, Job).join(Job, Job.id == JobMatch.job_id).where(*conditions)
        order = (
            [JobMatch.overall_match.desc(), Job.posted_at.desc().nulls_last()]
            if sort == "score"
            else [Job.posted_at.desc().nulls_last(), JobMatch.overall_match.desc()]
        )
        rows = await self.session.execute(base.order_by(*order, Job.id).limit(limit).offset(offset))
        total = await self.session.execute(
            select(func.count()).select_from(base.with_only_columns(JobMatch.id).subquery())
        )
        return [(m, j) for m, j in rows.tuples()], int(total.scalar_one())

    async def tab_counts(self, user_id: uuid.UUID, min_score: int) -> dict[str, int]:
        counts: dict[str, int] = {}
        for tab in ("matches", "saved", "skipped", "hidden"):
            result = await self.session.execute(
                select(func.count(JobMatch.id))
                .join(Job, Job.id == JobMatch.job_id)
                .where(JobMatch.user_id == user_id, self._tab_filter(tab, min_score))  # type: ignore[arg-type]
            )
            counts[tab] = int(result.scalar_one())
        return counts

    async def new_matches_since(self, user_id: uuid.UUID, since: datetime, min_score: int) -> int:
        result = await self.session.execute(
            select(func.count(JobMatch.id))
            .join(Job, Job.id == JobMatch.job_id)
            .where(
                JobMatch.user_id == user_id,
                self._tab_filter("matches", min_score),
                Job.first_seen_at >= since,
            )
        )
        return int(result.scalar_one())

    # ------------------------------------------------------------ search runs

    async def get_run(self, user_id: uuid.UUID, run_id: uuid.UUID) -> SearchRun | None:
        result = await self.session.execute(
            select(SearchRun)
            .where(SearchRun.id == run_id, SearchRun.user_id == user_id)
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_run_by_id(self, run_id: uuid.UUID) -> SearchRun | None:
        """Unscoped: only for the trusted search worker."""
        return await self.session.get(SearchRun, run_id, populate_existing=True)

    async def latest_run(self, user_id: uuid.UUID) -> SearchRun | None:
        result = await self.session.execute(
            select(SearchRun)
            .where(SearchRun.user_id == user_id)
            .order_by(SearchRun.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def active_run(self, user_id: uuid.UUID, since: datetime) -> SearchRun | None:
        result = await self.session.execute(
            select(SearchRun)
            .where(
                SearchRun.user_id == user_id,
                SearchRun.status.in_([SearchRunStatus.QUEUED, SearchRunStatus.RUNNING]),
                SearchRun.created_at >= since,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
