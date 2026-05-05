"""PID file management — atomic write with {pid, start_time_ns} and platform-aware stale detection.

Defense against P0-15: stale pid file preventing daemon restart.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Any

import structlog

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Task 051.1 — Atomic write / read
# ---------------------------------------------------------------------------


def write_pid_file(path: str) -> None:
    """Write the PID file atomically using temp + rename.

    The file contains a JSON object: ``{"pid": <int>, "start_time_ns": <int>}``
    where ``start_time_ns`` is ``time.monotonic_ns()`` captured at daemon start.

    Atomicity guarantees that readers never see a partially-written file.
    """
    payload: dict[str, int] = {
        "pid": os.getpid(),
        "start_time_ns": time.monotonic_ns(),
    }

    dirname = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dirname, prefix=".daemon_pid_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp_path, path)  # atomic on POSIX
    except Exception:
        # Best-effort cleanup — don't leave a temp file lying around.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_pid_file(path: str) -> dict[str, int] | None:
    """Read and validate the PID file.  Returns ``None`` when the file is
    missing, malformed, or does not contain the expected keys.
    """
    if not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data: Any = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning(
            "daemon.pid.read_failed",
            path=path,
            error_type=type(exc).__name__,
        )
        return None

    if not isinstance(data, dict):
        log.warning("daemon.pid.invalid_type", path=path, got=type(data).__name__)
        return None

    pid = data.get("pid")
    start_time_ns = data.get("start_time_ns")
    if not isinstance(pid, int) or not isinstance(start_time_ns, int):
        log.warning("daemon.pid.missing_fields", path=path)
        return None

    return {"pid": pid, "start_time_ns": start_time_ns}
