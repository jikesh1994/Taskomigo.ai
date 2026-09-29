from __future__ import annotations

import uuid
from unittest.mock import patch

from app.services.resume_dispatch import PARSE_TASK, CeleryParseDispatcher
from app.workers.celery_app import celery_app
from app.workers.resume_tasks import parse_resume_task


async def test_celery_dispatch_uses_the_configured_app_and_broker() -> None:
    resume_id = uuid.uuid4()
    with patch.object(celery_app, "send_task") as send_task:
        await CeleryParseDispatcher().dispatch(resume_id)
    send_task.assert_called_once_with(PARSE_TASK, args=[str(resume_id)])
    # The configured app talks to Redis, never Celery's default AMQP broker.
    assert celery_app.conf.broker_url.startswith("redis://")


def test_task_name_matches_the_worker() -> None:
    assert parse_resume_task.name == PARSE_TASK
