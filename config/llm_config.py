"""
LLM Configuration — multi-provider support (OpenAI, Azure, Anthropic).

Single Responsibility: manages LLM client instantiation from environment config.
Auto-attaches cost tracking callbacks when session/stage context is provided.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            logger.info(
                "LLM config: provider=azure, endpoint=%s, deployment=%s, api_version=%s",
                endpoint.split("//")[-1].split("/")[0] if endpoint else "(empty)",
                deployment,
                api_version,
            )
            if not endpoint:
                logger.warning("AZURE_OPENAI_ENDPOINT is empty — check .env")
            return cls(
                provider=provider,
                api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
                model=deployment,
                endpoint=endpoint,
                api_version=api_version,
            )
        elif provider == "anthropic":
            model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
            logger.info("LLM config: provider=anthropic, model=%s", model)
            return cls(
                provider=provider,
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                model=model,
            )
        else:
            model = os.getenv("OPENAI_MODEL", "gpt-4")
            logger.info("LLM config: provider=openai, model=%s", model)
            return cls(
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                model=model,
            )

    @property
    def is_valid(self) -> bool:
        if self.provider == "azure":
            return bool(self.endpoint and self.api_key and self.model)
        return bool(self.api_key and self.model)


def get_llm(
    temperature: float | None = None,
    settings: Optional[LLMSettings] = None,
    session_id: str = "",
    stage: str = "",
):
    """
    Factory that returns a LangChain chat model for the configured provider.

    When session_id/stage are provided, auto-attaches a CostTrackingCallback
    so every invocation is automatically metered.

    When EMBEDFORGE_STAGE_MODELS is set, overrides the deployment/model
    per stage (e.g. use a cheaper model for refiner).

    Raises:
        ValueError: if settings are invalid or provider unsupported.
    """
    if settings is None:
        settings = LLMSettings.from_env()

    # Stage-based model override
    if stage:
        from config.settings import get_stage_models
        stage_models = get_stage_models()
        if stage in stage_models:
            settings = LLMSettings(
                provider=settings.provider,
                api_key=settings.api_key,
                model=stage_models[stage],
                endpoint=settings.endpoint,
                api_version=settings.api_version,
            )

    if not settings.is_valid:
        raise ValueError(
            f"Invalid LLM configuration for provider '{settings.provider}'. "
            "Check your environment variables."
        )

    callbacks: List[Any] = []
    if session_id or stage:
        from core.cost_tracker import CostTrackingCallback
        callbacks.append(CostTrackingCallback(session_id=session_id or "unknown", stage=stage or "unknown"))

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
        if callbacks:
            kwargs["callbacks"] = callbacks

        return AzureChatOpenAI(**kwargs)
    elif settings.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        kwargs = {"model": settings.model, "api_key": settings.api_key}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if callbacks:
            kwargs["callbacks"] = callbacks
        return ChatAnthropic(**kwargs)
    else:
        from langchain_openai import ChatOpenAI

        kwargs = {"model": settings.model, "api_key": settings.api_key}
        if temperature is not None:
            kwargs["temperature"] = temperature
        if callbacks:
            kwargs["callbacks"] = callbacks
        return ChatOpenAI(**kwargs)
