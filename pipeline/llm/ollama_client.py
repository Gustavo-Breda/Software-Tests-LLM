import time

from typing import Any

from .adapter import LLMClient, LLMResponse


class OllamaClient(LLMClient):
    provider = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        num_ctx: int = 32768,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, **kwargs)
        try:
            from ollama import Client
        except ImportError as exc:
            raise ImportError(
                "The `ollama` package is required. Install via `pip install ollama`."
            ) from exc
        self._client = Client(host=base_url)
        self.base_url = base_url
        self.num_ctx = num_ctx

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        messages = []

        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        print(
            f"[ollama] request model={self.model} base_url={self.base_url} "
            f"temp={temperature} max_tokens={max_tokens} num_ctx={self.num_ctx}"
        )

        start = time.perf_counter()
        try:
            response = self._client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "num_ctx": self.num_ctx,
                },
            )
        except Exception as exc:
            print(f"[ollama] error model={self.model} type={type(exc).__name__}: {exc}")
            raise
        elapsed = time.perf_counter() - start

        msg = getattr(response, "message", None)
        text = getattr(msg, "content", None) or ""
        prompt_tokens = getattr(response, "prompt_eval_count", None)
        completion_tokens = getattr(response, "eval_count", None)
        done_reason = getattr(response, "done_reason", None)
        print(
            f"[ollama] done model={self.model} latency={elapsed:.2f}s "
            f"prompt_tokens={prompt_tokens} completion_tokens={completion_tokens} "
            f"done_reason={done_reason} num_ctx={self.num_ctx}"
        )

        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.provider,
            latency_seconds=elapsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw={"done_reason": done_reason},
        )
