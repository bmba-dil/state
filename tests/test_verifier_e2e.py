"""End-to-end verifier for the 10,000-event golden fixture.

Verifies:
1. Golden fixture DB SHA-256 matches recorded checksum
2. JSONL export is deterministic (triple checksum assertion)
3. Projector rebuild is deterministic
4. Crash-recovery repair is a no-op on consistent fixture
5. Mode-filtered event counts sum to total
6. Deterministic replay is bit-identical across independent runs

Run: pytest tests/test_verifier_e2e.py -x -v
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from src.state_core.events import SqliteEventStore
from src.state_core.projector import Projector

# ── Paths ────────────────────────────────────────────────────────────────

FIXTURES_DIR = Path.cwd() / ".state" / "fixtures"
FIXTURE_DB = FIXTURES_DIR / "golden-10k.sqlite"
CHECKSUMS_FILE = FIXTURES_DIR / "golden-10k-checksums.json"

# ── Fixtures ──────────────────────────────────────────────────────────────


def _load_checksums() -> dict[str, str]:
    """Load the golden checksums JSON file."""
    if not CHECKSUMS_FILE.exists():
        pytest.skip(f"Golden fixture checksums not found: {CHECKSUMS_FILE}")
    with open(CHECKSUMS_FILE) as f:
        return json.load(f)


@pytest.fixture(scope="module")
def checksums() -> dict[str, str]:
    """Module-scoped checksums — loaded once per test module."""
    return _load_checksums()


@pytest.fixture
def fixture_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Copy the golden fixture to a temp path and set STATE_DB_PATH.

    Returns the path to the copied fixture.
    """
    if not FIXTURE_DB.exists():
        pytest.skip(f"Golden fixture DB not found: {FIXTURE_DB}")
    dest = tmp_path / ".state" / "events.sqlite"
    dest.parent.mkdir(parents=True)
    shutil.copy2(FIXTURE_DB, dest)
    monkeypatch.setenv("STATE_DB_PATH", str(dest))

    # Also copy migrations for migrate() calls (used by some tests)
    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)

    return dest


class TestGoldenFixtureIntegrity:
    """Verify the golden fixture file integrity via SHA-256 checksum."""

    def test_db_checksum_matches(self, checksums: dict[str, str]) -> None:
        """Golden fixture DB SHA-256 must match recorded checksum."""
        db_bytes = FIXTURE_DB.read_bytes()
        actual = hashlib.sha256(db_bytes).hexdigest()
        expected = checksums["db_sha256"]
        assert actual == expected, (
            f"Golden fixture DB checksum mismatch!\n"
            f"  Expected: {expected}\n"
            f"  Actual:   {actual}\n"
            f"  The golden fixture has been modified or corrupted. "
            f"Run `.state/fixtures/regenerate_fixture.py` to regenerate."
        )

    # Note: this test is synchronous — no DB connection needed.
    # pytest.mark.asyncio is NOT required.


class TestTripleChecksumAssertion:
    """Triple verification: DB SHA-256 = export JSONL SHA-256 = projection snapshot SHA-256.

    Loads the golden fixture, exports to JSONL, runs rebuild_all(),
    and checksums all three independently.
    """

    async def test_export_jsonl_checksum(
        self, fixture_copy: Path, checksums: dict[str, str],
    ) -> None:
        """Export all events as JSONL, compute SHA-256, match recorded value."""
        store = SqliteEventStore()
        lines: list[str] = []
        async for ev in store.read_events_iter():
            line = json.dumps(ev, sort_keys=True, separators=(",", ":"))
            lines.append(line)
        jsonl_bytes = ("\n".join(lines) + "\n").encode("utf-8")
        actual = hashlib.sha256(jsonl_bytes).hexdigest()
        expected = checksums["export_jsonl_sha256"]
        assert actual == expected, (
            f"Export JSONL checksum mismatch!\n"
            f"  Expected: {expected}\n"
            f"  Actual:   {actual}\n"
            f"  Event export is non-deterministic. Check for datetime.now(), "
            f"ULID auto-generation, or non-deterministic JSON serialization."
        )

    async def test_projection_snapshot_checksum(
        self, fixture_copy: Path, checksums: dict[str, str],
    ) -> None:
        """Rebuild projections, snapshot cache tables, SHA-256 match recorded value."""
        store = SqliteEventStore()
        projector = Projector(db=store)
        count = await projector.rebuild_all()
        assert count == 10000, f"Expected 10000 events, got {count}"

        # Dump all three cache tables as sorted JSON.
        # Must match the generator's exact approach: row_factory=None,
        # frontmatter left as JSON string (not parsed to dict).
        snapshot: dict[str, list[dict]] = {}
        from src.state_core.database import get_connection

        for table in ("steps", "slices", "concepts"):
            async with get_connection() as db:
                cursor = await db.execute(f"SELECT * FROM {table} ORDER BY id")
                columns = [desc[0] for desc in cursor.description]
                rows = await cursor.fetchall()
                snapshot[table] = [dict(zip(columns, row)) for row in rows]

        snapshot_json = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
        actual = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
        expected = checksums["projection_snapshot_sha256"]
        assert actual == expected, (
            f"Projection snapshot checksum mismatch!\n"
            f"  Expected: {expected}\n"
            f"  Actual:   {actual}\n"
            f"  Projections are non-deterministic. Check handler purity."
        )


