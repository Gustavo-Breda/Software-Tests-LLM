from __future__ import annotations

import time

from typing import Any, Optional

from .adapter import LLMClient, LLMResponse


# models that support the ThinkingConfig API (budget for internal reasoning).
_THINKING_MODELS = ("gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.1-flash")

# thinking budget for reproducibility
_THINKING_BUDGET = 8_192

# minimum total token budget for thinking models (thinking + output combined)
_GEMINI_MIN_OUTPUT_TOKENS = 16_384

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

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        response = None
        finish_reason = None

        is_thinking_model = (
            any(self.model.startswith(m) for m in _THINKING_MODELS)
        )
        thinking_config = (
            self._types.ThinkingConfig(thinking_budget=_THINKING_BUDGET)
            if is_thinking_model
            else None
        )
        effective_max = (
            max(max_tokens, _GEMINI_MIN_OUTPUT_TOKENS) if is_thinking_model else max_tokens
        )
        config = self._types.GenerateContentConfig(
            system_instruction=system,
            thinking_config=thinking_config,
            temperature=temperature,
            max_output_tokens=effective_max,
        )

        # retry up to 3 times on transient server/quota errors so one API call does not abort the entire experiment run.
        last_exc: Optional[Exception] = None

        start = time.perf_counter()
        for attempt in range(3):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                break
            except Exception as exc:
                exc_name = type(exc).__name__
                if attempt < 2 and any(
                    kw in exc_name
                    for kw in ("ServerError", "ServiceUnavailable", "TooManyRequests", "ResourceExhausted")
                ):
                    last_exc = exc
                    time.sleep(2**attempt)
                    continue
                raise
        elapsed = time.perf_counter() - start

        # 
        if response is None:
            raise RuntimeError("Gemini API failed after retries") from last_exc
        
        #
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            fr = getattr(candidates[0], "finish_reason", None)
            finish_reason = (
                getattr(fr, "name", str(fr)) if fr is not None else None
            )

        # getting the response from gemini
        response_text = ""
        try:
            response_text = response.text or ""
        except ValueError:
            pass
        
        # group tokens metric
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        completion_tokens = getattr(usage, "candidates_token_count", None) if usage else None

        # thinking_token_count field name varies slightly by SDK patch version
        if usage:
            thoughts_tokens = getattr(usage, "thinking_token_count", None) or getattr(
                usage, "thoughts_token_count", None
            )
        else:
            thoughts_tokens = None

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
