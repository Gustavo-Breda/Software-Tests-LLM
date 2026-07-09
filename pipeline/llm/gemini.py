import logging
import time

from typing import Any

from .adapter import LLMClient, LLMResponse

log = logging.getLogger("gemini")

_HTTP_TIMEOUT = 120  # 2 min — no thinking, responses are fast

# transient server errors — short exponential backoff (1s, 2s)
_RETRYABLE_SERVER = ("ServerError", "ServiceUnavailable", "TooManyRequests", "ResourceExhausted")
# connection/TLS hangs — longer fixed backoff (30s, 60s) to let rate-limit window reset
_RETRYABLE_TIMEOUT = ("TimeoutError", "ConnectTimeout", "ReadTimeout", "PoolTimeout", "ConnectError")


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
        self._types = genai_types
        self._client = genai.Client(
            api_key=api_key,
            http_options=genai_types.HttpOptions(timeout=_HTTP_TIMEOUT * 1000),
        )
        log.debug("Model: %s | timeout=%ds", model, _HTTP_TIMEOUT)

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

        config_args = {
            "system_instruction": system,
            "temperature": temperature,
        }
        if max_tokens and max_tokens < 8192:
            config_args["max_output_tokens"] = max_tokens

        config = self._types.GenerateContentConfig(**config_args)

        last_exc: Exception | None = None
        start = time.perf_counter()

        for attempt in range(3):
            try:
                log.debug("Request attempt %d — max_tokens=%d", attempt + 1, max_tokens)
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                print(f"[gemini] success attempt={attempt + 1}/3 model={self.model}")
                break
            except Exception as exc:
                exc_name = type(exc).__name__
                if attempt < 2:
                    if any(kw in exc_name for kw in _RETRYABLE_SERVER):
                        wait = 2 ** attempt
                        log.warning("Server error (attempt %d): %s — retrying in %ds", attempt + 1, exc_name, wait)
                        last_exc = exc
                        time.sleep(wait)
                        continue
                    if any(kw in exc_name for kw in _RETRYABLE_TIMEOUT):
                        wait = 30 * (attempt + 1)
                        log.warning("Connection timeout (attempt %d): %s — retrying in %ds", attempt + 1, exc_name, wait)
                        last_exc = exc
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

        print(
            f"[gemini] done model={self.model} latency={elapsed:.2f}s "
            f"prompt_tokens={prompt_tokens} completion_tokens={completion_tokens} "
            f"finish_reason={finish_reason}"
        )
        log.debug(
            "Response in %.1fs | finish=%s | prompt_tok=%s | completion_tok=%s",
            elapsed,
            finish_reason,
            prompt_tokens,
            completion_tokens,
        )

        # RECITATION/SAFETY: content was blocked — raise so the caller can handle it
        # (returning empty text would silently fail JSON parsing downstream)
        _BLOCKED = {"RECITATION", "SAFETY", "PROHIBITED_CONTENT", "SPII"}
        if finish_reason in _BLOCKED:
            raise RuntimeError(
                f"Gemini blocked response: finish_reason={finish_reason} model={self.model}"
            )

        return LLMResponse(
            text=response_text,
            model=self.model,
            provider=self.provider,
            latency_seconds=elapsed,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw={
                # Store only primitives — SDK Candidate objects are not JSON-serializable
                "finish_reason": finish_reason,
                "n_candidates": len(candidates),
            },
        )
