import abc

from typing import Any
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    latency_seconds: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient(abc.ABC):
    provider: str = "unknown"

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model
        self.options: dict[str, Any] = kwargs

    @abc.abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...

    @property
    def identifier(self) -> str:
        return f"{self.provider}:{self.model}"
