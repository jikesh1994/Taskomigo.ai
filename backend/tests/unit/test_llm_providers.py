"""Provider adapters, tested against stand-in SDK clients (no network, no key)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import anthropic
import httpx
import openai
import pytest

from app.ai.llm.anthropic_provider import DEFAULT_MODEL, FALLBACK_BETA, AnthropicProvider
from app.ai.llm.base import (
    DisabledProvider,
    LLMNotConfiguredError,
    LLMOutputError,
    LLMRefusalError,
    LLMUnavailableError,
)
from app.ai.llm.factory import create_llm_provider
from app.ai.llm.openai_provider import OpenAIProvider
from app.ai.resume.schema import ParsedResume
from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from tests.resume_fixtures import parsed_resume


class Recorder:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result, self.error, self.calls = result, error, []

    async def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


def _anthropic(
    result: Any = None, error: Exception | None = None
) -> tuple[AnthropicProvider, Recorder]:
    parse = Recorder(result, error)
    client = SimpleNamespace(
        beta=SimpleNamespace(messages=SimpleNamespace(parse=parse, create=parse))
    )
    return AnthropicProvider(api_key="test", client=client), parse


def _status_error(sdk: Any, cls_name: str, status: int) -> Exception:
    request = httpx.Request("POST", "https://api.example.test/v1")
    response = httpx.Response(status, request=request, headers={"request-id": "req_1"})
    cls = getattr(sdk, cls_name)
    return cls("boom", response=response, body=None)


# ------------------------------------------------------------------ anthropic


async def test_anthropic_structured_request_shape() -> None:
    provider, parse = _anthropic(
        SimpleNamespace(stop_reason="end_turn", parsed_output=parsed_resume())
    )
    result = await provider.generate_structured(
        system="sys", prompt="resume", output_model=ParsedResume
    )

    assert result.full_name == "Priya Sharma"
    call = parse.calls[0]
    assert call["model"] == DEFAULT_MODEL == "claude-opus-5-5"
    assert call["output_format"] is ParsedResume
    assert call["output_config"] == {"effort": "low"}
    assert call["betas"] == [FALLBACK_BETA] and call["fallbacks"] == "default"
    assert call["system"] == "sys"
    assert call["messages"] == [{"role": "user", "content": "resume"}]


async def test_anthropic_refusal_and_truncation() -> None:
    refused = SimpleNamespace(
        stop_reason="refusal", stop_details=SimpleNamespace(category="cyber"), parsed_output=None
    )
    provider, _ = _anthropic(refused)
    with pytest.raises(LLMRefusalError):
        await provider.generate_structured(system="", prompt="", output_model=ParsedResume)

    provider, _ = _anthropic(SimpleNamespace(stop_reason="max_tokens", parsed_output=None))
    with pytest.raises(LLMOutputError):
        await provider.generate_structured(system="", prompt="", output_model=ParsedResume)


@pytest.mark.parametrize(
    ("cls_name", "status", "expected"),
    [
        ("AuthenticationError", 401, LLMNotConfiguredError),
        ("NotFoundError", 404, LLMNotConfiguredError),
        ("RateLimitError", 429, LLMUnavailableError),
        ("InternalServerError", 500, LLMUnavailableError),
    ],
)
async def test_anthropic_errors_are_mapped(
    cls_name: str, status: int, expected: type[Exception]
) -> None:
    provider, _ = _anthropic(error=_status_error(anthropic, cls_name, status))
    with pytest.raises(expected) as excinfo:
        await provider.generate_structured(system="", prompt="", output_model=ParsedResume)
    assert "boom" not in excinfo.value.message  # vendor details never reach users


async def test_anthropic_connection_error_is_retryable() -> None:
    error = anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.example.test"))
    provider, _ = _anthropic(error=error)
    with pytest.raises(LLMUnavailableError) as excinfo:
        await provider.generate_structured(system="", prompt="", output_model=ParsedResume)
    assert excinfo.value.retryable


# ------------------------------------------------------------------ openai / local


def _openai(result: Any = None, error: Exception | None = None) -> tuple[OpenAIProvider, Recorder]:
    parse = Recorder(result, error)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(parse=parse, create=parse))
    )
    return OpenAIProvider(api_key="test", model="gpt-test", client=client), parse


def _completion(parsed: Any = None, refusal: str | None = None, finish: str = "stop") -> Any:
    message = SimpleNamespace(parsed=parsed, refusal=refusal, content=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish)])


async def test_openai_structured_request_shape() -> None:
    provider, parse = _openai(_completion(parsed_resume()))
    result = await provider.generate_structured(
        system="sys", prompt="resume", output_model=ParsedResume
    )
    assert result.email == "priya.sharma@example.com"
    call = parse.calls[0]
    assert call["model"] == "gpt-test"
    assert call["response_format"] is ParsedResume
    assert call["messages"][0] == {"role": "system", "content": "sys"}


async def test_openai_refusal_length_and_errors() -> None:
    provider, _ = _openai(_completion(refusal="no"))
    with pytest.raises(LLMRefusalError):
        await provider.generate_structured(system="", prompt="", output_model=ParsedResume)

    provider, _ = _openai(_completion(finish="length"))
    with pytest.raises(LLMOutputError):
        await provider.generate_structured(system="", prompt="", output_model=ParsedResume)

    provider, _ = _openai(error=_status_error(openai, "RateLimitError", 429))
    with pytest.raises(LLMUnavailableError):
        await provider.generate_structured(system="", prompt="", output_model=ParsedResume)


# ------------------------------------------------------------------ factory


def _settings(**values: Any) -> Settings:
    return Settings(_env_file=None, **values)


def test_factory_selects_provider_by_configuration() -> None:
    assert isinstance(create_llm_provider(_settings()), DisabledProvider)
    anthropic_provider = create_llm_provider(_settings(llm_provider="anthropic", llm_api_key="k"))
    assert isinstance(anthropic_provider, AnthropicProvider)
    assert anthropic_provider.model == "claude-opus-5-5"
    openai_provider = create_llm_provider(
        _settings(llm_provider="openai", llm_api_key="k", llm_model="m")
    )
    assert isinstance(openai_provider, OpenAIProvider) and openai_provider.model == "m"
    local = create_llm_provider(
        _settings(llm_provider="local", llm_base_url="http://localhost:11434/v1", llm_model="llama")
    )
    assert isinstance(local, OpenAIProvider) and local.name == "local"


@pytest.mark.parametrize(
    "values",
    [
        {"llm_provider": "anthropic"},
        {"llm_provider": "openai"},
        {"llm_provider": "local", "llm_model": "x"},
    ],
)
def test_factory_rejects_incomplete_configuration(values: dict[str, Any]) -> None:
    with pytest.raises(ConfigurationError):
        create_llm_provider(_settings(**values))


async def test_disabled_provider_explains_itself() -> None:
    with pytest.raises(LLMNotConfiguredError) as excinfo:
        await DisabledProvider().generate_structured(
            system="", prompt="", output_model=ParsedResume
        )
    assert "isn't set up" in excinfo.value.message or "aren't set up" in excinfo.value.message
