"""Transactional worktree bootstrap per WRK-03.

Atomic three-step process for creating a Slice-scoped worktree:
  1. Compute deterministic branch/name (worktree_naming)
  2. Create worktree via WorktreeService
  3. Link .state/ directory from parent repo

If any step fails, compensation rollback removes partial state.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import structlog

from state_core.worktree import WorktreeInfo, WorktreeService
from state_core.worktree_naming import format_branch, format_worktree_name

log = structlog.get_logger(__name__)

STATE_DIR = ".state"


class WorktreeBootstrapper:
    """Transactional worktree creation with compensation rollback."""

    def __init__(self, service: WorktreeService, parent_repo_path: str | Path) -> None:
        self._service = service
        self._parent_path = Path(parent_repo_path).resolve()

    async def bootstrap(
        self,
        arc_id: str,
        phase_id: str,
        slice_id: str,
    ) -> WorktreeInfo:
        """Bootstrap a worktree for the given Slice.

        Steps:
          1. Compute deterministic branch/name.
          2. Create worktree.
          3. Link .state/ from parent.

        On failure at any step, compensation cleans up partial state
        so the system is left in its pre-bootstrap state.

        Returns:
            WorktreeInfo for the created worktree.
        """
        branch = format_branch(arc_id, phase_id, slice_id)
        name = format_worktree_name(arc_id, phase_id, slice_id)

        parent_state = self._parent_path / STATE_DIR

        worktree_created = False
        try:
            info = await self._service.create(name=name, branch=branch)
            worktree_created = True
            log.debug("bootstrapper: worktree created", name=name, path=info.path)

            worktree_path = Path(info.path)
            target_state = worktree_path / STATE_DIR

            if parent_state.is_dir():
                if target_state.exists():
                    shutil.rmtree(str(target_state), ignore_errors=True)
                shutil.copytree(str(parent_state), str(target_state))
                log.debug("bootstrapper: .state/ linked", from_=str(parent_state),
                          to=str(target_state))
            else:
                target_state.mkdir(parents=True, exist_ok=True)
                log.debug("bootstrapper: .state/ created empty", path=str(target_state))

            return info

        except Exception:
            if worktree_created:
                log.warning("bootstrapper: rolling back worktree", name=name)
                try:
                    await self._service.remove(name)
                except Exception as remove_err:
                    log.error("bootstrapper: rollback remove failed", name=name,
                              error=str(remove_err))
            raise
