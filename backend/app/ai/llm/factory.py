from __future__ import annotations

from app.ai.llm.base import DisabledProvider, LLMProvider
from app.core.config import Settings
from app.core.exceptions import ConfigurationError


def create_llm_provider(settings: Settings) -> LLMProvider:
    """The provider selected by LLM_PROVIDER. Switching vendors is a configuration change."""
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    common = {
        "model": settings.llm_model or None,
        "timeout": settings.llm_timeout_seconds,
        "max_retries": settings.llm_max_retries,
    }
    match settings.llm_provider:
        case "none":
            return DisabledProvider()
        case "anthropic":
            if not key:
                raise ConfigurationError("LLM_API_KEY is required when LLM_PROVIDER=anthropic.")
            from app.ai.llm.anthropic_provider import AnthropicProvider

            return AnthropicProvider(api_key=key, **common)
        case "openai":
            if not key:
                raise ConfigurationError("LLM_API_KEY is required when LLM_PROVIDER=openai.")
            from app.ai.llm.openai_provider import OpenAIProvider

            return OpenAIProvider(api_key=key, **common)
        case "local":
            if not settings.llm_base_url or not settings.llm_model:
                raise ConfigurationError(
                    "LLM_BASE_URL and LLM_MODEL are required when LLM_PROVIDER=local."
                )
            from app.ai.llm.openai_provider import OpenAIProvider

            return OpenAIProvider(
                api_key=key, base_url=settings.llm_base_url, name="local", **common
            )
    raise ConfigurationError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
