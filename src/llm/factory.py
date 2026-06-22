from __future__ import annotations

from typing import List

from ..config import Settings, get_settings
from .adapter import LLMClient
from .claude import ClaudeClient
from .gemini import GeminiClient
from .ollama_client import OllamaClient


def get_client(identifier: str, settings: Settings | None = None) -> LLMClient:
    """Instantiate a client from an ``<provider>[:<model>]`` identifier.

    Examples
    --------
    >>> get_client("ollama:llama3")
    >>> get_client("gemini")            # uses GEMINI_MODEL from .env
    >>> get_client("claude:claude-3-5-sonnet-latest")
    """
    settings = settings or get_settings()

    if ":" in identifier:
        provider, model = identifier.split(":", 1)
    else:
        provider, model = identifier, ""

    provider = provider.lower().strip()

    if provider == "ollama":
        return OllamaClient(
            model=model or (settings.ollama_models[0] if settings.ollama_models else "llama3"),
            base_url=settings.ollama_base_url,
        )
    if provider == "gemini":
        return GeminiClient(
            model=model or settings.gemini_model,
            api_key=settings.google_api_key or "",
        )
    if provider in {"claude", "anthropic"}:
        return ClaudeClient(
            model=model or settings.claude_model,
            api_key=settings.anthropic_api_key or "",
        )
    raise ValueError(f"Unknown LLM provider: {provider!r}")


def list_available_clients(settings: Settings | None = None) -> List[str]:
    """Return the identifiers that *could* be instantiated given current env."""
    settings = settings or get_settings()
    available: List[str] = [f"ollama:{m}" for m in settings.ollama_models]
    if settings.google_api_key:
        available.append(f"gemini:{settings.gemini_model}")
    if settings.anthropic_api_key:
        available.append(f"claude:{settings.claude_model}")
    return available
