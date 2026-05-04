"""Tests for state_core.worktree_bootstrap — transactional bootstrap."""

from __future__ import annotations

from pathlib import Path

import pygit2
import pytest

from state_core.pygit2_worktree import Pygit2WorktreeService
from state_core.worktree_bootstrap import STATE_DIR, WorktreeBootstrapper
from state_core.worktree_naming import format_worktree_name


@pytest.fixture
def seeded_repo(tmp_path: Path) -> Path:
    """Repo with initial commit and .state/ dir."""
    repo_dir = tmp_path / "test-repo"
    repo_dir.mkdir()
    repo = pygit2.init_repository(str(repo_dir))
    sig = pygit2.Signature("Test", "test@test.com")
    blob = repo.create_blob("initial")
    tb = repo.TreeBuilder()
    tree_oid = tb.write()
    repo.create_commit("refs/heads/main", sig, sig, "initial", tree_oid, [])
    repo.set_head("refs/heads/main")

    (repo_dir / STATE_DIR).mkdir()
    (repo_dir / STATE_DIR / "events.sqlite").write_text("")
    (repo_dir / STATE_DIR / "config.json").write_text("{}")

    return repo_dir


@pytest.mark.asyncio
async def test_bootstrap_creates_worktree(seeded_repo: Path) -> None:
    """bootstrap creates a worktree with deterministic name."""
    service = Pygit2WorktreeService(str(seeded_repo))
    bootstrapper = WorktreeBootstrapper(service, seeded_repo)

    info = await bootstrapper.bootstrap("arc-1", "phase-2", "slice-3")

    expected_name = format_worktree_name("arc-1", "phase-2", "slice-3")
    assert info.name == expected_name
    assert info.branch == expected_name
    assert Path(info.path).is_dir()


@pytest.mark.asyncio
async def test_bootstrap_links_state_dir(seeded_repo: Path) -> None:
    """bootstrap copies .state/ into worktree."""
    service = Pygit2WorktreeService(str(seeded_repo))
    bootstrapper = WorktreeBootstrapper(service, seeded_repo)

    info = await bootstrapper.bootstrap("a1", "p2", "s3")

    worktree_path = Path(info.path)
    assert (worktree_path / STATE_DIR).is_dir()
    assert (worktree_path / STATE_DIR / "events.sqlite").exists()
    assert (worktree_path / STATE_DIR / "config.json").exists()


@pytest.mark.asyncio
async def test_bootstrap_cleanup_on_service_failure(seeded_repo: Path) -> None:
    """bootstrap propagates error when service.create fails."""
    class _FailingService:
        async def create(self, name: str, branch: str):
            raise RuntimeError("simulated failure")
        async def list(self): return []
        async def remove(self, name: str): pass
        async def reset(self, name: str): pass

    bootstrapper = WorktreeBootstrapper(_FailingService(), seeded_repo)

    with pytest.raises(RuntimeError, match="simulated failure"):
        await bootstrapper.bootstrap("ax", "px", "sx")

    assert True


@pytest.mark.asyncio
async def test_bootstrap_without_parent_state(seeded_repo: Path) -> None:
    """bootstrap creates empty .state/ when parent lacks it."""
    service = Pygit2WorktreeService(str(seeded_repo))
    empty_parent = seeded_repo.parent / "no-state-repo"
    empty_parent.mkdir()
    empty_repo = pygit2.init_repository(str(empty_parent))
    sig = pygit2.Signature("Test", "test@test.com")
    blob = empty_repo.create_blob("initial")
    tb = empty_repo.TreeBuilder()
    tree_oid = tb.write()
    empty_repo.create_commit("refs/heads/main", sig, sig, "initial", tree_oid, [])
    empty_repo.set_head("refs/heads/main")

    empty_service = Pygit2WorktreeService(str(empty_parent))
    bootstrapper = WorktreeBootstrapper(empty_service, empty_parent)

    info = await bootstrapper.bootstrap("a1", "p1", "s1")
    assert (Path(info.path) / STATE_DIR).is_dir()
