"""EmbedForge Configuration."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from config.llm_config import LLMSettings, get_llm
from config.settings import AppSettings

__all__ = ["LLMSettings", "get_llm", "AppSettings"]
