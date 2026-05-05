"""Worker session identity — resolves session ID and project context.

Provides the canonical session identity model consumed by every
other worker subsystem (bridge, hooks, state container, teardown).
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class SessionIdentity(BaseModel):
    """Canonical session identity for a worker process.

    Immutable after construction.  Carried through all worker
    subsystems so they agree on who this worker represents.
    """

    session_id: str = Field(..., min_length=1)
    project_root: str = Field(...)
    pid: int = Field(ge=0)


def resolve_session_id(session_id: str | None = None) -> SessionIdentity:
    """Resolve a :class:`SessionIdentity` for the current process.

    Priority:
        1. Explicit *session_id* argument (CLI flag)
        2. ``STATE_SESSION_ID`` environment variable
        3. Auto-generated ``STATE-{pid}``

    *project_root* is always ``Path.cwd().resolve()``.
    *pid* is always ``os.getpid()``.
    """
    pid = os.getpid()

    if session_id is not None:
        resolved = session_id.strip()
        if not resolved:
            raise ValueError("session_id must be non-empty")
    else:
        resolved = os.environ.get("STATE_SESSION_ID")
        if resolved is not None:
            resolved = resolved.strip()
            if not resolved:
                resolved = f"STATE-{pid}"
        else:
            resolved = f"STATE-{pid}"

    project_root = str(Path.cwd().resolve())

    return SessionIdentity(
        session_id=resolved,
        project_root=project_root,
        pid=pid,
    )
