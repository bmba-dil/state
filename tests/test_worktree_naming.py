"""Tests for state_core.worktree_naming — deterministic branch/name generation."""

from __future__ import annotations

import pytest

from state_core.worktree import WorktreeInfo
from state_core.worktree_naming import (
    format_branch,
    format_worktree_name,
    find_collision,
)


def test_format_branch_basic() -> None:
    """format_branch produces expected output for clean IDs."""
    result = format_branch("arc-1", "phase-2", "slice-3")
    assert result == "slice/arc-1/phase-2/slice-3"


def test_format_branch_deterministic() -> None:
    """Same inputs always produce same output."""
    a = format_branch("a1", "p2", "s3")
    b = format_branch("a1", "p2", "s3")
    assert a == b


def test_format_branch_sanitizes_spaces() -> None:
    """Spaces replaced with dashes."""
    result = format_branch("Arc One", "Phase Two", "Slice Three")
    assert result == "slice/arc-one/phase-two/slice-three"


def test_format_branch_sanitizes_uppercase() -> None:
    """Uppercase converted to lowercase."""
    result = format_branch("ARC-1", "PHASE-2", "SLICE-3")
    assert result == "slice/arc-1/phase-2/slice-3"


def test_format_branch_sanitizes_special_chars() -> None:
    """Special characters replaced with dashes."""
    result = format_branch("arc@1", "phase#2", "slice$3")
    assert result == "slice/arc-1/phase-2/slice-3"


def test_format_branch_collapses_multiple_dashes() -> None:
    """Multiple consecutive dashes collapsed to single dash."""
    result = format_branch("arc--1", "phase__2", "slice..3")
    assert result == "slice/arc-1/phase-2/slice-3"


def test_format_branch_strips_leading_trailing_dashes() -> None:
    """Leading/trailing dashes removed from each component."""
    result = format_branch("-arc-1-", "-phase-2-", "-slice-3-")
    assert result == "slice/arc-1/phase-2/slice-3"


def test_format_branch_empty_ids() -> None:
    """Empty IDs produce minimal valid names (just 'slice')."""
    result = format_branch("", "", "")
    assert result == "slice///"


def test_format_worktree_name_equals_format_branch() -> None:
    """Worktree names equal branch names by convention."""
    branch = format_branch("a", "p", "s")
    name = format_worktree_name("a", "p", "s")
    assert name == branch


class _MockWorktreeService:
    def __init__(self, names: list[str] | None = None) -> None:
        self._names = names or []

    async def create(self, name: str, branch: str) -> WorktreeInfo:
        raise NotImplementedError

    async def list(self) -> list[WorktreeInfo]:
        return [WorktreeInfo(name=n, path=f"/tmp/{n}", branch=n) for n in self._names]

    async def remove(self, name: str) -> None:
        raise NotImplementedError

    async def reset(self, name: str) -> None:
        raise NotImplementedError


@pytest.mark.asyncio
async def test_find_collision_true() -> None:
    """Collision detected when worktree name already exists."""
    service = _MockWorktreeService(names=["slice/a/p/s"])
    result = await find_collision(service, "a", "p", "s")
    assert result is True


@pytest.mark.asyncio
async def test_find_collision_false() -> None:
    """No collision when worktree name does not exist."""
    service = _MockWorktreeService(names=["slice/x/y/z"])
    result = await find_collision(service, "a", "p", "s")
    assert result is False


@pytest.mark.asyncio
async def test_find_collision_empty_list() -> None:
    """No collision when no worktrees exist."""
    service = _MockWorktreeService(names=[])
    result = await find_collision(service, "a", "p", "s")
    assert result is False
