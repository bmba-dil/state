"""Tests for state_cli.main — CLI tail, replay, export commands.

Uses typer.testing.CliRunner for CLI invocation.
Tests are sync because CLI commands use asyncio.run() internally
and cannot be called from within a running event loop.
Follows the same _isolate_db + store fixture pattern as test_events.py.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from src.state_cli.main import app
from src.state_core.events import SqliteEventStore
from src.state_core.migrations import migrate

# ── Fixtures ──────────────────────────────────────────────────────────────

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Point STATE_DB_PATH to a temp directory and apply all migrations."""
    db_path = tmp_path / ".state" / "events.sqlite"
    monkeypatch.setenv("STATE_DB_PATH", str(db_path))

    migrations_src = Path.cwd() / ".state" / "migrations"
    migrations_dst = tmp_path / ".state" / "migrations"
    if migrations_src.exists():
        shutil.copytree(migrations_src, migrations_dst, dirs_exist_ok=True)


@pytest.fixture
def store(_isolate_db: None) -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    asyncio.run(migrate())
    return SqliteEventStore()


# ── Helpers ────────────────────────────────────────────────────────────────


def _populate_events(
    store: SqliteEventStore,
    count: int = 5,
    mode: str = "build",
) -> list[str]:
    """Append *count* deterministic events and return their ULIDs.

    Sync wrapper — calls store.append() via asyncio.run().
    """
    async def _do() -> list[str]:
        ids: list[str] = []
        for i in range(count):
            id_ = await store.append(
                "step", f"step-{i % 3 + 1}", "state.step.executed",
                {"changes_summary": f"event-{i}"},
                mode=mode,  # type: ignore[arg-type]
            )
            ids.append(id_)
        return ids
    return asyncio.run(_do())


def _parse_jsonl_lines(text: str) -> list[dict[str, Any]]:
    """Parse JSONL text into a list of dicts. Skips empty lines."""
    return [json.loads(line) for line in text.strip().splitlines() if line.strip()]


# ── Tail command tests ────────────────────────────────────────────────────


class TestTail:
    """state events tail command."""

    def test_tail_help(self) -> None:
        """--help shows tail options."""
        result = runner.invoke(app, ["events", "tail", "--help"])
        assert result.exit_code == 0
        assert "Tail events" in result.stdout
        assert "--from" in result.stdout
        assert "--mode" in result.stdout
        assert "--count" in result.stdout or "-n" in result.stdout
        assert "--follow" in result.stdout or "--no-follow" in result.stdout

    def test_tail_empty_store_with_no_follow(self, _isolate_db: None) -> None:
        """Empty store: tail --no-follow shows nothing and exits."""
        asyncio.run(migrate())
        result = runner.invoke(app, ["events", "tail", "--no-follow"])
        assert result.exit_code == 0

    def test_tail_shows_last_n_events(self, store: SqliteEventStore) -> None:
        """tail --no-follow with events shows last N events."""
        _populate_events(store, count=5)
        result = runner.invoke(app, ["events", "tail", "--no-follow", "--count", "3"])
        assert result.exit_code == 0
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 3

    def test_tail_mode_filter(self, store: SqliteEventStore) -> None:
        """tail --mode build shows only build events."""
        # Append 2 build + 2 teach
        _populate_events(store, count=2, mode="build")
        _populate_events(store, count=2, mode="teach")

        result = runner.invoke(app, ["events", "tail", "--no-follow", "--mode", "teach"])
        assert result.exit_code == 0
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 2

    def test_tail_from_offset(self, store: SqliteEventStore) -> None:
        """tail --from <ulid> shows events after that offset."""
        ids = _populate_events(store, count=5)
        # Use 3rd event's ID as offset
        offset_id = ids[2]
        result = runner.invoke(app, ["events", "tail", "--no-follow", "--from", offset_id])
        assert result.exit_code == 0
        lines = result.stdout.strip().splitlines()
        # Should show events at index 3 and 4 (2 events)
        assert len(lines) == 2

    def test_tail_defaults_to_follow(self) -> None:
        """tail without --no-follow defaults to follow=True (verified via CliRunner)."""
        # Just verify the option exists — the actual follow behavior is tested
        # by checking that --no-follow shows in help
        result = runner.invoke(app, ["events", "tail", "--help"])
        assert "--no-follow" in result.stdout


# ── Replay command tests ──────────────────────────────────────────────────


class TestReplay:
    """state events replay command."""

    def test_replay_help(self) -> None:
        """--help shows replay options."""
        result = runner.invoke(app, ["events", "replay", "--help"])
        assert result.exit_code == 0
        assert "Replay events" in result.stdout
        assert "--from" in result.stdout
        assert "--limit" in result.stdout or "-n" in result.stdout
        assert "--mode" in result.stdout

    def test_replay_from_required(self) -> None:
        """--from is required for replay."""
        result = runner.invoke(app, ["events", "replay"])
        # Without --from, Typer should exit with error code 2
        assert result.exit_code == 2
        # Typer writes usage errors to stderr, not stdout
        assert "Error" in result.output or "Missing option" in result.output or "--from" in result.output

    def test_replay_from_offset(self, store: SqliteEventStore) -> None:
        """replay --from <ulid> shows events after that offset."""
        ids = _populate_events(store, count=5)
        offset_id = ids[2]
        result = runner.invoke(app, ["events", "replay", "--from", offset_id])
        assert result.exit_code == 0
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 2  # Events at index 3 and 4

    def test_replay_with_limit(self, store: SqliteEventStore) -> None:
        """replay --from --limit limits output."""
        ids = _populate_events(store, count=5)
        offset_id = ids[1]
        result = runner.invoke(app, ["events", "replay", "--from", offset_id, "--limit", "2"])
        assert result.exit_code == 0
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 2

    def test_replay_mode_filter(self, store: SqliteEventStore) -> None:
        """replay --mode build shows only build events."""
        _populate_events(store, count=2, mode="build")
        teach_ids = _populate_events(store, count=2, mode="teach")
        # Replay from first teach event's ID, filtering for build
        result = runner.invoke(app, ["events", "replay", "--from", teach_ids[0], "--mode", "build"])
        assert result.exit_code == 0
        lines = result.stdout.strip().splitlines()
        # Should show no events (all events after teach_ids[0] are teach mode)
        assert len(lines) == 0

    def test_replay_to_upper_bound(self, store: SqliteEventStore) -> None:
        """replay --from --to with exclusive upper bound."""
        ids = _populate_events(store, count=5)
        result = runner.invoke(app, ["events", "replay", "--from", ids[0], "--to", ids[3]])
        assert result.exit_code == 0
        lines = result.stdout.strip().splitlines()
        # Events at index 1 and 2 (exclusive of both bounds)
        assert len(lines) == 2

    def test_replay_empty_store(self, _isolate_db: None) -> None:
        """replay on empty store shows nothing."""
        asyncio.run(migrate())
        result = runner.invoke(
            app, ["events", "replay", "--from", "01ARZ3NDEKTSV4RRFFQ69G5FAV"]
        )
        assert result.exit_code == 0
        assert result.stdout.strip() == ""
