---
phase: 010-event-store-verifier-10-000
plan: D
type: checkpoint
autonomous: false
wave: 2
depends_on:
  - 010-A
files_modified:
  - tests/test_verifier_e2e.py
requirements: [EVT-06]
---

<objective>
Create the golden fixture end-to-end verifier at tests/test_verifier_e2e.py. This file proves:
1. The golden fixture DB checksum matches the recorded value
2. Export JSONL from the fixture produces a deterministic checksum
3. Projector rebuild from the fixture produces deterministic cache tables
4. Crash-recovery repair is a no-op on the consistent fixture
5. Mode-filtered counts sum correctly
6. Deterministic replay is bit-identical across two independent runs
</objective>

<threat_model>
ASVS L1 threats for Plan D:
- V6 (Integrity Verification): SHA-256 checksums in golden-10k-checksums.json are the integrity anchor. If any checksum changes, tests MUST fail. The test reads checksums from the JSON file, not hardcoded values.
- V12 (File Resources): The golden fixture is read-only (loaded as static file, copied before use). Never modified in place. Fixture path is hardcoded relative to project root — no user-controlled input.
- V7 (Error Handling): If golden fixture file is missing, tests must skip with a clear message (not crash with obscure traceback). Use pytest.skip() with explanation.
- V10 (Malicious Code): The fixture generator script (Plan A) could be tampered with to produce a fixture with wrong events. Mitigation: all three checksums must match. If any single checksum diverges, the test fails.
</threat_model>

<read_first>
- .planning/milestones/v1/phases/010-event-store-verifier-10-000/010-RESEARCH.md (section 3: golden fixture, section 5: determinism verification, section 7: integration test flow)
- .planning/milestones/v1/phases/010-event-store-verifier-10-000/010-VALIDATION.md (goals: golden fixture verification, triple assertion)
- src/state_core/events.py (count_events with mode filter, read_events_iter)
- src/state_core/projector.py (Projector.rebuild_all)
- tests/test_events.py (existing _sorted_json helper pattern, _isolate_db fixture)
- tests/test_cli.py (structlog suppression, CliRunner pattern)
</read_first>

## Tasks

### Task 1: Create tests/test_verifier_e2e.py — setup + golden fixture checksum verification

<read_first>
- tests/test_events.py (line 23-33 — _isolate_db fixture pattern using monkeypatch)
- tests/test_cli.py (line 26-28 — structlog CRITICAL suppression for CLI tests)
</read_first>

<action>
Create `tests/test_verifier_e2e.py` with the following structure:

```python
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
from src.state_core.migrations import migrate

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
```

</action>

<acceptance_criteria>
- `tests/test_verifier_e2e.py` exists
- `FIXTURE_DB`, `CHECKSUMS_FILE`, `FIXTURES_DIR` constants point to correct paths
- `fixture_copy` fixture copies DB and sets STATE_DB_PATH
- `_load_checksums` reads and returns the JSON checksums dict
</acceptance_criteria>

### Task 2: Add golden fixture DB checksum assertion test

<read_first>
- FIXTURE_DB and CHECKSUMS_FILE paths
</read_first>

<action>
Add `TestGoldenFixtureIntegrity` class:

```python
class TestGoldenFixtureIntegrity:
    """Verify the golden fixture file integrity via SHA-256 checksum."""

    async def test_db_checksum_matches(self, checksums: dict[str, str]) -> None:
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
```

</action>

<acceptance_criteria>
- `test_db_checksum_matches` passes when fixture is intact
- Test fails with clear error message when fixture is modified
- Error message includes regeneration instructions
</acceptance_criteria>

### Task 3: Add triple-checksum assertion test

<read_first>
- src/state_core/events.py (read_events_iter for JSONL export simulation)
- src/state_core/projector.py (Projector.rebuild_all)
- src/state_cli/main.py (export uses `json.dumps(ev, sort_keys=True, separators=(",", ":"))`)
</read_first>

<action>
Add `TestTripleChecksumAssertion` class:

