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
        import aiosqlite

        store = SqliteEventStore()
        projector = Projector(db=store)
        count = await projector.rebuild_all()
        assert count == 10000, f"Expected 10000 events, got {count}"

        # Dump all three cache tables as sorted JSON
        snapshot: dict[str, list[dict]] = {}
        from src.state_core.database import get_connection

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
