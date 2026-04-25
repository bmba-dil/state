"""Tests for state_cli.main — CLI tail, replay, export commands.

Uses typer.testing.CliRunner for CLI invocation.
Follows the same _isolate_db + store fixture pattern as test_events.py.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from src.state_cli.main import app  # noqa: F401 — used by test classes in Tasks 2-5
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
async def store(_isolate_db: None) -> SqliteEventStore:
    """Return a SqliteEventStore with migrations applied."""
    await migrate()
    return SqliteEventStore()


# ── Helpers ────────────────────────────────────────────────────────────────


async def _populate_events(
    store: SqliteEventStore,
    count: int = 5,
    mode: str = "build",
) -> list[str]:
    """Append *count* deterministic events and return their ULIDs."""
    ids: list[str] = []
    for i in range(count):
        id_ = await store.append(
            "step", f"step-{i % 3 + 1}", "state.step.executed",
            {"changes_summary": f"event-{i}"},
            mode=mode,  # type: ignore[arg-type]
        )
        ids.append(id_)
    return ids


def _parse_jsonl_lines(text: str) -> list[dict[str, Any]]:
    """Parse JSONL text into a list of dicts. Skips empty lines."""
    return [json.loads(line) for line in text.strip().splitlines() if line.strip()]
