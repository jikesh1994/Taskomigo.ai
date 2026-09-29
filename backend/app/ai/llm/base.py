from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """An LLM call failed. `message` is safe to show users; details go to logs."""

    code = "ai_error"
    retryable = False

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class LLMNotConfiguredError(LLMError):
    code = "ai_not_configured"


class LLMUnavailableError(LLMError):
    """Rate limits, timeouts, overload, 5xx, network: worth retrying later."""

    code = "ai_unavailable"
    retryable = True


class LLMRefusalError(LLMError):
    code = "ai_refused"


class LLMOutputError(LLMError):
    """The model's output was missing, truncated or didn't match the schema."""

    code = "ai_invalid_output"


class LLMProvider(Protocol):
    """What the rest of the app may ask of a model."""

    name: str
    model: str

    async def generate(self, *, system: str, prompt: str, max_tokens: int = 4096) -> str: ...

    async def generate_structured(
        self, *, system: str, prompt: str, output_model: type[T], max_tokens: int = 16000
    ) -> T:
        """Return a validated instance of `output_model`."""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class DisabledProvider:
    """LLM_PROVIDER=none: every call fails with a clear, user-safe message."""

    name = "none"
    model = "none"
    _message = (
        "AI features aren't set up yet, so this couldn't be processed. Please try again later."
    )

    async def generate(self, *, system: str, prompt: str, max_tokens: int = 4096) -> str:
        raise LLMNotConfiguredError(self._message)

    async def generate_structured(
        self, *, system: str, prompt: str, output_model: type[T], max_tokens: int = 16000
    ) -> T:
        raise LLMNotConfiguredError(self._message)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise LLMNotConfiguredError(self._message)
