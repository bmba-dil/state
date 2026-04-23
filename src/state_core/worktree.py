"""Worktree abstraction: opencode-preferred, pygit2 fallback."""

from __future__ import annotations

from typing import Protocol


class WorktreeService(Protocol):
    """Create/list/remove worktrees, preferring opencode HTTP API."""

    async def create(self, name: str, branch: str) -> str: ...
    async def remove(self, name: str) -> None: ...
