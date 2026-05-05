"""Tests for state_daemon.logging — daemon structured logging with rotation.

Task 056.1: Logging Configuration Module
Task 056.2: Orchestrator Integration
Task 056.3: Log Rotation Config from Config File
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import structlog

from src.state_daemon.logging import (
    DEFAULT_BACKUP_COUNT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_BYTES,
    DEFAULT_MODE,
    _LEVEL_MAP,
    _load_logging_config,
    configure_daemon_logging,
)
from state_core.observability import install as install_redactor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project_root(tmp_path: Path) -> Path:
    """A temporary project root with an empty .state/ directory."""
    state_dir = tmp_path / ".state"
    state_dir.mkdir()
    return tmp_path


@pytest.fixture
def tmp_log_dir(tmp_path: Path) -> Path:
    """A dedicated temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture(autouse=True)
def _isolate_logging() -> None:
    """Snapshot and restore root logger state around each test.

    structlog.configure() from install() and configure_daemon_logging()
    both mutate global state.  This fixture ensures tests are isolated
    from each other.
    """
    root = logging.getLogger()
    # Save state
    saved_handlers = list(root.handlers)
    saved_level = root.level
    root.handlers.clear()
    root.setLevel(logging.NOTSET)
    yield
    # Restore state
    root.handlers.clear()
    for h in saved_handlers:
        root.addHandler(h)
    root.setLevel(saved_level)


# ---------------------------------------------------------------------------
# Task 056.1 — Logging Configuration Module
# ---------------------------------------------------------------------------


class TestConfigureDaemonLogging:
    """Verify configure_daemon_logging() sets up rotation, redaction, and modes."""

    def test_log_file_is_created(self, tmp_log_dir: Path) -> None:
        """The daemon log file is created on first write."""
        log_file = tmp_log_dir / "daemon.log"
        install_redactor(level=None)
        configure_daemon_logging(log_dir=str(tmp_log_dir), mode="dev")

        # Write a log record through structlog
        test_logger = structlog.get_logger("test.file_created")
        test_logger.info("hello")

        assert log_file.is_file()
        content = log_file.read_text(encoding="utf-8")
        assert "hello" in content

    def test_json_mode_uses_json_renderer(self, tmp_log_dir: Path) -> None:
        """JSON mode outputs JSON lines."""
        log_file = tmp_log_dir / "daemon.log"
        import json

        install_redactor(level=None)
        configure_daemon_logging(log_dir=str(tmp_log_dir), mode="json")

        test_logger = structlog.get_logger("test.json")
        test_logger.info("json_event", key="value")

        content = log_file.read_text(encoding="utf-8").strip()
        # JSON mode outputs one JSON object per line (JSONL).
        # Parse the last line which contains our test event.
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        record = json.loads(lines[-1])
        assert record["event"] == "json_event"
        assert record["key"] == "value"

    def test_dev_mode_uses_console_renderer(self, tmp_log_dir: Path) -> None:
        """Dev mode outputs human-readable text (not JSON)."""
        log_file = tmp_log_dir / "daemon.log"

        install_redactor(level=None)
        configure_daemon_logging(log_dir=str(tmp_log_dir), mode="dev")

        test_logger = structlog.get_logger("test.dev")
        test_logger.info("dev_event", key="value")

        content = log_file.read_text(encoding="utf-8")
        assert "dev_event" in content
        assert "key" in content
        assert "value" in content

    def test_rotation_creates_backup_file(self, tmp_log_dir: Path) -> None:
        """When maxBytes is exceeded, a backup file is created."""
        log_file = tmp_log_dir / "daemon.log"
        # Small maxBytes to trigger rotation quickly.
        install_redactor(level=None)
        configure_daemon_logging(
            log_dir=str(tmp_log_dir),
            mode="dev",
            max_bytes=100,  # very small — triggers after first log line
            backup_count=3,
        )

        test_logger = structlog.get_logger("test.rotation")
        for i in range(10):
            test_logger.info("rotation_test", iteration=i, padding="x" * 200)

        # At least one backup file should exist.
        backup_files = list(tmp_log_dir.glob("daemon.log*"))
        backup_count = len([f for f in backup_files if f.name != "daemon.log"])
        assert backup_count >= 1, f"Expected backup files, found: {backup_files}"

    def test_redactor_filters_tokens(self, tmp_log_dir: Path) -> None:
        """Token redactor filters sensitive values from log output."""
        log_file = tmp_log_dir / "daemon.log"
        canary = "sk-ant-oat-test-" + ("X" * 32)

        install_redactor(level=None)
        configure_daemon_logging(log_dir=str(tmp_log_dir), mode="dev")

        test_logger = structlog.get_logger("test.redact")
        test_logger.info("token_test", token=canary)

        content = log_file.read_text(encoding="utf-8")
        assert "[REDACTED]" in content
        assert canary not in content

    def test_log_directory_is_created_automatically(self, tmp_path: Path) -> None:
        """If the log directory doesn't exist, it is created."""
        log_dir = tmp_path / "auto_created_logs"
        log_file = log_dir / "daemon.log"

        install_redactor(level=None)
        configure_daemon_logging(log_dir=str(log_dir), mode="dev")

        assert log_dir.is_dir()
        # Write something to actually create the log file.
        test_logger = structlog.get_logger("test.auto_create")
        test_logger.info("created")
        assert log_file.is_file()

    def test_stderr_handler_remains(self, tmp_log_dir: Path) -> None:
        """configure_daemon_logging() adds to, not replaces, existing handlers."""
        root = logging.getLogger()

        # Simulate install() having added a StreamHandler.
        install_redactor(level=None)
        handler_count_before = len(root.handlers)

        configure_daemon_logging(log_dir=str(tmp_log_dir), mode="dev")
        handler_count_after = len(root.handlers)

        # At least one new handler (RotatingFileHandler) was added.
        assert handler_count_after > handler_count_before


