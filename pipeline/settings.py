import os

from dotenv import load_dotenv
from pathlib import Path
from dataclasses import dataclass, field


def _load_env() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_int(name: str, default: int) -> int:
    # tolerates empty strings (VAR=) without raising
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    claude_model: str = "claude-sonnet-4-6"
    ollama_base_url: str = "http://localhost:11434"
    ollama_models: list[str] = field(default_factory=lambda: ["llama3"])
    log_level: str = "INFO"
    random_seed: int = 42

    @classmethod
    def from_env(cls) -> "Settings":
        _load_env()
        return cls(
            google_api_key=os.getenv("GOOGLE_API_KEY") or None,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_models=_split_csv(os.getenv("OLLAMA_MODELS")) or ["llama3"],
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            random_seed=_env_int("RANDOM_SEED", 42),
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings
