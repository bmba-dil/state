"""Daemon structured logging configuration.

Configures structlog + RotatingFileHandler for daemon log output with:
- Token redaction (via state_core.observability.redact_processor, Phase 020)
- Configurable output mode: JSON (production) or dev (human-readable)
- Size-based log rotation with configurable retention
- Log level configurable via .state/config.toml [daemon.logging]

Must be called AFTER ``observability.install()`` — the redact_processor is
expected to already be at position 0 of the structlog chain.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import tomllib
from pathlib import Path
from typing import Any

import structlog

from state_core.observability import redact_processor

LOG = structlog.get_logger(__name__)

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_BACKUP_COUNT = 5
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MODE = "dev"

_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def _load_logging_config(project_root: Path) -> dict[str, Any]:
    """Load daemon logging config from .state/config.toml [daemon.logging].

    Falls back to defaults if the config file is missing or the section
    is absent. Silently swallows parse errors — the log file isn't set
    up yet so we cannot log the failure; the caller uses the defaults.
    """
    config_path = project_root / ".state" / "config.toml"
    defaults: dict[str, Any] = {
        "level": DEFAULT_LOG_LEVEL,
        "max_bytes": DEFAULT_MAX_BYTES,
        "backup_count": DEFAULT_BACKUP_COUNT,
        "mode": DEFAULT_MODE,
    }
    if not config_path.is_file():
        return defaults
    try:
        raw = config_path.read_text(encoding="utf-8")
        data = tomllib.loads(raw)
        section = data.get("daemon", {}).get("logging", {})
        for key in defaults:
            if key in section:
                defaults[key] = section[key]
    except (tomllib.TOMLDecodeError, OSError, ValueError):
        pass
    return defaults


def configure_daemon_logging(
    log_dir: str | None = None,
    mode: str | None = None,
    max_bytes: int | None = None,
    backup_count: int | None = None,
    log_level: str | None = None,
    project_root: str | Path | None = None,
) -> None:
    """Configure daemon structured logging with rotation, redaction, and mode selection.

    Attaches a ``RotatingFileHandler`` to the stdlib root logger so every
    log record — from structlog-native loggers AND third-party stdlib loggers
    (httpx, litellm, pygit2, aiosqlite) — flows through the redactor and
    lands in ``.state/logs/daemon.log``.

    The handler is ADDED to any existing handlers (e.g. the StreamHandler
    installed by ``observability.install()``).  The existing StreamHandler
    continues to emit to stderr; this handler writes exclusively to the
    daemon log file.

    Args:
        log_dir: Directory for log files.  Defaults to ``.state/logs/``
            relative to *project_root*.
        mode: Output mode — ``"dev"`` (ConsoleRenderer) or ``"json"``
            (JSONRenderer).  Overrides the config-file value.
        max_bytes: Max log file size in bytes before rotation.  Overrides
            the config-file value.
        backup_count: Number of rotated backup files to keep.  Overrides
            the config-file value.
        log_level: Python log level name (``"debug"``, ``"info"``,
            ``"warning"``, ``"error"``).  Overrides the config-file value.
        project_root: Project root directory for config-file discovery
            and relative log-dir resolution.  Defaults to ``Path.cwd()``.
    """
    if project_root is None:
        project_root = Path.cwd()
    elif isinstance(project_root, str):
        project_root = Path(project_root)

    # Load config from .state/config.toml with fallback defaults.
    cfg = _load_logging_config(project_root)

    resolved_mode: str = mode or cfg["mode"]  # type: ignore[assignment]
    resolved_max_bytes: int = max_bytes if max_bytes is not None else cfg["max_bytes"]  # type: ignore[assignment]
    resolved_backup_count: int = (
        backup_count if backup_count is not None else cfg["backup_count"]  # type: ignore[assignment]
    )
    resolved_level_name: str = log_level or cfg["level"]  # type: ignore[assignment]
    numeric_level: int = _LEVEL_MAP.get(resolved_level_name.lower(), logging.INFO)

    if log_dir is not None:
        log_dir_path = Path(log_dir)
    else:
        log_dir_path = project_root / ".state" / "logs"

    # Ensure log directory exists.
    log_dir_path.mkdir(parents=True, exist_ok=True)
    log_file = log_dir_path / "daemon.log"

    # Select renderer.
    if resolved_mode == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    # Build the ProcessorFormatter for the file handler.
    # foreign_pre_chain: processors applied BEFORE the renderer.
    # We use redact_processor as the sole foreign_pre_chain processor —
    # the global structlog.configure() from install() already handles the
    # full chain for structlog-native loggers.  This formatter ensures
    # stdlib records (httpx, litellm, pygit2, aiosqlite) are also redacted
    # in the file output.
    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[redact_processor],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Attach RotatingFileHandler to the root logger.
    root = logging.getLogger()
    handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=resolved_max_bytes,
        backupCount=resolved_backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(file_formatter)
    handler.setLevel(numeric_level)
    root.addHandler(handler)

    LOG.info(
        "daemon.logging.configured",
        log_file=str(log_file),
        mode=resolved_mode,
        max_bytes=resolved_max_bytes,
        backup_count=resolved_backup_count,
        log_level=resolved_level_name,
    )
