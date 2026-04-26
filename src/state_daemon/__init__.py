"""Daemon package — always-on user service for state."""

from __future__ import annotations

from src.state_daemon.orchestrator import startup

__all__ = ["startup"]
