"""Tests for state_core.snapshot — content-addressed snapshots."""

from __future__ import annotations

from pathlib import Path

import pytest

from state_core.snapshot import (
    SnapshotManager,
    _hash_file,
    _hash_directory,
)


def test_hash_file_deterministic(tmp_path: Path) -> None:
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    h1 = _hash_file(f)
    h2 = _hash_file(f)
    assert h1 == h2
    assert len(h1) == 64


def test_hash_file_different_content(tmp_path: Path) -> None:
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("hello")
    f2.write_text("world")
    assert _hash_file(f1) != _hash_file(f2)


def test_hash_directory_deterministic(tmp_path: Path) -> None:
    (tmp_path / "x.txt").write_text("x")
    (tmp_path / "y.txt").write_text("y")
    d1 = _hash_directory(tmp_path)
    d2 = _hash_directory(tmp_path)
    assert d1 == d2


def test_hash_directory_empty(tmp_path: Path) -> None:
    d = _hash_directory(tmp_path)
    assert len(d) == 64


@pytest.mark.asyncio
async def test_snapshot_track_step(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("snapshot content")
    manager = SnapshotManager()
    snap_id = await manager.track("step", "slice-1/step-1", worktree_dir=tmp_path)
    assert snap_id.startswith("step-")
    assert len(snap_id) > 6


@pytest.mark.asyncio
async def test_snapshot_track_slice(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("slice content")
    manager = SnapshotManager()
    snap_id = await manager.track("slice", "slice-1", reason="shipped",
                                  worktree_dir=tmp_path)
    assert snap_id.startswith("slice-")


@pytest.mark.asyncio
async def test_snapshot_list(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("x")
    manager = SnapshotManager()
    await manager.track("step", "ref-1", worktree_dir=tmp_path)

    (tmp_path / "f.txt").write_text("y")
    await manager.track("step", "ref-2", worktree_dir=tmp_path)

    entries = manager.list()
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_snapshot_diff_identical(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("same")
    manager = SnapshotManager()
    sid1 = await manager.track("step", "r1", worktree_dir=tmp_path)
    sid2 = await manager.track("step", "r2", worktree_dir=tmp_path)

    result = manager.diff(sid1, sid2)
    assert result["status"] == "identical"


@pytest.mark.asyncio
async def test_snapshot_diff_different(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("v1")
    manager = SnapshotManager()
    sid1 = await manager.track("step", "r1", worktree_dir=tmp_path)

    (tmp_path / "f.txt").write_text("v2")
    sid2 = await manager.track("step", "r2", worktree_dir=tmp_path)

    result = manager.diff(sid1, sid2)
    assert result["status"] == "different"


@pytest.mark.asyncio
async def test_snapshot_diff_missing(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("x")
    manager = SnapshotManager()
    await manager.track("step", "r1", worktree_dir=tmp_path)

    result = manager.diff("missing-id", "also-missing")
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_snapshot_get(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("x")
    manager = SnapshotManager()
    sid = await manager.track("slice", "ref", worktree_dir=tmp_path)

    entry = manager.get(sid)
    assert entry is not None
    assert entry.tier == "slice"
    assert entry.ref == "ref"
