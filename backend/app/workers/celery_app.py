"""Celery application. Long-running work never runs inside HTTP request handlers."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging


def create_celery(settings: Settings | None = None) -> Celery:
    settings = settings or get_settings()
    app = Celery("job_agent", broker=settings.broker_url, backend=settings.result_backend)
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        # A task is acknowledged only after it finishes, so a crashed worker's task is
        # redelivered. Tasks must therefore be idempotent.
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_time_limit=15 * 60,
        task_soft_time_limit=14 * 60,
        result_expires=24 * 60 * 60,
        broker_connection_retry_on_startup=True,
        task_default_queue="default",
        beat_schedule={
            "purge-refresh-tokens": {
                "task": "maintenance.purge_refresh_tokens",
                "schedule": crontab(minute=17),  # hourly
            },
        },
    )
    app.conf.task_routes = {"resumes.*": {"queue": "default"}, "jobs.*": {"queue": "default"}}
    app.autodiscover_tasks(["app.workers"], related_name="maintenance_tasks")
    app.autodiscover_tasks(["app.workers"], related_name="resume_tasks")
    app.autodiscover_tasks(["app.workers"], related_name="job_tasks")
    return app


@setup_logging.connect
def _configure_worker_logging(**_: object) -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_output=settings.log_json)


celery_app = create_celery()
