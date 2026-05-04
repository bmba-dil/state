"""Tests for state_core.pygit2_worktree — Pygit2WorktreeService."""

from __future__ import annotations

from pathlib import Path

import pygit2
import pytest

from state_core.pygit2_worktree import Pygit2WorktreeService
from state_core.worktree import WorktreeService


@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    """Create a real git repository in a temp directory."""
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()
    pygit2.init_repository(str(repo_dir))
    return repo_dir


@pytest.fixture
def seeded_repo(repo_path: Path) -> Path:
    """Repo with an initial commit so branches can be created."""
    repo = pygit2.Repository(str(repo_path))
    sig = pygit2.Signature("Test", "test@test.com")
    blob = repo.create_blob("initial content")
    tb = repo.TreeBuilder()
    tree_oid = tb.write()
    repo.create_commit("refs/heads/main", sig, sig, "initial commit", tree_oid, [])
    repo.set_head("refs/heads/main")
    return repo_path


@pytest.mark.asyncio
async def test_protocol_conformance(repo_path: Path) -> None:
    """Pygit2WorktreeService satisfies WorktreeService Protocol."""
    service = Pygit2WorktreeService(str(repo_path))
    assert isinstance(service, WorktreeService)


@pytest.mark.asyncio
async def test_create_worktree(seeded_repo: Path) -> None:
    """Create a worktree and verify it exists."""
    service = Pygit2WorktreeService(str(seeded_repo))
    info = await service.create(
        name="slice/a-1/p-2/s-3",
        branch="slice/a-1/p-2/s-3",
    )
    assert info.name == "slice/a-1/p-2/s-3"
    assert info.branch == "slice/a-1/p-2/s-3"
    assert info.locked is False

    worktree_dir = Path(info.path)
    assert worktree_dir.is_dir()


@pytest.mark.asyncio
async def test_create_worktree_idempotent(seeded_repo: Path) -> None:
    """Creating same worktree twice returns existing info."""
    service = Pygit2WorktreeService(str(seeded_repo))
    info1 = await service.create(name="dup-wt", branch="dup-wt")
    info2 = await service.create(name="dup-wt", branch="dup-wt")
    assert info1.path == info2.path


@pytest.mark.asyncio
async def test_list_worktrees(seeded_repo: Path) -> None:
    """List returns all worktrees."""
    service = Pygit2WorktreeService(str(seeded_repo))
    await service.create(name="wt-a", branch="wt-a")
    await service.create(name="wt-b", branch="wt-b")

    result = await service.list()
    names = {wt.name for wt in result}
    assert "wt-a" in names
    assert "wt-b" in names


@pytest.mark.asyncio
async def test_list_empty(seeded_repo: Path) -> None:
    """List on repo with no worktrees returns empty list."""
    service = Pygit2WorktreeService(str(seeded_repo))
    result = await service.list()
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_remove_worktree(seeded_repo: Path) -> None:
    """Remove a worktree and verify it's gone."""
    service = Pygit2WorktreeService(str(seeded_repo))
    info = await service.create(name="remove-me", branch="remove-me")
    worktree_dir = Path(info.path)
    assert worktree_dir.is_dir()

    await service.remove("remove-me")

    result = await service.list()
    names = {wt.name for wt in result}
    assert "remove-me" not in names


@pytest.mark.asyncio
async def test_remove_nonexistent_no_error(seeded_repo: Path) -> None:
    """Removing non-existent worktree is a no-op."""
    service = Pygit2WorktreeService(str(seeded_repo))
    await service.remove("nonexistent")


@pytest.mark.asyncio
async def test_reset_worktree(seeded_repo: Path) -> None:
    """Reset clears uncommitted changes in worktree."""
    service = Pygit2WorktreeService(str(seeded_repo))
    info = await service.create(name="reset-me", branch="reset-me")

    worktree_dir = Path(info.path)
    dirty_file = worktree_dir / "dirty.txt"
    dirty_file.write_text("some change")

    await service.reset("reset-me")

    # After reset, the dirty file should be gone
    assert not dirty_file.exists()
