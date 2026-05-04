"""Step + Slice tier snapshot manager (WRK-06, WRK-07).

Content-addressed snapshots at two tiers:
  - Step tier: captured pre-execute and pre-verify
  - Slice tier: captured on boundary (ship-time)

Snapshots are content-addressed (SHA-256) of tracked files within a
worktree. The hash is stored as an event in the event store and written
to the STEP.md / SLICE.md frontmatter.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import structlog

log = structlog.get_logger(__name__)

SnapshotTier = Literal["step", "slice"]
SnapshotReason = Literal["pre_execute", "pre_verify", "shipped"]

SNAPSHOT_CHUNK_SIZE = 65536


def _hash_file(path: Path) -> str:
    """SHA-256 hex digest of file contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(SNAPSHOT_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _hash_directory(dir_path: Path) -> str:
    """SHA-256 hex digest of all files in a directory (sorted by path)."""
    h = hashlib.sha256()
    files = sorted(p for p in dir_path.rglob("*") if p.is_file())
    for path in files:
        rel = path.relative_to(dir_path)
        h.update(str(rel).encode())
        h.update(_hash_file(path).encode())
    return h.hexdigest()


class SnapshotEntry:
    """Metadata for a single snapshot."""

    def __init__(
        self,
        snapshot_id: str,
        tier: SnapshotTier,
        reason: SnapshotReason,
        ref: str,
        hash_digest: str,
    ) -> None:
        self.snapshot_id = snapshot_id
        self.tier = tier
        self.reason = reason
        self.ref = ref
        self.hash_digest = hash_digest


class SnapshotManager:
    """Manages content-addressed snapshots at Step and Slice boundaries.

    Usage::

        manager = SnapshotManager()
        snap_id = await manager.track("step", "arc-1/phase-2/slice-3/step-1",
                                       reason="pre_execute",
                                       worktree_dir=Path("/tmp/wt-1"))
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, SnapshotEntry] = {}

    async def track(
        self,
        tier: SnapshotTier,
        ref: str,
        reason: SnapshotReason = "pre_execute",
        worktree_dir: Path | None = None,
    ) -> str:
        """Capture a snapshot of the worktree at *worktree_dir*.

        Args:
            tier: "step" or "slice".
            ref: Hierarchical reference string.
            reason: Why the snapshot is being taken.
            worktree_dir: Directory to snapshot. If None, snapshots cwd.

        Returns:
            A snapshot_id (content hash) that can be used for diff/revert.
        """
        target = worktree_dir or Path.cwd()

        if not target.is_dir():
            raise FileNotFoundError(f"worktree directory not found: {target}")

        digest = _hash_directory(target)

        # Create a short composite ID: {tier}-{digest[:12]}
        snapshot_id = f"{tier}-{digest[:12]}"

        entry = SnapshotEntry(
            snapshot_id=snapshot_id,
            tier=tier,
            reason=reason,
            ref=ref,
            hash_digest=digest,
        )
        self._snapshots[snapshot_id] = entry

        log.info("snapshot captured",
                 snapshot_id=snapshot_id,
                 tier=tier,
                 reason=reason,
                 ref=ref,
                 digest=digest[:16])

        return snapshot_id

    def list(self) -> list[SnapshotEntry]:
        """List all snapshots, most recent first."""
        return list(self._snapshots.values())[::-1]

    def diff(self, snapshot_a: str, snapshot_b: str) -> dict[str, str]:
        """Compare two snapshots by digest.

        Returns:
            {"status": "identical" | "different", "a": digest, "b": digest}
        """
        entry_a = self._snapshots.get(snapshot_a)
        entry_b = self._snapshots.get(snapshot_b)

        if entry_a is None or entry_b is None:
            missing = []
            if entry_a is None:
                missing.append(snapshot_a)
            if entry_b is None:
                missing.append(snapshot_b)
            return {"status": "error", "missing": ",".join(missing)}

        if entry_a.hash_digest == entry_b.hash_digest:
            return {"status": "identical", "digest": entry_a.hash_digest}
        return {
            "status": "different",
            "a": entry_a.hash_digest[:16],
            "b": entry_b.hash_digest[:16],
        }

    def get(self, snapshot_id: str) -> SnapshotEntry | None:
        """Look up a snapshot by ID."""
        return self._snapshots.get(snapshot_id)
