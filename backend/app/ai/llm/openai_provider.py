"""OpenAI, or any OpenAI-compatible server for LLM_PROVIDER=local (Ollama, vLLM, …).

Optional dependency: `pip install ".[openai]"`.
"""

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

DEFAULT_MODEL = "gpt-5"
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

_UNAVAILABLE = "The AI service is busy right now. Please try again in a few minutes."
_FAILED = "The AI service couldn't process this request."


class OpenAIProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 120,
        max_retries: int = 2,
        name: str = "openai",
        client: Any = None,
    ) -> None:
        import openai

        self._sdk = openai
        self.name = name
        self.model = model or DEFAULT_MODEL
        self._client = client or openai.AsyncOpenAI(
            # Local servers usually ignore the key but the SDK requires one.
            api_key=api_key or "not-needed",
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def generate(self, *, system: str, prompt: str, max_tokens: int = 4096) -> str:
        completion = await self._call(
            self._client.chat.completions.create,
            model=self.model,
            max_completion_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        choice = completion.choices[0]
        self._check_finish(choice)
        return choice.message.content or ""

    async def generate_structured(
        self, *, system: str, prompt: str, output_model: type[T], max_tokens: int = 16000
    ) -> T:
        completion = await self._call(
            self._client.chat.completions.parse,
            model=self.model,
            max_completion_tokens=max_tokens,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            response_format=output_model,
        )
        choice = completion.choices[0]
        self._check_finish(choice)
        if choice.message.refusal:
            raise LLMRefusalError(
                "The AI declined to process this content.", detail=choice.message.refusal
            )
        if choice.message.parsed is None:
            raise LLMOutputError(_FAILED, detail="no parsed message")
        return choice.message.parsed

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self._call(
            self._client.embeddings.create, model=DEFAULT_EMBEDDING_MODEL, input=texts
        )
        return [item.embedding for item in response.data]

    def _check_finish(self, choice: Any) -> None:
        if choice.finish_reason == "length":
            raise LLMOutputError(_FAILED, detail="finish_reason=length")
        if choice.finish_reason == "content_filter":
            raise LLMRefusalError(
                "The AI declined to process this content.", detail="content_filter"
            )

    async def _call(self, method: Any, **kwargs: Any) -> Any:
        sdk = self._sdk
        try:
            return await method(**kwargs)
        except (sdk.AuthenticationError, sdk.PermissionDeniedError) as exc:
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
        except (sdk.LengthFinishReasonError, sdk.ContentFilterFinishReasonError) as exc:
            raise LLMOutputError(_FAILED, detail=type(exc).__name__) from exc
        except sdk.BadRequestError as exc:
            raise LLMError(_FAILED, detail=str(exc)) from exc
        except sdk.APIStatusError as exc:
            if exc.status_code >= 500:
                raise LLMUnavailableError(_UNAVAILABLE, detail=f"status {exc.status_code}") from exc
            raise LLMError(_FAILED, detail=f"status {exc.status_code}") from exc
        except (sdk.APIConnectionError, sdk.APITimeoutError) as exc:
            raise LLMUnavailableError(_UNAVAILABLE, detail=type(exc).__name__) from exc
        except sdk.OpenAIError as exc:
            raise LLMOutputError(_FAILED, detail=str(exc)) from exc
