from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import REDACTED, redact

STRONG_A = "a" * 40
STRONG_B = "b" * 40


def test_production_rejects_default_secrets() -> None:
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, environment="production")
    message = str(exc.value)
    assert "SECRET_KEY" in message and "JWT_SECRET" in message and "ENCRYPTION_KEYS" in message


def test_empty_secrets_rejected_in_every_environment() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET must not be empty"):
        Settings(_env_file=None, environment="local", jwt_secret="  ")


def test_production_rejects_identical_secrets() -> None:
    with pytest.raises(ValidationError, match="must differ"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key=STRONG_A,
            jwt_secret=STRONG_A,
            encryption_keys=Fernet.generate_key().decode(),
        )


def test_production_accepts_strong_config() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        secret_key=STRONG_A,
        jwt_secret=STRONG_B,
        encryption_keys=Fernet.generate_key().decode(),
    )
    assert settings.is_production


def test_local_allows_defaults_and_builds_cors_list() -> None:
    settings = Settings(
        _env_file=None,
        environment="local",
        frontend_url="http://localhost:3000",
        cors_origins="https://a.example, https://b.example",
    )
    assert settings.cors_origin_list == [
        "https://a.example",
        "https://b.example",
        "http://localhost:3000",
    ]


def test_redact_nested_sensitive_values() -> None:
    event = {
        "event": "login",
        "email": "a@example.com",
        "password": "hunter2",
        "headers": {"Authorization": "Bearer abc", "Accept": "json"},
        "items": [{"refresh_token": "r"}, {"name": "ok"}],
        "LLM_API_KEY": "sk-123",
        "session_cookie": "c",
    }
    result = redact(event)
    assert result["password"] == REDACTED
    assert result["headers"]["Authorization"] == REDACTED
    assert result["headers"]["Accept"] == "json"
    assert result["items"][0]["refresh_token"] == REDACTED
    assert result["items"][1]["name"] == "ok"
    assert result["LLM_API_KEY"] == REDACTED
    assert result["session_cookie"] == REDACTED
    assert result["email"] == "a@example.com"
