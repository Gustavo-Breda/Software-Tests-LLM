import time

from typing import Any

from .adapter import LLMClient, LLMResponse


class ClaudeClient(LLMClient):
    provider = "claude"

    def __init__(self, model: str, api_key: str, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)

        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ImportError(
                "The `anthropic` package is required. Install via `pip install anthropic`."
            ) from exc
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set.")

        self._client = Anthropic(api_key=api_key)

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        start = time.perf_counter()
        response = self._client.messages.create(
            model=self.model,
            system=system or "You are a helpful assistant.",
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        elapsed = time.perf_counter() - start

        usage = getattr(response, "usage", None)

        return LLMResponse(
            text="".join(block.text for block in response.content if getattr(block, "type", None) == "text"),
            model=self.model,
            provider=self.provider,
            latency_seconds=elapsed,
            prompt_tokens=getattr(usage, "input_tokens", None) if usage else None,
            completion_tokens=getattr(usage, "output_tokens", None) if usage else None,
            raw={"stop_reason": response.stop_reason, "id": response.id},
        )
