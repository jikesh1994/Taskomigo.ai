from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, func, inspect, select

from app.core.database import Database
from app.core.security import utc_now
from app.models import Base, RefreshToken
from app.services.maintenance_service import purge_refresh_tokens
from app.workers.celery_app import celery_app
from tests.conftest import RegisteredUser

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(
    bool(os.environ.get("TEST_DATABASE_URL")), reason="migration test uses its own SQLite database"
)
def test_migrations_upgrade_match_models_and_downgrade(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}")
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["configure_logger"] = False

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    assert diff == [], f"Models and migrations differ: {diff}"

    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()


async def test_purge_refresh_tokens(user: RegisteredUser, database: Database) -> None:
    async with database.session_factory() as session:
        token = (await session.execute(select(RefreshToken))).scalar_one()
        now = utc_now()
        session.add_all(
            [
                RefreshToken(
                    user_id=token.user_id,
                    token_hash="a" * 64,
                    family_id=token.family_id,
                    expires_at=now - timedelta(days=1),
                ),
                RefreshToken(
                    user_id=token.user_id,
                    token_hash="b" * 64,
                    family_id=token.family_id,
                    expires_at=now + timedelta(days=1),
                    revoked_at=now - timedelta(days=30),
                ),
                RefreshToken(  # recently revoked: kept for reuse detection
                    user_id=token.user_id,
                    token_hash="c" * 64,
                    family_id=token.family_id,
                    expires_at=now + timedelta(days=1),
                    revoked_at=now - timedelta(hours=1),
                ),
            ]
        )
        await session.commit()

    async with database.session_factory() as session:
        assert await purge_refresh_tokens(session) == 2
        remaining = (await session.execute(select(func.count(RefreshToken.id)))).scalar_one()
    assert remaining == 2


def test_celery_configuration() -> None:
    celery_app.loader.import_default_modules()
    assert "maintenance.purge_refresh_tokens" in celery_app.tasks
    assert "maintenance.ping" in celery_app.tasks
    assert "resumes.parse" in celery_app.tasks
    assert celery_app.tasks["resumes.parse"].acks_late is True
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
    assert "purge-refresh-tokens" in celery_app.conf.beat_schedule
    assert celery_app.tasks["maintenance.ping"].apply().get() == "pong"
