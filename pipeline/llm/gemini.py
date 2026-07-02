import logging
import time

from typing import Any

from .adapter import LLMClient, LLMResponse

log = logging.getLogger("gemini")

# Models that support ThinkingConfig. Matched by prefix so versioned variants
# (e.g. gemini-2.5-flash-001) are also covered. "-lite" models are explicitly
# excluded — they do not support thinking and would fail with ThinkingConfig.
_THINKING_MODEL_PREFIXES = ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.1-flash")

# thinking budget for reproducibility
_THINKING_BUDGET = 8_192

# minimum total token budget for thinking models (thinking + output combined)
_GEMINI_MIN_OUTPUT_TOKENS = 16_384

_RETRYABLE = ("ServerError", "ServiceUnavailable", "TooManyRequests", "ResourceExhausted")


def _is_thinking_model(model: str) -> bool:
    if model.endswith("-lite"):
        return False
    return any(model.startswith(prefix) for prefix in _THINKING_MODEL_PREFIXES)


class GeminiClient(LLMClient):
    provider = "gemini"

    def __init__(self, model: str, api_key: str, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)

        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError as exc:
            raise ImportError(
                "The `google-genai` package is required. Install via `pip install google-genai>=1.5,<2.0`."
            ) from exc
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set.")

        self._genai = genai
        self._client = genai.Client(api_key=api_key)
        self._types = genai_types

        thinking = _is_thinking_model(model)
        log.debug("Model: %s | thinking=%s", model, thinking)

    def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        response = None
        finish_reason = None

        thinking = _is_thinking_model(self.model)
        thinking_config = (
            self._types.ThinkingConfig(thinking_budget=_THINKING_BUDGET)
            if thinking
            else None
        )
        effective_max = max(max_tokens, _GEMINI_MIN_OUTPUT_TOKENS) if thinking else max_tokens
        config = self._types.GenerateContentConfig(
            system_instruction=system,
            thinking_config=thinking_config,
            temperature=temperature,
            max_output_tokens=effective_max,
        )

        last_exc: Exception | None = None
        start = time.perf_counter()

        for attempt in range(3):
            try:
                log.debug(
                    "Request attempt %d — max_tokens=%d thinking=%s",
                    attempt + 1,
                    effective_max,
                    thinking,
                )
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                break
            except Exception as exc:
                exc_name = type(exc).__name__
                if attempt < 2 and any(kw in exc_name for kw in _RETRYABLE):
                    last_exc = exc
                    wait = 2 ** attempt
                    log.warning("Transient error (attempt %d): %s — retrying in %ds", attempt + 1, exc_name, wait)
                    time.sleep(wait)
                    continue
                raise

        elapsed = time.perf_counter() - start

        if response is None:
            raise RuntimeError("Gemini API failed after retries") from last_exc

        candidates = getattr(response, "candidates", None) or []
        if candidates:
            fr = getattr(candidates[0], "finish_reason", None)
            finish_reason = getattr(fr, "name", str(fr)) if fr is not None else None

        response_text = ""
        try:
            response_text = response.text or ""
        except ValueError:
            pass

        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        completion_tokens = getattr(usage, "candidates_token_count", None) if usage else None

        if usage:
            thoughts_tokens = getattr(usage, "thinking_token_count", None) or getattr(
                usage, "thoughts_token_count", None
            )
        else:
            thoughts_tokens = None

        log.debug(
            "Response in %.1fs | finish=%s | prompt_tok=%s | completion_tok=%s | thinking_tok=%s",
            elapsed,
            finish_reason,
            prompt_tokens,
            completion_tokens,
            thoughts_tokens,
        )

        return LLMResponse(
            text=response_text,
            model=self.model,
            provider=self.provider,
            latency_seconds=elapsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw={
                "candidates": candidates,
                "finish_reason": finish_reason,
                "thinking_token_count": thoughts_tokens,
            },
        )
