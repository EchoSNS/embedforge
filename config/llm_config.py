"""
LLM Configuration — multi-provider support (OpenAI, Azure, Anthropic).

Single Responsibility: manages LLM client instantiation from environment config.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMSettings:
    """Immutable LLM connection settings resolved from environment."""

    provider: str
    api_key: str
    model: str
    endpoint: Optional[str] = None
    api_version: Optional[str] = None

    @classmethod
    def from_env(cls) -> "LLMSettings":
        provider = os.getenv("LLM_PROVIDER", "openai").lower()

        if provider == "azure":
            return cls(
                provider=provider,
                api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
                endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            )
        elif provider == "anthropic":
            return cls(
                provider=provider,
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            )
        else:
            return cls(
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
            )

    @property
    def is_valid(self) -> bool:
        if self.provider == "azure":
            return bool(self.endpoint and self.api_key and self.model)
        return bool(self.api_key and self.model)


def get_llm(temperature: float | None = None, settings: Optional[LLMSettings] = None):
    """
    Factory that returns a LangChain chat model for the configured provider.

    Raises:
        ValueError: if settings are invalid or provider unsupported.
    """
    if settings is None:
        settings = LLMSettings.from_env()

    if not settings.is_valid:
        raise ValueError(
            f"Invalid LLM configuration for provider '{settings.provider}'. "
            "Check your environment variables."
        )

    if settings.provider == "azure":
        from langchain_openai import AzureChatOpenAI

        kwargs: dict = {
            "azure_endpoint": settings.endpoint,
            "api_key": settings.api_key,
            "api_version": settings.api_version,
            "azure_deployment": settings.model,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        return AzureChatOpenAI(**kwargs)
    elif settings.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {"model": settings.model, "api_key": settings.api_key}
        if temperature is not None:
            kwargs["temperature"] = temperature
        return ChatAnthropic(**kwargs)
    else:
        from langchain_openai import ChatOpenAI

        kwargs = {"model": settings.model, "api_key": settings.api_key}
        if temperature is not None:
            kwargs["temperature"] = temperature
        return ChatOpenAI(**kwargs)
