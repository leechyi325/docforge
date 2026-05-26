from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, cast


ProviderName = Literal[
    "local",
    "openai-responses",
    "openai-compatible",
    "anthropic-messages",
]

_SUPPORTED_PROVIDERS: set[str] = {
    "local",
    "openai",
    "openai-responses",
    "openai-compatible",
    "anthropic-messages",
}

DEFAULT_OPENAI_RESPONSES_MODEL = "gpt-4.1-mini"


def normalize_provider(provider: str) -> ProviderName:
    normalized = provider.strip().lower()
    if normalized == "openai":
        normalized = "openai-responses"
    if normalized not in _SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported llm provider: {provider}")
    return cast(ProviderName, normalized)


@dataclass(frozen=True)
class LlmSettings:
    provider: str = "local"
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None

    @property
    def normalized_provider(self) -> ProviderName:
        return normalize_provider(self.provider)

    def api_key_or_env(self) -> str | None:
        if self.api_key:
            return self.api_key
        env_var = (
            "ANTHROPIC_API_KEY"
            if self.normalized_provider == "anthropic-messages"
            else "OPENAI_API_KEY"
        )
        return os.environ.get(env_var)

    def model_or_env(self) -> str | None:
        if self.model:
            return self.model
        if os.environ.get("DOCFORGE_LLM_MODEL"):
            return os.environ["DOCFORGE_LLM_MODEL"]
        if self.normalized_provider == "openai-responses":
            return DEFAULT_OPENAI_RESPONSES_MODEL
        return None

    def base_url_or_env(self) -> str | None:
        return self.base_url or os.environ.get("DOCFORGE_LLM_BASE_URL")

    def validate_for_remote_use(self) -> None:
        if self.normalized_provider == "local":
            return
        if not self.model_or_env():
            raise ValueError(f"{self.normalized_provider} requires --llm-model")
        if not self.api_key_or_env():
            raise ValueError(f"{self.normalized_provider} requires --api-key")
