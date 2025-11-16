"""Central logging configuration for SidecarEQ.

This module configures a console logger by default and can be extended to
write logs to a file in the user's config directory.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from . import store


_LOGGER_NAME_PREFIX = "sidecareq"
_DEFAULT_LEVEL = logging.INFO


def _get_log_file_path() -> Path:
    """Return the path to the main SidecarEQ log file.

    We reuse the config directory used by ``store`` and place ``sidecareq.log``
    in it. If anything goes wrong, we fall back to a log file in the user's
    home directory.
    """

    try:
        config_dir = store._config_dir()  # type: ignore[attr-defined]
        return config_dir / "sidecareq.log"
    except Exception:
        return Path.home() / ".sidecareq.log"


def configure_logging(level: int | None = None) -> None:
    """Configure the root SidecarEQ logger.

    This function is idempotent and safe to call multiple times. It will not
    add duplicate handlers if called more than once.
    """

    log_level_name = os.getenv("SIDECAR_LOG_LEVEL")
    resolved_level: int
    if level is None:
        if log_level_name:
            resolved_level = int(getattr(logging, log_level_name.upper(), _DEFAULT_LEVEL))
        else:
            resolved_level = _DEFAULT_LEVEL
    else:
        resolved_level = int(level)

    logger = logging.getLogger(_LOGGER_NAME_PREFIX)
    if logger.handlers:
        # Already configured.
        logger.setLevel(resolved_level)
        return

    logger.setLevel(resolved_level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (stderr)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Optional file handler
    try:
        log_file = _get_log_file_path()
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(resolved_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception:
        # If file logging fails, we silently fall back to console-only.
        pass


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger for the given module name.

    Example::

        from .logging_config import get_logger
        logger = get_logger(__name__)
    """

    if name is None:
        return logging.getLogger(_LOGGER_NAME_PREFIX)
    return logging.getLogger(f"{_LOGGER_NAME_PREFIX}.{name}")
