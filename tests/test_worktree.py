"""Tests for state_core.worktree — WorktreeService Protocol + WorktreeInfo model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from state_core.worktree import WorktreeInfo, WorktreeService


class FakeWorktreeService:
    """Minimal structural conformance to the WorktreeService Protocol."""

    async def create(self, name: str, branch: str) -> WorktreeInfo:
        return WorktreeInfo(name=name, path=f"/tmp/{name}", branch=branch)

    async def list(self) -> list[WorktreeInfo]:
        return []

    async def remove(self, name: str) -> None:
        pass

    async def reset(self, name: str) -> None:
        pass


class IncompleteWorktreeService:
    """Missing list and reset — should fail structural check."""

    async def create(self, name: str, branch: str) -> WorktreeInfo:
        return WorktreeInfo(name=name, path=f"/tmp/{name}", branch=branch)

    async def remove(self, name: str) -> None:
        pass


def test_worktree_info_valid_construction() -> None:
    """WorktreeInfo can be constructed with required fields."""
    info = WorktreeInfo(name="slice/a-1/p-2/s-3", path="/tmp/slice-3", branch="main")
    assert info.name == "slice/a-1/p-2/s-3"
    assert info.path == "/tmp/slice-3"
    assert info.branch == "main"


def test_worktree_info_defaults() -> None:
    """Locked and prunable default to False."""
    info = WorktreeInfo(name="test", path="/tmp/test", branch="main")
    assert info.locked is False
    assert info.prunable is False


def test_worktree_info_all_fields() -> None:
    """All 5 fields are accepted including optional booleans."""
    info = WorktreeInfo(
        name="locked-wt",
        path="/tmp/locked",
        branch="feature/x",
        locked=True,
        prunable=True,
    )
    assert info.locked is True
    assert info.prunable is True


def test_worktree_info_rejects_unknown_fields() -> None:
    """extra='forbid' rejects unexpected keys."""
    with pytest.raises(ValidationError):
        WorktreeInfo(name="test", path="/tmp", branch="main", bogus="nope")  # type: ignore[call-arg]


def test_worktree_info_frozen_immutable() -> None:
    """frozen=True prevents mutation after construction."""
    info = WorktreeInfo(name="test", path="/tmp/test", branch="main")
    with pytest.raises(ValidationError):
        info.name = "changed"  # type: ignore[misc]


def test_protocol_structural_subtyping() -> None:
    """A class with all 4 methods is recognised as a WorktreeService."""
    assert isinstance(FakeWorktreeService(), WorktreeService)


def test_protocol_rejects_incomplete_implementation() -> None:
    """A class missing methods is not recognised as a WorktreeService."""
    assert not isinstance(IncompleteWorktreeService(), WorktreeService)


def test_worktree_service_is_runtime_checkable() -> None:
    """Protocol is decorated with @runtime_checkable so isinstance works."""
    assert hasattr(WorktreeService, "_is_runtime_protocol") or hasattr(
        WorktreeService, "__protocol_attrs__"
    )
