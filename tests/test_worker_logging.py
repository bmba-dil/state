"""Tests for state_worker.logging — per-worker log configuration (Phase 066)."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path


class TestConfigureWorkerLogging:
    """Worker logging configuration."""

    def test_creates_log_file(self) -> None:
        from src.state_worker.logging import configure_worker_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = configure_worker_logging(
                session_id="test-session-001",
                project_root=tmpdir,
            )

            assert os.path.isfile(log_path)
            assert "worker-test-session-001.log" in log_path

    def test_handler_added_to_root_logger(self) -> None:
        from src.state_worker.logging import configure_worker_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            handler_count_before = len(logging.getLogger().handlers)

            log_path = configure_worker_logging(
                session_id="test-handler",
                project_root=tmpdir,
            )

            handler_count_after = len(logging.getLogger().handlers)
            assert handler_count_after == handler_count_before + 1

            # The new handler should be a RotatingFileHandler.
            assert any(
                isinstance(h, logging.handlers.RotatingFileHandler)
                and str(log_path) in str(h.baseFilename)
                for h in logging.getLogger().handlers
            )

    def test_session_id_sanitized(self) -> None:
        from src.state_worker.logging import configure_worker_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = configure_worker_logging(
                session_id="STATE-12345/evil",
                project_root=tmpdir,
            )

            # Slashes replaced with underscores; hyphens preserved.
            assert "worker-STATE-12345_evil.log" in log_path

    def test_log_dir_created(self) -> None:
        from src.state_worker.logging import configure_worker_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / ".state" / "logs"
            assert not log_dir.exists()

            configure_worker_logging(
                session_id="test-dir",
                project_root=tmpdir,
            )

            assert log_dir.is_dir()
