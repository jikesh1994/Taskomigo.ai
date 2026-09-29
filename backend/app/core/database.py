"""Async SQLAlchemy engine and session factory."""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


class Database:
    def __init__(
        self,
        url: str,
        *,
        echo: bool = False,
        pool_size: int = 10,
        max_overflow: int = 20,
        use_null_pool: bool = False,
    ) -> None:
        kwargs: dict[str, Any] = {"echo": echo, "pool_pre_ping": True}
        is_sqlite = url.startswith("sqlite")
        if use_null_pool:
            kwargs["poolclass"] = NullPool
        elif not is_sqlite:
            kwargs.update(pool_size=pool_size, max_overflow=max_overflow)

        self.engine: AsyncEngine = create_async_engine(url, **kwargs)
        if is_sqlite:
            event.listen(self.engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine, expire_on_commit=False, autoflush=False
        )

    async def dispose(self) -> None:
        await self.engine.dispose()


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
