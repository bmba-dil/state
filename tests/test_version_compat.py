"""Tests for state_core.version — version compat negotiation (WRK-13)."""

from __future__ import annotations

from src.state_core.version import (
    PLUGIN_VERSION,
    COMPAT_MAJOR_MINOR,
    HEADER_NAME,
    check_version_compat,
)


class TestCheckVersionCompat:
    """Version handshake validation."""

    def test_compatible_version(self) -> None:
        ok, msg = check_version_compat("0.1.0")
        assert ok is True
        assert msg == "ok"

    def test_compatible_version_patch_diff(self) -> None:
        ok, msg = check_version_compat("0.1.99")
        assert ok is True

    def test_incompatible_version(self) -> None:
        ok, msg = check_version_compat("0.2.0")
        assert ok is False
        assert "incompatible" in msg
        assert "0.2.0" in msg
        assert COMPAT_MAJOR_MINOR in msg

    def test_missing_header_none(self) -> None:
        ok, msg = check_version_compat(None)
        assert ok is False
        assert "missing" in msg.lower() or "Missing" in msg

    def test_missing_header_empty(self) -> None:
        ok, msg = check_version_compat("")
        assert ok is False
        assert "missing" in msg.lower() or "Missing" in msg

    def test_custom_header_name_constant(self) -> None:
        assert HEADER_NAME == "x-state-plugin-version"

    def test_plugin_version_constant(self) -> None:
        assert PLUGIN_VERSION.startswith(COMPAT_MAJOR_MINOR)
