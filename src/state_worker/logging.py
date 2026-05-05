"""Worker structured logging configuration (Phase 066).

Adds a per-worker-PID rotating file handler to the existing structlog
pipeline so every worker session writes to its own log file under
``.state/logs/worker-{session_id}.log`` with rotation, redaction,
and configurable output format.
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

import structlog

from state_core.observability import redact_processor

LOG = structlog.get_logger(__name__)

_WORKER_DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB
_WORKER_DEFAULT_BACKUP_COUNT = 5
_WORKER_DEFAULT_LOG_LEVEL = "INFO"

_LEVEL_MAP: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


def configure_worker_logging(
    session_id: str,
    project_root: str | Path | None = None,
    mode: str = "dev",
    log_level: str = _WORKER_DEFAULT_LOG_LEVEL,
    max_bytes: int = _WORKER_DEFAULT_MAX_BYTES,
    backup_count: int = _WORKER_DEFAULT_BACKUP_COUNT,
) -> str:
    """Add a rotating file handler for the worker session.

    Args:
        session_id: Worker session ID (used in log filename).
        project_root: Project root for log directory resolution.
        mode: Output mode — ``"dev"`` (ConsoleRenderer) or ``"json"`` (JSONRenderer).
        log_level: Python log level name (debug, info, warning, error).
        max_bytes: Max log file size in bytes before rotation.
        backup_count: Number of rotated backup files to keep.

    Returns:
        The absolute path to the log file.
    """
    if project_root is None:
        project_root = Path.cwd()
    elif isinstance(project_root, str):
        project_root = Path(project_root)

    log_dir = project_root / ".state" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    sanitized = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
    log_file = log_dir / f"worker-{sanitized}.log"

    numeric_level: int = _LEVEL_MAP.get(log_level.lower(), logging.INFO)

    if mode == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    file_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[redact_processor],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    root = logging.getLogger()
    handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(file_formatter)
    handler.setLevel(numeric_level)
    root.addHandler(handler)

    LOG.info(
        "worker.logging.configured",
        log_file=str(log_file),
        session_id=session_id,
        mode=mode,
        max_bytes=max_bytes,
        backup_count=backup_count,
        log_level=log_level,
    )

    return str(log_file)
