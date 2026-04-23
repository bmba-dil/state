"""Opencode config file discovery and URL resolution.

Searches up from CWD for opencode.json or .opencode/opencode.json
and reads server.port / server.hostname to construct the API base URL.
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

DEFAULT_OPENCODE_PORT = 17495
DEFAULT_OPENCODE_HOST = "127.0.0.1"


def find_opencode_config(start_dir: Path | None = None) -> Path | None:
    """Walk up from *start_dir* looking for opencode.json or .opencode/opencode.json.

    Checks each directory for:
      1. ``<dir>/opencode.json``
      2. ``<dir>/.opencode/opencode.json``

    Returns the first matching path, or *None* if nothing is found
    (including when the search reaches the filesystem root).
    """
    if start_dir is None:
        start_dir = Path.cwd()
    current = start_dir.resolve()
    while True:
        for candidate in (current / "opencode.json",
                          current / ".opencode" / "opencode.json"):
            if candidate.is_file():
                return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def resolve_opencode_url(start_dir: Path | None = None) -> str:
    """Resolve the opencode HTTP base URL from config, with fallback defaults.

    Priority:
      1. ``STATE_OPENCODE_URL`` environment variable (bypass config search)
      2. ``opencode.json`` / ``.opencode/opencode.json`` found by walking up
      3. ``http://127.0.0.1:17495`` (opencode default)

    Returns:
        A URL string like ``http://127.0.0.1:17495`` (no trailing slash).
    """
    import os
    env_url = os.environ.get("STATE_OPENCODE_URL")
    if env_url:
        return env_url.rstrip("/")

    config_path = find_opencode_config(start_dir)
    if config_path is not None:
        try:
            raw = config_path.read_text(encoding="utf-8")
            cfg = json.loads(raw)
            server = cfg.get("server", {}) or {}
            port = int(server.get("port", DEFAULT_OPENCODE_PORT))
            host = str(server.get("hostname", DEFAULT_OPENCODE_HOST))
            if port <= 0 or port > 65535:
                port = DEFAULT_OPENCODE_PORT
            url = f"http://{host}:{port}"
            log.debug("resolved opencode URL from config", url=url, config=str(config_path))
            return url
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            log.warning("failed to parse opencode config, using defaults",
                        config=str(config_path), error=str(exc))

    log.debug("using default opencode URL", url=f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}")
    return f"http://{DEFAULT_OPENCODE_HOST}:{DEFAULT_OPENCODE_PORT}"
