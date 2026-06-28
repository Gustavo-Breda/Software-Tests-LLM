from __future__ import annotations

import abc

from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    latency_seconds: float = 0.0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

class LLMClient(abc.ABC):
    provider: str = "unknown"

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self.options: Dict[str, Any] = kwargs

    @abc.abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Send `prompt` (optionally with a `system` instruction) and return text."""

    @property
    def identifier(self) -> str:
        return f"{self.provider}:{self.model}"
