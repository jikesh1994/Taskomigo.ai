"""Claude via the official Anthropic SDK (optional dependency: `pip install ".[anthropic]"`)."""

from __future__ import annotations

from typing import Any

from app.ai.llm.base import (
    LLMError,
    LLMNotConfiguredError,
    LLMOutputError,
    LLMRefusalError,
    LLMUnavailableError,
    T,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-opus-5-5"
# Server-side fallback: if a request is declined by a safety classifier, the API
# re-runs it on an appropriate model within the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

_UNAVAILABLE = "The AI service is busy right now. Please try again in a few minutes."
_FAILED = "The AI service couldn't process this request."


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model: str | None = None,
        timeout: float = 120,
        max_retries: int = 2,
        effort: str = "low",
        client: Any = None,
    ) -> None:
        import anthropic

        self._sdk = anthropic
        self.model = model or DEFAULT_MODEL
        # Extraction-style tasks don't need deep reasoning; low effort keeps cost down.
        self._effort = effort
        self._client = client or anthropic.AsyncAnthropic(
            api_key=api_key, timeout=timeout, max_retries=max_retries
        )

    async def generate(self, *, system: str, prompt: str, max_tokens: int = 4096) -> str:
        response = await self._call(
            self._client.beta.messages.create,
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": self._effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        self._check_stop(response)
        return "".join(block.text for block in response.content if block.type == "text")

    async def generate_structured(
        self, *, system: str, prompt: str, output_model: type[T], max_tokens: int = 16000
    ) -> T:
        response = await self._call(
            self._client.beta.messages.parse,
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=output_model,
            output_config={"effort": self._effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        self._check_stop(response)
        parsed = response.parsed_output
        if parsed is None:
            raise LLMOutputError(_FAILED, detail="no parsed_output")
        return parsed

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise LLMError(
            "Embeddings aren't available from this AI provider.",
            detail="anthropic has no embeddings API",
        )

    def _check_stop(self, response: Any) -> None:
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise LLMRefusalError(
                "The AI declined to process this content.",
                detail=f"category={getattr(details, 'category', None)}",
            )
        if response.stop_reason == "max_tokens":
            raise LLMOutputError(_FAILED, detail="max_tokens reached")

    async def _call(self, method: Any, **kwargs: Any) -> Any:
        sdk = self._sdk
        try:
            return await method(**kwargs)
        # Most specific first: auth/permission/not-found are configuration problems,
        # rate limits and 5xx/connection errors are transient.
        except (sdk.AuthenticationError, sdk.PermissionDeniedError) as exc:
            logger.error("llm_auth_failed", provider=self.name, request_id=_request_id(exc))
            raise LLMNotConfiguredError(
                "The AI service rejected our credentials. Please check the API key.",
                detail=str(exc),
            ) from exc
        except sdk.NotFoundError as exc:
            raise LLMNotConfiguredError(
                f"The configured AI model ({self.model}) isn't available.", detail=str(exc)
            ) from exc
        except sdk.RateLimitError as exc:
            raise LLMUnavailableError(_UNAVAILABLE, detail="rate limited") from exc
        except sdk.BadRequestError as exc:
            logger.warning("llm_bad_request", provider=self.name, request_id=_request_id(exc))
            raise LLMError(_FAILED, detail=str(exc)) from exc
        except sdk.APIStatusError as exc:
            if exc.status_code >= 500:
                raise LLMUnavailableError(_UNAVAILABLE, detail=f"status {exc.status_code}") from exc
            raise LLMError(_FAILED, detail=f"status {exc.status_code}") from exc
        except (sdk.APIConnectionError, sdk.APITimeoutError) as exc:
            raise LLMUnavailableError(_UNAVAILABLE, detail=type(exc).__name__) from exc
        except sdk.AnthropicError as exc:  # e.g. SDK-side validation of the parsed output
            raise LLMOutputError(_FAILED, detail=str(exc)) from exc


def _request_id(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    return response.headers.get("request-id") if response is not None else None
