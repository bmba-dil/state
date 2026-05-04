"""Tests for state_core.worktree_gc — orphan worktree GC."""

from __future__ import annotations

import pytest

from state_core.worktree import WorktreeInfo
from state_core.worktree_gc import WorktreeGC


class _MockService:
    def __init__(self, worktrees: list[WorktreeInfo]) -> None:
        self._worktrees = worktrees
        self.removed: list[str] = []

    async def create(self, name: str, branch: str) -> WorktreeInfo:
        raise NotImplementedError

    async def list(self) -> list[WorktreeInfo]:
        return list(self._worktrees)

    async def remove(self, name: str) -> None:
        self.removed.append(name)

    async def reset(self, name: str) -> None:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_collect_finds_prunable() -> None:
    wt = [
        WorktreeInfo(name="a", path="/tmp/a", branch="a", prunable=True),
        WorktreeInfo(name="b", path="/tmp/b", branch="b", prunable=False),
        WorktreeInfo(name="c", path="/tmp/c", branch="c", prunable=True),
    ]
    service = _MockService(wt)
    gc = WorktreeGC()

    result = await gc.collect(service)
    names = {r.name for r in result}
    assert names == {"a", "c"}


@pytest.mark.asyncio
async def test_collect_empty() -> None:
    service = _MockService([])
    gc = WorktreeGC()
    result = await gc.collect(service)
    assert result == []


@pytest.mark.asyncio
async def test_prune_removes_orphans() -> None:
    wt = [
        WorktreeInfo(name="x", path="/tmp/x", branch="x", prunable=True),
    ]
    service = _MockService(wt)
    gc = WorktreeGC()

    result = await gc.prune(service)
    assert len(result) == 1
    assert result[0].name == "x"
    assert service.removed == ["x"]


@pytest.mark.asyncio
async def test_prune_dry_run_no_removal() -> None:
    wt = [
        WorktreeInfo(name="y", path="/tmp/y", branch="y", prunable=True),
    ]
    service = _MockService(wt)
    gc = WorktreeGC()

    result = await gc.prune(service, dry_run=True)
    assert len(result) == 1
    assert service.removed == []
