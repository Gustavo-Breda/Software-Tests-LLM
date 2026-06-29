from __future__ import annotations

import time

from typing import Any, Optional

from .adapter import LLMClient, LLMResponse


class OllamaClient(LLMClient):
    provider = "ollama"

    def __init__(self, model: str, base_url: str = "http://localhost:11434", **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        try:
            from ollama import Client
        except ImportError as exc:
            raise ImportError(
                "The `ollama` package is required. Install via `pip install ollama`."
            ) from exc
        self._client = Client(host=base_url)
        self.base_url = base_url

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        messages = []

        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        start = time.perf_counter()
        response = self._client.chat(
            model=self.model,
            messages=messages,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        elapsed = time.perf_counter() - start

        msg = getattr(response, "message", None)
        text = getattr(msg, "content", None) or ""

        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.provider,
            latency_seconds=elapsed,
            prompt_tokens=getattr(response, "prompt_eval_count", None),
            completion_tokens=getattr(response, "eval_count", None),
            raw={},
        )
