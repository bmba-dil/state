"""Version negotiation for worker-daemon handshake.

Defines the protocol version, compat range, and the version validation
used by the daemon to accept or reject worker connections (WRK-13).
"""

from __future__ import annotations

PLUGIN_VERSION = "0.1.0"
COMPAT_MAJOR_MINOR = "0.1"
HEADER_NAME = "x-state-plugin-version"


def check_version_compat(version_header: str | None) -> tuple[bool, str]:
    """Validate a worker's ``X-State-Plugin-Version`` header value.

    Returns:
        A ``(ok, message)`` tuple.  *ok* is ``True`` when the
        version is compatible (starts with *COMPAT_MAJOR_MINOR*);
        *message* describes the reason when not ok.
    """
    if not version_header:
        return (False, "missing X-State-Plugin-Version header")
    if version_header.startswith(COMPAT_MAJOR_MINOR):
        return (True, "ok")
    return (
        False,
        f"incompatible plugin version {version_header!r} "
        f"(daemon expects {COMPAT_MAJOR_MINOR}.x)",
    )
