"""Unix socket path resolution — deterministic, platform-aware socket paths.

Resolves a unix domain socket path from the project root via SHA-256
hash, preferring ``$XDG_RUNTIME_DIR`` on Linux with a macOS ``$TMPDIR``
or ``/tmp`` fallback.  Also provides atomic socket-path storage to
``.state/daemon.sock`` for worker/client discovery.
"""

from __future__ import annotations

import hashlib
import os
import tempfile


# ---------------------------------------------------------------------------
# Task 052.1 — Deterministic socket path resolution
# ---------------------------------------------------------------------------


def resolve_socket_path(project_root: str) -> str:
    """Return a deterministic, platform-aware unix socket path.

    The socket name is derived from the SHA-256 hash of the project root's
    absolute path, truncated to 16 hex characters::

        state-<hash16>.sock

    This guarantees the same socket name across restarts but uniqueness
    across distinct project checkouts.

    **Platform behaviour:**

    * **Linux:** prefers ``$XDG_RUNTIME_DIR``.
    * **macOS:** prefers ``$TMPDIR``, falls back to ``/tmp``.

    The parent directory is created if it does not already exist.
    """
    # Normalise and hash the project root.
    abs_root = os.path.abspath(project_root)
    hash16 = hashlib.sha256(abs_root.encode()).hexdigest()[:16]
    socket_name = f"state-{hash16}.sock"

    # Resolve the runtime directory.
    runtime_dir = _runtime_dir()
    os.makedirs(runtime_dir, exist_ok=True)

    return os.path.join(runtime_dir, socket_name)


def _runtime_dir() -> str:
    """Return the preferred runtime directory for unix sockets."""
    # Linux: XDG_RUNTIME_DIR is the standard per-user runtime dir.
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg:
        return xdg

    # macOS / other BSD: TMPDIR or fallback to /tmp.
    return os.environ.get("TMPDIR", "/tmp")


# ---------------------------------------------------------------------------
# Task 052.2 — Atomic socket-path storage for worker discovery
# ---------------------------------------------------------------------------

_SOCKET_MARKER_PATH = ".state/daemon.sock"


def write_socket_path(socket_path: str) -> None:
    """Atomically write *socket_path* to ``.state/daemon.sock``.

    Uses temp + rename to guarantee readers never see a partially-written
    file.  This marker enables workers (Phase 061) and CLI clients to
    discover the daemon socket without hard-coding paths.
    """
    dirname = os.path.dirname(_SOCKET_MARKER_PATH) or "."
    os.makedirs(dirname, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        dir=dirname, prefix=".daemon_sock_", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(socket_path)
        os.replace(tmp_path, _SOCKET_MARKER_PATH)  # atomic on POSIX
    except Exception:
        # Best-effort cleanup — don't leave a temp file.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def read_socket_path() -> str | None:
    """Read the daemon socket path from ``.state/daemon.sock``.

    Returns ``None`` when the marker file does not exist, is empty, or is
    unreadable.
    """
    if not os.path.isfile(_SOCKET_MARKER_PATH):
        return None

    try:
        with open(_SOCKET_MARKER_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except OSError:
        return None

    if not content:
        return None

    return content
