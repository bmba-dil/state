"""Mode-enforcement HTTP middleware for the state daemon.

Provides mode configuration loading (``ModeConfig``) and the
``ModeMiddleware`` callable that wraps the JSON-RPC router to
enforce ``X-State-Mode`` header validation — the 6th layer of
defense-in-depth for mode isolation.

Reads ``.state/mode.json`` from the project root; rejects
cross-mode write operations with HTTP 403 before they reach
any JSON-RPC handler.

Also provides ``validate_daemon_path()`` for filesystem-level subtree
enforcement — the 2nd of 6 mode-isolation defense layers.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Awaitable

import structlog
from pydantic import ValidationError
from src.state_core.schema import (
    ALL_RECOGNISED_MODES,
    BUILD_ONLY_EVENT_PREFIXES,
    ModeConfig,
    TEACH_ONLY_EVENT_PREFIXES,
    validate_subtree_path,
)

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Cached mode config — loaded once at daemon startup
# ---------------------------------------------------------------------------

_config: ModeConfig | None = None


def load_mode_config(root: str) -> ModeConfig:
    """Read ``.state/mode.json`` from *root*, validate with Pydantic, and cache.

    If the file is missing, creates a default ``{"mode": "both"}``
    config (permissive — both build and teach allowed).  This default
    is written to disk so subsequent reads are fast.

    Raises:
        ValueError: if the file exists but contains invalid JSON or
                    an unsupported mode value.
    """
    global _config

    mode_path = os.path.join(root, ".state", "mode.json")
    os.makedirs(os.path.dirname(mode_path), exist_ok=True)

    if not os.path.isfile(mode_path):
        default = ModeConfig(mode="both")
        # Atomically create with correct permissions (O_EXCL avoids TOCTOU race)
        try:
            fd = os.open(mode_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            # Race: another process created the file between isfile() and open().
            # Fall through to the normal read path below.
            pass
        else:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"mode": "both"}, f)
            _config = default
            log.info(
                "daemon.middleware.mode_config_created",
                mode="both",
                path=mode_path,
            )
            return default

    try:
        with open(mode_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {mode_path}: {e}") from e

    try:
        cfg = ModeConfig(**raw)
    except ValidationError as e:
        raise ValueError(f"Invalid mode config in {mode_path}: {e}") from e

    _config = cfg
    log.info("daemon.middleware.mode_config_loaded", mode=cfg.mode, path=mode_path)
    return cfg


def get_current_mode() -> str:
    """Return the active mode string.

    Returns ``"both"`` if ``load_mode_config()`` has not been called yet.
    """
    if _config is None:
        return "both"
    return _config.mode


# ---------------------------------------------------------------------------
# Mode validation helpers
# ---------------------------------------------------------------------------

# Re-exported from schema.py for backwards compatibility within this module.
_VALID_MODES = ALL_RECOGNISED_MODES

_READ_METHODS: frozenset[str] = frozenset({"GET", "HEAD"})

# POST paths that are read-only (no write side effects).
_READ_POST_PATHS: frozenset[str] = frozenset({"/health"})


def is_valid_mode(mode: str) -> bool:
    """Return ``True`` if *mode* is a recognised mode string.

    Valid modes: ``build``, ``teach``, ``both``, ``kernel``.
    """
    return mode in _VALID_MODES


def validate_daemon_path(path: str | Path) -> None:
    """Validate that *path* is within the daemon's active-mode subtree.

    Reads the active mode from the cached ``ModeConfig`` (loaded at daemon
    startup via ``load_mode_config()``).  Delegates to
    ``state_core.schema.validate_subtree_path()`` for the actual prefix check.

    Call this BEFORE any daemon write operation that touches a mode-specific
    file.  The call is a hard gate — if it raises ``ValueError``, the write
    MUST be aborted and the request rejected with a 403.

    Paths in the ``.state/`` root (``mode.json``, ``events.sqlite``, etc.)
    are always allowed — they are shared kernel files.

    Args:
        path: A filesystem path (string or ``pathlib.Path``).

    Raises:
        ValueError: If *path* crosses into the wrong subtree for the
                    currently active daemon mode.
                    Also raises if ``get_current_mode()`` returns an
                    unrecognised value (e.g., empty string or a stale
                    corrupted config).
    """
    active_mode = get_current_mode()
    validate_subtree_path(path, active_mode)


def _is_read_operation(method: str, path: str) -> bool:
    """Heuristic: determine if a request is read-only.

    GET and HEAD are always reads.
    POST to ``/health`` is considered a read.
    All other POST/PUT/PATCH/DELETE are writes.
    """
    if method in _READ_METHODS:
        return True
    if method == "POST" and path in _READ_POST_PATHS:
        return True
    return False


def _extract_event_type(body: bytes) -> str | None:
    """Extract the event type from a JSON-RPC ``state.emit`` request body.

    Parses the JSON body to find ``params.type`` when the method is
    ``"state.emit"``.  Returns ``None`` for any other method, malformed
    JSON, or missing type field — the caller decides how to handle.

    Args:
        body: Raw HTTP request body bytes.

    Returns:
        The event type string (e.g. ``"state.concept.introduced"``),
        or ``None`` if extraction is not applicable.
    """
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(payload, dict):
        return None

    if payload.get("method") != "state.emit":
        return None

    params = payload.get("params")
    if not isinstance(params, dict):
        return ""  # state.emit without proper params — treat as no event type

    return params.get("type") or ""  # None/null type → ""


# ---------------------------------------------------------------------------
# Router type (extended to support middleware status codes)
# ---------------------------------------------------------------------------

# The router receives (method, path, headers, body) and returns either
# plain bytes (for HTTP 200/204) or a (status_code, bytes) tuple so
# middleware can signal rejection status codes to the server.
Router = Callable[
    [str, str, dict[str, str], bytes],
    Awaitable[bytes | tuple[int, bytes]],
]


# ---------------------------------------------------------------------------
# Mode enforcement middleware
# ---------------------------------------------------------------------------


class ModeMiddleware:
    """Callable middleware that enforces ``X-State-Mode`` header validity.

    Wraps an inner router.  On mode mismatch for write operations,
    returns ``(403, body)`` — the server detects the tuple and uses
    the provided status code instead of the default 200.

    Rules (in order):
    1. Missing or invalid ``X-State-Mode`` → 400.
    2. Active mode is ``both`` → allow all.
    3. Request mode is ``kernel`` → allow all.
    4. Modes match → allow.
    5. Mismatch + read operation → allow.
    6. Mismatch + write operation → 403.
    """

    def __init__(self, router: Router, config: ModeConfig) -> None:
        self._router = router
        self._config = config

    async def __call__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
    ) -> bytes | tuple[int, bytes]:
        # --- Extract X-State-Mode header ---
        # Headers are lowercased by DaemonServer._handle_connection.
        request_mode = headers.get("x-state-mode", "").strip()
        active_mode = self._config.mode

        if not request_mode:
            return _reject(400, "missing_mode_header", request_mode="", active_mode=active_mode)

        if not is_valid_mode(request_mode):
            return _reject(400, "invalid_mode_header", request_mode=request_mode, active_mode=active_mode)

        # --- Mode decision tree ---
        # "both" allows everything
        if active_mode == "both":
            return await self._router(method, path, headers, body)

        # kernel always allowed
        if request_mode == "kernel":
            return await self._router(method, path, headers, body)

        # Same mode — allow
        if request_mode == active_mode:
            return await self._router(method, path, headers, body)

        # Mismatch — read operations still allowed
        if _is_read_operation(method, path):
            return await self._router(method, path, headers, body)

        # Mismatch + write — reject
        return _reject(403, "cross_mode_rejected", request_mode=request_mode, active_mode=active_mode)

    def validate_path(self, path: str | Path) -> None:
        """Validate a filesystem path against this middleware's mode config.

        Convenience method for JSON-RPC handlers to call before performing
        file writes.  Delegates to ``validate_subtree_path()`` using the
        same ``ModeConfig`` instance the middleware was constructed with.

        Raises:
            ValueError: If *path* crosses into the wrong subtree.
        """
        validate_subtree_path(path, self._config.mode)


# ---------------------------------------------------------------------------
# Rejection helpers
# ---------------------------------------------------------------------------


def _reject(
    status: int,
    error: str,
    request_mode: str = "",
    active_mode: str = "",
) -> tuple[int, bytes]:
    """Build a mode-enforcement rejection response.

    Returns a ``(status_code, body_bytes)`` tuple that the server
    detects and translates to the correct HTTP status line.
    """
    payload = {
        "error": error,
        "request_mode": request_mode,
        "active_mode": active_mode,
    }
    return (status, json.dumps(payload).encode())