```python
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

        # Dump all three cache tables as sorted JSON
        snapshot: dict[str, list[dict]] = {}
        from src.state_core.database import get_connection
        import aiosqlite

        for table in ("steps", "slices", "concepts"):
            async with get_connection() as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(f"SELECT * FROM {table} ORDER BY id")
                rows = await cursor.fetchall()
                rows_list: list[dict] = []
                for row in rows:
                    d = dict(row)
                    # Re-serialize frontmatter deterministically for comparison
                    if isinstance(d.get("frontmatter"), str):
                        d["frontmatter"] = json.loads(d["frontmatter"])
                    rows_list.append(d)
                snapshot[table] = rows_list

        snapshot_json = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        actual = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
        expected = checksums["projection_snapshot_sha256"]
        assert actual == expected, (
            f"Projection snapshot checksum mismatch!\n"
            f"  Expected: {expected}\n"
            f"  Actual:   {actual}\n"
            f"  Projections are non-deterministic. Check handler purity."
        )
```

Note: The CLI export uses `json.dumps(ev, sort_keys=True, separators=(",", ":"))`. The test must use the exact same serialization to produce a matching checksum.

</action>

<acceptance_criteria>
- `test_export_jsonl_checksum` computes SHA-256 of all 10,000 events as JSONL and matches `export_jsonl_sha256`
- `test_projection_snapshot_checksum` rebuilds all projections, dumps cache tables as sorted JSON, computes SHA-256, and matches `projection_snapshot_sha256`
- Both tests fail with clear error message on mismatch
</acceptance_criteria>

### Task 4: Add crash-recovery no-op test

<read_first>
- src/state_core/events.py (repair_aggregate_seqs — lines 255-323)
- tests/test_seq_crash_recovery.py (TestRepairAggregateSeqs — especially test_repair_already_consistent and test_repair_twice_idempotent)
</read_first>

<action>
Add `TestCrashRecoveryOnGolden` class:

```python
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
```

</action>

<acceptance_criteria>
- `test_repair_is_noop_on_golden_fixture` passes: `repairs == []`
- `test_repair_twice_idempotent` passes: both calls return empty list
- Tests verify the fixture aggregate_seq is fully consistent
</acceptance_criteria>

### Task 5: Add mode filter verification test

<read_first>
- src/state_core/events.py (count_events with mode filter — lines 451-472)
</read_first>

<action>
Add `TestModeFiltering` class:

```python
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
```

</action>

<acceptance_criteria>
- `test_mode_counts_sum_to_total` passes: build + teach + kernel == 10000
- `test_each_mode_has_events` passes: each mode has count > 0
</acceptance_criteria>

### Task 6: Add deterministic replay idempotence test

<read_first>
- src/state_core/events.py (read_events — from_id/to_id/mode/limit filter)
</read_first>

<action>
Add `TestDeterministicReplay` class:

```python
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
```

</action>

<acceptance_criteria>
- `test_replay_deterministic` passes: two independent reads produce identical event lists
- `test_replay_with_mode_filter` passes: mode-filtered sets are disjoint and sum to total
</acceptance_criteria>

## Verification

1. `pytest tests/test_verifier_e2e.py -x -v` — all 8 tests pass
2. Manually corrupt golden-10k.sqlite (e.g., `echo x >>`), rerun — `test_db_checksum_matches` MUST fail
3. Modify fixture, regenerate, rerun — all tests pass with new checksums
4. `pytest tests/ -x --co` — full test suite passes with no regressions (all existing tests in test_events.py, test_projector.py, test_seq_crash_recovery.py, test_cli.py still pass)

## Must Haves

- Eight test methods across five test classes
- `test_db_checksum_matches` — reads checksums from file, not hardcoded
- Triple assertion: DB checksum = export JSONL checksum = projection snapshot checksum
- Crash-recovery tests prove repair is no-op on consistent fixture
- Mode-filter tests prove all 3 modes present and counting sums correct
- Replay determinism proves two independent reads produce identical results
- Tests use pytest.skip() with clear message when fixture files are missing
- Tests copy the fixture to temp before use (never modify the original)
</must_haves>
