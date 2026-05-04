"""Worktree abstraction: host-agnostic Protocol contract.

This module defines the WorktreeService Protocol and its return types.
Implementations live in separate modules:

  * Phase 033 — opencode-HTTP adapter (preferred path)
  * Phase 034 — pygit2 fallback (opencode unavailable)

The Protocol is host-agnostic — no imports from opencode, pygit2,
httpx, or any transport-specific package. Adapters satisfy the Protocol
structurally (no inheritance needed).

Cardinal rules:
  1. Mode isolation — no build/teach imports (BASE-08).
  2. Determinism — no datetime.now() in models or signatures.
  3. Extra forbid — all pydantic models reject unknown keys.
  4. Frozen — all pydantic models are immutable.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class WorktreeInfo(BaseModel):
    """Metadata for a single worktree."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    """Unique worktree name (e.g. 'slice/arc-1/phase-2/slice-3' per WRK-05)."""

    path: str
    """Absolute filesystem path to the worktree directory."""

    branch: str
    """Git branch name associated with this worktree."""

    locked: bool = False
    """Whether the worktree is currently locked (open session or git operation)."""

    prunable: bool = False
    """Whether the worktree can be safely pruned (orphaned or stale per WRK-04)."""


@runtime_checkable
class WorktreeService(Protocol):
    """Host-agnostic worktree management contract.

    Implementations: opencode-HTTP adapter (Phase 033), pygit2 fallback (Phase 034).
    """

    async def create(self, name: str, branch: str) -> WorktreeInfo:
        """Create a new worktree for the given branch.

        Returns a WorktreeInfo with the resulting filesystem path.
        Must raise on collision (duplicate name).
        """
        ...

    async def list(self) -> list[WorktreeInfo]:
        """List all active worktrees with metadata.

        Includes locked, prunable, and healthy worktrees.
        """
        ...

    async def remove(self, name: str) -> None:
        """Remove (prune) a worktree by name.

        Idempotent — no-op if the worktree does not exist.
        Per WRK-04, orphan pruning is a daemon concern; this method
        removes a specific named worktree.
        """
        ...

    async def reset(self, name: str) -> None:
        """Reset worktree to a clean state.

        Discards uncommitted changes. Used before reassigning a
        worktree to a new Slice or Step.
        """
        ...
