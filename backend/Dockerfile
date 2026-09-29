# syntax=docker/dockerfile:1.7
# One image serves the API, Celery worker, Celery beat and migrations;
# docker-compose / Cloud Run choose the command.

FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY pyproject.toml ./
COPY app ./app
RUN pip install --prefix=/install ".[anthropic,openai,s3]"

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # uvicorn trusts X-Forwarded-* only from these proxies (override behind a load balancer)
    FORWARDED_ALLOW_IPS=127.0.0.1
RUN groupadd --system app && useradd --system --gid app --home-dir /app --no-create-home app
COPY --from=builder /install /usr/local
WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app
# Local upload storage (mounted as a volume in compose; unused with S3/GCS).
RUN mkdir -p /app/data/uploads && chown -R app:app /app/data
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
