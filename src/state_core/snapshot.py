"""Step + Slice tier snapshot glue for fine-grained revert."""

from __future__ import annotations


class SnapshotManager:
    """Manages snapshots at Step and Slice boundaries."""

    async def track(self, tier: str, ref: str) -> str: ...
    async def revert(self, snapshot_id: str) -> None: ...
