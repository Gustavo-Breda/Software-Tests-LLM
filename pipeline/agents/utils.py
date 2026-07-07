import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


REPO_ROOT = Path(__file__).resolve().parents[2]


class AgentOutputError(ValueError):
    pass


class RawAgentResponseError(AgentOutputError):
    def __init__(
        self,
        message: str,
        *,
        raw_text: str,
        provider: str,
        model: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.raw_text = raw_text
        self.provider = provider
        self.model = model
        self.metadata = metadata or {}


def wrap_raw_response_error(exc: AgentOutputError, response: Any) -> RawAgentResponseError:
    if isinstance(exc, RawAgentResponseError):
        return exc
    return RawAgentResponseError(
        str(exc),
        raw_text=getattr(response, "text", ""),
        provider=getattr(response, "provider", ""),
        model=getattr(response, "model", ""),
        metadata={
            "latency_seconds": getattr(response, "latency_seconds", 0.0),
            "prompt_tokens": getattr(response, "prompt_tokens", None),
            "completion_tokens": getattr(response, "completion_tokens", None),
            "raw": getattr(response, "raw", {}),
        },
    )


def load_prompt(name: str) -> str:
    path = REPO_ROOT / "pipeline" / "prompts" / name
    if not path.is_file():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise AgentOutputError("LLM response did not contain a valid JSON object.")


def validate_schema(data: dict[str, Any], schema_name: str) -> None:
    path = REPO_ROOT / "pipeline" / "schemas" / schema_name
    if not path.is_file():
        raise FileNotFoundError(f"Schema not found: {path}")
    schema = json.loads(path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=_error_sort_key)
    if errors:
        raise AgentOutputError(_format_validation_error(errors[0]))


def _error_sort_key(error: ValidationError) -> tuple[list[Any], str]:
    return list(error.path), error.message


def _format_validation_error(error: ValidationError) -> str:
    location = ".".join(str(part) for part in error.path) or "<root>"
    return f"Schema validation failed at {location}: {error.message}"
