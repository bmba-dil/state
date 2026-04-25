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
