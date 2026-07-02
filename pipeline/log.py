import logging
import sys

_FMT = "%(asctime)s | %(levelname)-8s | %(name)-10s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup(level: str = "INFO") -> None:
    """Configure root logger. Call once from runner.main() before any work starts."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=_FMT,
        datefmt=_DATEFMT,
        stream=sys.stderr,
        force=True,
    )
