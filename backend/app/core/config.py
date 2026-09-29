"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "change-me"  # noqa: S105 - sentinel, rejected in production
MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Typed settings. Every value can be overridden through the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Taskomigo API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    log_json: bool = True

    # Infrastructure
    database_url: str = "postgresql+asyncpg://jobagent:jobagent@localhost:5432/jobagent"
    database_pool_size: int = Field(default=10, ge=1)
    database_max_overflow: int = Field(default=20, ge=0)
    database_echo: bool = False
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    # Security
    secret_key: SecretStr = SecretStr(INSECURE_DEFAULT_SECRET)
    jwt_secret: SecretStr = SecretStr(INSECURE_DEFAULT_SECRET)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "job-agent"
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_ttl_days: int = Field(default=14, ge=1, le=90)
    refresh_cookie_name: str = "refresh_token"
    # Comma-separated Fernet keys. The first key encrypts; all keys decrypt (rotation).
    encryption_keys: SecretStr = SecretStr("")
    password_min_length: int = Field(default=10, ge=8)

    # Rate limiting (per client IP, fixed window)
    rate_limit_auth_requests: int = Field(default=10, ge=1)
    rate_limit_auth_window_seconds: int = Field(default=60, ge=1)
    # Failed sign-ins allowed per account (any IP) within the window.
    login_max_failures_per_account: int = Field(default=10, ge=1)
    login_failure_window_seconds: int = Field(default=900, ge=60)

    # Web
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = ""

    # Product limits
    max_applications_per_day_cap: int = Field(default=100, ge=1)
    max_concurrent_browser_sessions_cap: int = Field(default=5, ge=1)
    max_retries_per_application_cap: int = Field(default=5, ge=0)

    # AI. "none" disables AI features: resume parsing fails with a clear message and
    # can be retried once a provider is configured.
    llm_provider: Literal["none", "anthropic", "openai", "local"] = "none"
    llm_api_key: SecretStr | None = None
    # Model id; empty means the provider's default (see app/ai/llm/factory.py).
    llm_model: str | None = None
    # Base URL for "local" (any OpenAI-compatible server, e.g. Ollama or vLLM).
    llm_base_url: str | None = None
    llm_timeout_seconds: float = Field(default=120, gt=0)
    llm_max_retries: int = Field(default=2, ge=0, le=10)

    # Object storage. "gcs" uses Google Cloud Storage's S3-compatible XML API
    # (HMAC keys); "s3" works with AWS S3 and S3-compatible stores (e.g. MinIO).
    storage_backend: Literal["local", "gcs", "s3"] = "local"
    storage_local_path: str = "./data/uploads"
    storage_bucket: str | None = None
    storage_access_key: SecretStr | None = None
    storage_secret_key: SecretStr | None = None
    storage_endpoint_url: str | None = None
    storage_region: str | None = None

    # Job search (public ATS job-board APIs)
    greenhouse_api_base: str = "https://boards-api.greenhouse.io"
    lever_api_base: str = "https://api.lever.co"
    job_fetch_timeout_seconds: float = Field(default=20, gt=0)
    job_fetch_concurrency: int = Field(default=4, ge=1, le=20)
    job_max_sources_per_user: int = Field(default=50, ge=1)
    # Run search/analysis inside the API request instead of the worker (tests / dev).
    job_tasks_inline: bool = False

    # Resumes
    resume_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)
    resume_max_per_user: int = Field(default=10, ge=1)
    resume_max_pages: int = Field(default=20, ge=1)
    # Parse inside the API request instead of the worker queue (tests / no-worker dev).
    resume_parse_inline: bool = False

    @property
    def is_production(self) -> bool:
        return self.environment in ("staging", "production")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.frontend_url and self.frontend_url not in origins:
            origins.append(self.frontend_url)
        return origins

    @property
    def encryption_key_list(self) -> list[str]:
        raw = self.encryption_keys.get_secret_value()
        return [k.strip() for k in raw.split(",") if k.strip()]

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @model_validator(mode="after")
    def _validate_production_safety(self) -> Settings:
        # Never allow an empty signing key, whatever the environment.
        for name in ("secret_key", "jwt_secret"):
            if not getattr(self, name).get_secret_value().strip():
                raise ValueError(f"{name.upper()} must not be empty")
        if not self.is_production:
            return self
        problems: list[str] = []
        for name in ("secret_key", "jwt_secret"):
            value: SecretStr = getattr(self, name)
            secret = value.get_secret_value()
            if secret == INSECURE_DEFAULT_SECRET or len(secret) < MIN_PRODUCTION_SECRET_LENGTH:
                problems.append(
                    f"{name.upper()} must be set to a random value of at least "
                    f"{MIN_PRODUCTION_SECRET_LENGTH} characters"
                )
        if self.secret_key.get_secret_value() == self.jwt_secret.get_secret_value():
            problems.append("SECRET_KEY and JWT_SECRET must differ")
        if not self.encryption_key_list:
            problems.append("ENCRYPTION_KEYS must be configured")
        if self.debug:
            problems.append("DEBUG must be false")
        if problems:
            raise ValueError("Unsafe production configuration: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