# ---------------------------------------------------------------------------
# Task 056.3 — Log Rotation Config from Config File
# ---------------------------------------------------------------------------


class TestLoadLoggingConfig:
    """Verify config loading from .state/config.toml [daemon.logging]."""

    def test_defaults_when_no_config_file(self, tmp_path: Path) -> None:
        """Returns defaults when config file is missing."""
        cfg = _load_logging_config(tmp_path)
        assert cfg["level"] == DEFAULT_LOG_LEVEL
        assert cfg["max_bytes"] == DEFAULT_MAX_BYTES
        assert cfg["backup_count"] == DEFAULT_BACKUP_COUNT
        assert cfg["mode"] == DEFAULT_MODE

    def test_defaults_when_section_absent(self, tmp_project_root: Path) -> None:
        """Returns defaults when [daemon.logging] section is absent."""
        config_dir = tmp_project_root / ".state"
        config_file = config_dir / "config.toml"
        config_file.write_text("[other]\nkey = \"val\"\n", encoding="utf-8")

        cfg = _load_logging_config(tmp_project_root)
        assert cfg["level"] == DEFAULT_LOG_LEVEL

    def test_reads_values_from_config_file(self, tmp_project_root: Path) -> None:
        """Values from [daemon.logging] override defaults."""
        config_dir = tmp_project_root / ".state"
        config_file = config_dir / "config.toml"
        config_file.write_text(
            "[daemon.logging]\n"
            "level = \"debug\"\n"
            "max_bytes = 5242880\n"
            "backup_count = 3\n"
            "mode = \"json\"\n",
            encoding="utf-8",
        )

        cfg = _load_logging_config(tmp_project_root)
        assert cfg["level"] == "debug"
        assert cfg["max_bytes"] == 5242880
        assert cfg["backup_count"] == 3
        assert cfg["mode"] == "json"

    def test_partial_config_preserves_defaults(self, tmp_project_root: Path) -> None:
        """Missing keys in config file fall back to defaults."""
        config_dir = tmp_project_root / ".state"
        config_file = config_dir / "config.toml"
        config_file.write_text(
            "[daemon.logging]\n"
            "level = \"error\"\n",
            encoding="utf-8",
        )

        cfg = _load_logging_config(tmp_project_root)
        assert cfg["level"] == "error"
        assert cfg["max_bytes"] == DEFAULT_MAX_BYTES  # unchanged
        assert cfg["backup_count"] == DEFAULT_BACKUP_COUNT  # unchanged
        assert cfg["mode"] == DEFAULT_MODE  # unchanged

    def test_config_override_parameters(self, tmp_log_dir: Path) -> None:
        """Explicit parameters to configure_daemon_logging() override config file."""
        install_redactor(level=None)
        configure_daemon_logging(
            log_dir=str(tmp_log_dir),
            mode="json",
            max_bytes=500_000,
            backup_count=2,
            log_level="error",
        )
        # Check that the handler was configured correctly by inspecting the root logger.
        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(file_handlers) >= 1
        handler = file_handlers[-1]
        assert handler.maxBytes == 500_000
        assert handler.backupCount == 2
        assert handler.level == logging.ERROR

    def test_invalid_toml_falls_back_to_defaults(self, tmp_project_root: Path) -> None:
        """Malformed TOML does not crash — defaults are used."""
        config_dir = tmp_project_root / ".state"
        config_file = config_dir / "config.toml"
        config_file.write_text("this is not valid toml {{{", encoding="utf-8")

        cfg = _load_logging_config(tmp_project_root)
        assert cfg["level"] == DEFAULT_LOG_LEVEL

    def test_level_map_coverage(self) -> None:
        """_LEVEL_MAP contains the expected levels."""
        assert _LEVEL_MAP["debug"] == logging.DEBUG
        assert _LEVEL_MAP["info"] == logging.INFO
        assert _LEVEL_MAP["warning"] == logging.WARNING
        assert _LEVEL_MAP["error"] == logging.ERROR


# ---------------------------------------------------------------------------
# Task 056.2 — Orchestrator Integration
# ---------------------------------------------------------------------------


class TestOrchestratorIntegration:
    """Verify logging is wired into the orchestrator startup sequence."""

    def test_startup_logs_configuration(
        self, tmp_path: Path, tmp_log_dir: Path,
    ) -> None:
        """Calling configure_daemon_logging() produces the expected log entry."""
        import io

        install_redactor(level=None)
        configure_daemon_logging(log_dir=str(tmp_log_dir), mode="dev")

        log_file = tmp_log_dir / "daemon.log"
        assert log_file.is_file()

        content = log_file.read_text(encoding="utf-8")
        assert "daemon.logging.configured" in content
        assert str(tmp_log_dir) in content
