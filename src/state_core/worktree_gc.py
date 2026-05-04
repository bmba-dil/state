"""Orphan worktree garbage collector (WRK-04, P0-10).

Nightly daemon task that scans worktrees for orphans — stale branches,
missing directories, lingering lock files — and prunes them safely.

P0-10: Errors are NEVER silently swallowed. Every prunable worktree is
logged individually, and any failure during pruning is raised.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from state_core.worktree import WorktreeInfo, WorktreeService

log = structlog.get_logger(__name__)


class WorktreeGC:
    """Identify and prune orphaned worktrees."""

    async def collect(self, service: WorktreeService) -> list[WorktreeInfo]:
        """Collect all worktrees currently marked as prunable."""
        all_wt = await service.list()
        return [wt for wt in all_wt if wt.prunable]

    async def prune(
        self,
        service: WorktreeService,
        dry_run: bool = False,
    ) -> list[WorktreeInfo]:
        """Prune orphaned worktrees.

        Args:
            service: The WorktreeService to query and remove through.
            dry_run: If True, report what would be pruned without removing.

        Returns:
            List of worktrees that are (or would be) pruned.

        Raises:
            RuntimeError: If pruning a collected worktree fails.
        """
        orphans = await self.collect(service)

        for wt in orphans:
            if dry_run:
                log.info("gc: would prune orphan worktree",
                         name=wt.name, path=wt.path)
            else:
                log.info("gc: pruning orphan worktree",
                         name=wt.name, path=wt.path)
                await service.remove(wt.name)

        return orphans