class TestCrashRecoveryOnGolden:
    """Crash-recovery repair is a no-op on the consistent golden fixture."""

    async def test_repair_is_noop_on_golden_fixture(
        self, fixture_copy: Path,
    ) -> None:
        """Running repair_aggregate_seqs() on the consistent golden fixture does nothing."""
        store = SqliteEventStore()
        repairs = await store.repair_aggregate_seqs()
        assert repairs == [], (
            f"Repair should be a no-op on the golden fixture, "
            f"but found {len(repairs)} repairs: {repairs}"
        )

    async def test_repair_twice_idempotent(
        self, fixture_copy: Path,
    ) -> None:
        """Two repair calls are both no-ops on the golden fixture."""
        store = SqliteEventStore()
        r1 = await store.repair_aggregate_seqs()
        r2 = await store.repair_aggregate_seqs()
        assert r1 == [], f"First repair should be no-op, got {r1}"
        assert r2 == [], f"Second repair should be no-op, got {r2}"


class TestModeFiltering:
    """Mode-filtered event counts sum to the total on the golden fixture."""

    async def test_mode_counts_sum_to_total(
        self, fixture_copy: Path,
    ) -> None:
        """count_events("build") + count_events("teach") + count_events("kernel") == count_events()."""
        store = SqliteEventStore()
        total = await store.count_events()
        assert total == 10000, f"Expected 10000 events, got {total}"

        build = await store.count_events(mode="build")
        teach = await store.count_events(mode="teach")
        kernel = await store.count_events(mode="kernel")

        assert build + teach + kernel == total, (
            f"Mode counts don't sum to total: "
            f"{build} + {teach} + {kernel} = {build + teach + kernel} != {total}"
        )

    async def test_each_mode_has_events(
        self, fixture_copy: Path,
    ) -> None:
        """All three modes have at least one event."""
        store = SqliteEventStore()
        for mode in ("build", "teach", "kernel"):
            count = await store.count_events(mode=mode)
            assert count > 0, f"Mode '{mode}' has zero events in the golden fixture"


class TestDeterministicReplay:
    """Replaying the golden fixture twice produces identical output."""

    async def test_replay_deterministic(
        self, fixture_copy: Path,
    ) -> None:
        """Two independent replays of the same fixture produce identical event lists."""
        store = SqliteEventStore()

        # First replay: read all events in order
        events_1 = await store.read_events()

        # Second replay: read via iterator
        events_2: list[dict] = []
        async for ev in store.read_events_iter():
            events_2.append(ev)

        # Both must be identical (same number, same data)
        assert len(events_1) == len(events_2) == 10000

        # Compare first and last events as a quick check
        for key in ("id", "seq", "type", "mode", "aggregate_id"):
            assert events_1[0][key] == events_2[0][key], (
                f"First event mismatch on {key}: "
                f"{events_1[0][key]} != {events_2[0][key]}"
            )
            assert events_1[-1][key] == events_2[-1][key], (
                f"Last event mismatch on {key}: "
                f"{events_1[-1][key]} != {events_2[-1][key]}"
            )

        # Full data comparison (10000 events × dict comparison)
        # This is expensive but necessary for bit-identical proof
        assert events_1 == events_2, "Full event list mismatch on second replay"

    async def test_replay_with_mode_filter(
        self, fixture_copy: Path,
    ) -> None:
        """Replay with --mode filter produces subset that sums to total."""
        store = SqliteEventStore()
        all_events = await store.read_events()
        build_events = await store.read_events(mode="build")
        teach_events = await store.read_events(mode="teach")
        kernel_events = await store.read_events(mode="kernel")

        assert len(build_events) + len(teach_events) + len(kernel_events) == len(all_events)
        # Mode-filtered sets are disjoint
        build_ids = {e["id"] for e in build_events}
        teach_ids = {e["id"] for e in teach_events}
        kernel_ids = {e["id"] for e in kernel_events}
        assert build_ids.isdisjoint(teach_ids)
        assert build_ids.isdisjoint(kernel_ids)
        assert teach_ids.isdisjoint(kernel_ids)
