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


# ---------------------------------------------------------------------------
# Task 051.2 — Stale process detection
# ---------------------------------------------------------------------------


def is_pid_alive(pid: int, expected_start_time_ns: int) -> bool:
    """Check whether *pid* refers to a live process whose start time matches
    *expected_start_time_ns*.

    Returns ``False`` when:
    - The process does not exist (no such pid).
    - The process exists but its start time differs from *expected_start_time_ns*
      (the pid was recycled — stale).
    - The platform does not support start-time comparison and process existence
      cannot be verified.

    Platform behaviour
    ------------------
    **Linux:** reads ``/proc/<pid>/stat`` field 22 (starttime in clock ticks
    since boot) and converts to nanoseconds for comparison.

    **macOS:** runs ``ps -p <pid> -o lstart=`` to obtain the process start
    time as a wall-clock string, converts it to an approximate monotonic
    nanosecond offset using ``time.time() - time.monotonic()`` as the boot
    epoch, then compares with *expected_start_time_ns*.

    **Other platforms:** falls back to ``os.kill(pid, 0)`` — process
    existence check only (no start-time match).
    """
    if sys.platform == "linux":
        return _is_pid_alive_linux(pid, expected_start_time_ns)
    elif sys.platform == "darwin":
        return _is_pid_alive_darwin(pid, expected_start_time_ns)
    else:
        return _is_pid_alive_fallback(pid)


def _is_pid_alive_linux(pid: int, expected_start_time_ns: int) -> bool:
    """Check pid via /proc/<pid>/stat."""
    try:
        with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as f:
            stat = f.read()
    except (FileNotFoundError, PermissionError):
        return False  # process gone

    # /proc/pid/stat format: pid (comm) state ppid ... starttime (field 22 after
    # the closing paren).  The comm field may contain spaces and parentheses.
    end_paren = stat.rfind(")")
    if end_paren == -1:
        return False  # malformed

    fields = stat[end_paren + 2:].split()
    if len(fields) < 20:
        return False  # not enough fields to reach starttime (field 22 → index 19)

    try:
        starttime_ticks = int(fields[19])  # 0-based after pid + comm + state
    except (ValueError, IndexError):
        return False

    ticks_per_sec = os.sysconf("SC_CLK_TCK")
    if ticks_per_sec <= 0:
        ticks_per_sec = 100  # safe fallback

    running_start_ns = int(starttime_ticks * 1_000_000_000 / ticks_per_sec)

    # Allow a small window of tolerance for clock granularity.
    tolerance_ns = 5_000_000_000  # 5 seconds
    return abs(running_start_ns - expected_start_time_ns) <= tolerance_ns


def _is_pid_alive_darwin(pid: int, expected_start_time_ns: int) -> bool:
    """Check pid via ``ps -p <pid> -o lstart=``."""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "lstart="],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False

    if result.returncode != 0 or not result.stdout.strip():
        return False

    lstart = result.stdout.strip()
    try:
        # lstart format example: "Sun May  4 12:00:00 2026"
        proc_start_epoch = _parse_lstart(lstart)
    except ValueError:
        log.warning("daemon.pid.parse_lstart_failed", pid=pid, lstart=lstart)
        return False

    # Approximate boot time: time.time() is wall clock, time.monotonic()
    # is time since boot on Darwin (mach_absolute_time).
    boot_epoch = time.time() - time.monotonic()
    running_start_ns = int((proc_start_epoch - boot_epoch) * 1_000_000_000)

    tolerance_ns = 5_000_000_000  # 5 seconds
    return abs(running_start_ns - expected_start_time_ns) <= tolerance_ns


def _parse_lstart(lstart: str) -> float:
    """Parse a ``ps -o lstart=`` date string (BSD format) to epoch seconds.

    Example input: ``"Sun May  4 12:00:00 2026"``
    """
    import calendar as _cal
    from datetime import datetime as _dt

    # Map abbreviated month names to numbers.
    _MONTH_MAP: dict[str, int] = {
        name[:3].lower(): num
        for num, name in enumerate(_cal.month_name)
        if num > 0
    }

    parts = lstart.split()
    if len(parts) < 5:
        raise ValueError(f"unexpected lstart format: {lstart!r}")

    # BSD lstart: "Day Mon DD HH:MM:SS YYYY"
    month_str = parts[1].lower() if len(parts) >= 2 else ""
    month = _MONTH_MAP.get(month_str, 0)
    if month == 0:
        raise ValueError(f"unknown month in lstart: {lstart!r}")

    day = int(parts[2]) if len(parts) >= 3 else 0
    time_str = parts[3] if len(parts) >= 4 else "00:00:00"
    year = int(parts[4]) if len(parts) >= 5 else 1970

    hour, minute, second = (int(x) for x in time_str.split(":"))

    dt = _dt(year, month, day, hour, minute, second)
    return dt.timestamp()


def _is_pid_alive_fallback(pid: int) -> bool:
    """Fallback: check process existence via ``os.kill(pid, 0)``."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
