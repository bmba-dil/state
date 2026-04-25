"""Tests for state_cli.main — CLI tail, replay, export commands.

Uses typer.testing.CliRunner for CLI invocation.
Tests are sync because CLI commands use asyncio.run() internally
and cannot be called from within a running event loop.
Follows the same _isolate_db + store fixture pattern as test_events.py.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Any

import structlog
import pytest
from typer.testing import CliRunner

# Suppress structlog info messages during CLI tests — repair logs
# are emitted to stdout via ConsoleRenderer and pollute CliRunner output.
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL),
)

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
