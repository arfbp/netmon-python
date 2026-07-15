"""Structured, rotating, JSON-formatted logging setup.

Contract: `configure_logging(settings)` is called exactly once, at
application startup (Step 4). Every other module obtains a logger via
`get_logger(__name__)` and logs with structured keyword fields
(`logger.info("ping.recorded", extra={"target": t, "latency_ms": lat})`),
never pre-formatted strings — so logs stay machine-parseable for the
history/analytics step (Step 15) and for any future log-shipping setup.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

try:
    from pythonjsonlogger.json import JsonFormatter
except ImportError:  # python-json-logger < 3.x
    from pythonjsonlogger.jsonlogger import JsonFormatter

from app.core.config import LoggingConfig

_CONFIGURED = False

_JSON_FORMAT_FIELDS = (
    "%(asctime)s %(levelname)s %(name)s %(message)s "
    "%(filename)s %(lineno)d %(funcName)s"
)


def configure_logging(config: LoggingConfig) -> None:
    """Idempotent: safe to call more than once (e.g. across test setup
    fixtures) — only the first call has an effect, guarded by module
    state rather than relying on every caller to remember not to."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    config.dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if config.debug else config.level)
    root.handlers.clear()

    formatter = JsonFormatter(_JSON_FORMAT_FIELDS, rename_fields={"levelname": "level"})

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=Path(config.dir) / "netmon.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,  # keep 5 rotated files (~50 MB ceiling)
            encoding="utf-8",
        )
    except OSError:
        root.warning(
            "logging.file_handler_disabled",
            extra={"log_dir": str(config.dir)},
        )
    else:
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    # Third-party libraries are noisy at DEBUG; keep them at WARNING even
    # when our own app is in debug mode, unless explicitly overridden.
    for noisy_logger in ("asyncio", "httpx", "aiosqlite"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Thin wrapper (not just `logging.getLogger`) so call sites import
    from `app.core.logging` consistently, and so a future change (e.g.
    contextvar-based request-id injection) has one place to land."""
    return logging.getLogger(name)


def reset_logging_for_tests() -> None:
    """Test-only escape hatch: allows a test to call `configure_logging`
    again with a different config (e.g. a tmp_path log dir) instead of
    being stuck with whatever configured logging first."""
    global _CONFIGURED
    _CONFIGURED = False
    logging.getLogger().handlers.clear()
