import logging
from pathlib import Path

_FMT = "%(asctime)s | %(levelname)-8s | %(name)-10s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

_LOG_FILE = Path("pipeline.log")


def setup(level: str = "INFO") -> None:
    """Configure root logger to write to pipeline.log. Call once from runner.main()."""
    handler = logging.FileHandler(_LOG_FILE, mode="a", encoding="utf-8")
    handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATEFMT))

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # silence noisy SDK loggers
    for noisy in ("httpx", "google_genai", "google.auth"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
