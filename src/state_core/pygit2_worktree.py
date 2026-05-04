"""Pygit2 fallback worktree adapter.

Implements the WorktreeService Protocol (Phase 032) via pygit2.
Used when opencode is unavailable (non-opencode hosts). This is the
secondary worktree path per WRK-02.

Lifecycle:
  1. Daemon detects opencode-unreachable and switches to this adapter.
  2. Adapter opens the local git repository via pygit2.
  3. Worktree directories are created alongside the main repo in
     ``<repo_root>/.git/worktrees/``.

Branch naming per WRK-05: ``slice/<arc>/<phase>/<slice-id>``.

API surface:
  Pygit2WorktreeService(repo_path)      — open repo at path
  await service.create(name, branch)    → WorktreeInfo
  await service.list()                  → list[WorktreeInfo]
  await service.remove(name)            → None
  await service.reset(name)             → None
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pygit2
import structlog

from state_core.worktree import WorktreeInfo

log = structlog.get_logger(__name__)

GIT_CHECKOUT_FORCE = 2
GIT_CHECKOUT_REMOVE_UNTRACKED = 32
CHECKOUT_RESET_STRATEGY = GIT_CHECKOUT_FORCE | GIT_CHECKOUT_REMOVE_UNTRACKED


class Pygit2WorktreeService:
    """Pygit2-based implementation of the WorktreeService Protocol."""

    def __init__(self, repo_path: str | Path) -> None:
        self._repo_path = Path(repo_path).resolve()
        if not (self._repo_path / ".git").is_dir():
            self._repo = pygit2.Repository(str(self._repo_path))
        else:
            self._repo = pygit2.Repository(str(self._repo_path))

    def _get_repo(self) -> pygit2.Repository:
        return self._repo

    async def create(self, name: str, branch: str) -> WorktreeInfo:
        repo = self._get_repo()

        existing = repo.lookup_branch(branch)
        if existing is not None:
            log.debug("branch already exists, using existing", branch=branch,
                      target=str(existing.target))
            branch_ref = existing
        else:
            head_commit = repo[repo.head.target]
            branch_ref = repo.create_branch(branch, head_commit)
            log.debug("created branch", branch=branch,
                      target=str(repo.head.target))

        worktree_dir = self._repo_path.parent / "state-worktrees" / name
        worktree_dir.parent.mkdir(parents=True, exist_ok=True)

        # pygit2 creates .git/worktrees/<name> internally — ensure parent exists
        git_worktree_dir = self._repo_path / ".git" / "worktrees" / name
        git_worktree_dir.parent.mkdir(parents=True, exist_ok=True)

        try:
            existing_wt = repo.lookup_worktree(name)
            if existing_wt is not None:
                log.debug("worktree already exists", name=name,
                          path=existing_wt.path)
                return WorktreeInfo(
                    name=name,
                    path=existing_wt.path,
                    branch=branch,
                    locked=existing_wt.is_prunable is False,
                    prunable=existing_wt.is_prunable,
                )
        except KeyError:
            pass

        wt = repo.add_worktree(name, str(worktree_dir), branch_ref)

        return WorktreeInfo(
            name=name,
            path=wt.path,
            branch=branch,
            locked=False,
            prunable=wt.is_prunable,
        )

    async def list(self) -> list[WorktreeInfo]:
        repo = self._get_repo()
        result: list[WorktreeInfo] = []

        for wt_name in repo.list_worktrees():
            try:
                wt = repo.lookup_worktree(wt_name)
                result.append(WorktreeInfo(
                    name=wt.name,
                    path=wt.path,
                    branch=wt_name,
                    locked=False,
                    prunable=wt.is_prunable,
                ))
            except KeyError:
                log.debug("worktree removed during list", name=wt_name)

        return result

    async def remove(self, name: str) -> None:
        repo = self._get_repo()
        try:
            wt = repo.lookup_worktree(name)
            if wt.is_prunable:
                wt.prune()
            else:
                worktree_dir = Path(wt.path)
                if worktree_dir.exists():
                    shutil.rmtree(str(worktree_dir), ignore_errors=True)
                wt.prune()
            log.debug("removed worktree", name=name)
        except KeyError:
            log.debug("worktree not found, nothing to remove", name=name)

    async def reset(self, name: str) -> None:
        repo = self._get_repo()
        try:
            wt = repo.lookup_worktree(name)
        except KeyError:
            log.debug("worktree not found, nothing to reset", name=name)
            return

        wt_repo = pygit2.Repository(wt.path)
        target_oid = wt_repo.head.target

        wt_repo.reset(target_oid, pygit2.enums.ResetMode.HARD)
        wt_repo.checkout_head(strategy=CHECKOUT_RESET_STRATEGY)
        wt_repo.state_cleanup()

        log.debug("reset worktree", name=name, oid=str(target_oid))
