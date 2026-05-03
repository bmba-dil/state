"""Phase 022 — AUTH-12 Typer command integration tests.

Tests for state_cli.auth Typer sub-app using Typer's CliRunner.
Implemented GREEN in Plan 03 (022-03-PLAN.md).
"""
from __future__ import annotations

import json
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from state_core.auth.base import ApiKeyCredential, OAuthCredential
from state_core.auth.errors import AuthError, UnknownApiKeyProviderError
from state_core.auth.store import AuthVaultPermissionError


def _make_fake_cred(
    provider_id: str = "anthropic",
    key: str = "sk-ant-api03-test-key-not-real",
) -> ApiKeyCredential:
    return ApiKeyCredential(
        provider_id=provider_id,
        key=key,
        extras={"_source": "vault"},
    )


def _make_fake_oauth_cred(
    provider_id: str = "anthropic",
    email: str = "test@example.com",
) -> OAuthCredential:
    return OAuthCredential(
        provider_id=provider_id,
        access="test-access-token-not-real",
        refresh="test-refresh-token-not-real",
        expires=9_999_999_999.0,
        account_id="test-account-id",
        extras={"email_address": email, "_source": "vault"},
    )


def _make_status_report(provider_id: str = "anthropic") -> object:
    """Build a minimal StatusReport for status() tests."""
    from state_core.auth.cli_ops import StatusReport, StatusRow

    row = StatusRow(
        provider_id=provider_id,
        type="api_key",
        account_label="test@example.com",
        expires_at=None,
        expires_in_seconds=None,
        source="vault",
        prefix12="sk-ant-api03",
        is_expired=False,
    )
    return StatusReport(
        providers=[{"id": provider_id, "creds": [{"type": "api_key", "account_label": "test@example.com"}]}],
        rows=[row],
        summary="1 provider(s) configured · 1 credential(s)",
        total_providers=1,
        total_credentials=1,
        total_expired=0,
        total_unknown=0,
    )


# Import auth_app once for all tests (triggers at module collect time)
from src.state_cli.auth import auth_app  # noqa: E402


def test_state_auth_login_exits_64_on_non_tty() -> None:
    """'state auth login anthropic' on non-TTY without --api-key/--code-state/--from-stdin
    exits 64 with message 'refusing interactive login on non-TTY'."""
    runner = CliRunner()
    # CliRunner's input="" simulates a non-TTY (no real stdin); isatty() returns False
    result = runner.invoke(auth_app, ["login", "anthropic"], input="")
    assert result.exit_code == 64
    # Rich Console(stderr=True) writes to stderr; CliRunner merges stdout+stderr
    assert "refusing interactive login on non-TTY" in result.output


def test_state_auth_login_alias_claude_normalizes_to_anthropic() -> None:
    """'state auth login claude --api-key test' resolves 'claude' -> 'anthropic'."""
    runner = CliRunner()
    fake_cred = _make_fake_cred("anthropic", "sk-ant-api03-test")

    with patch(
        "src.state_cli.auth.ops_login",
        new=AsyncMock(return_value=fake_cred),
    ) as mock_login:
        result = runner.invoke(auth_app, ["login", "claude", "--api-key", "sk-ant-api03-test"])

    assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
    # ops_login should be called with provider_id='anthropic' (not 'claude')
    mock_login.assert_called_once()
    call_args = mock_login.call_args
    assert call_args.args[0] == "anthropic", (
        f"provider_id should be 'anthropic', got {call_args.args[0]!r}"
    )


def test_state_auth_login_unknown_provider_exits_64() -> None:
    """'state auth login not-a-provider' exits 64 with did-you-mean suggestion."""
    runner = CliRunner()
    result = runner.invoke(auth_app, ["login", "not-a-provider", "--api-key", "some-key"])
    assert result.exit_code == 64
    # Output should contain either the provider name or "error"
    assert "not-a-provider" in result.output.lower() or "error" in result.output.lower()


def test_state_auth_login_exits_130_on_keyboard_interrupt() -> None:
    """KeyboardInterrupt in login flow yields exit code 130."""
    runner = CliRunner()

    with patch(
        "src.state_cli.auth.ops_login",
        new=AsyncMock(side_effect=KeyboardInterrupt()),
    ):
        result = runner.invoke(auth_app, ["login", "anthropic", "--api-key", "test-key"])

    assert result.exit_code == 130, f"exit_code={result.exit_code}, output={result.output}"


def test_state_auth_login_stealth_rejected_exits_3() -> None:
    """StealthRejected from ops layer yields exit code 3."""
    from state_core.auth.providers.anthropic import StealthRejected
    runner = CliRunner()

    with patch(
        "src.state_cli.auth.ops_login",
        new=AsyncMock(side_effect=StealthRejected("header drift")),
    ):
        result = runner.invoke(auth_app, ["login", "anthropic", "--api-key", "test-key"])

    assert result.exit_code == 3, f"exit_code={result.exit_code}, output={result.output}"


def test_state_auth_login_vault_permission_error_exits_77() -> None:
    """AuthVaultPermissionError from ops layer yields exit code 77."""
    from pathlib import Path
    runner = CliRunner()

    with patch(
        "src.state_cli.auth.ops_login",
        new=AsyncMock(side_effect=AuthVaultPermissionError(Path("/tmp/.state/auth.json"), 0o644)),
    ):
        result = runner.invoke(auth_app, ["login", "anthropic", "--api-key", "test-key"])

    assert result.exit_code == 77, f"exit_code={result.exit_code}, output={result.output}"


def test_state_auth_logout_single_cred_prompts_confirmation() -> None:
    """Single-cred logout prompts 'Remove the only ...' unless --yes supplied."""
    runner = CliRunner()
    fake_cred = _make_fake_cred("anthropic")

    with (
        patch("src.state_cli.auth.get_auth_json_path") as mock_path,
        patch("src.state_cli.auth.load_vault") as mock_load,
        patch("src.state_cli.auth.ops_logout", new=AsyncMock(return_value=1)),
    ):
        mock_vault_path = MagicMock()
        mock_vault_path.exists.return_value = True
        mock_path.return_value = mock_vault_path
        mock_vault = MagicMock()
        mock_vault.providers = {"anthropic": [fake_cred]}
        mock_load.return_value = mock_vault

        # Provide "y" to confirm the prompt
        result = runner.invoke(auth_app, ["logout", "anthropic"], input="y\n")

    assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
    # The prompt should mention "Remove the only"
    assert "Remove the only" in result.output or "only" in result.output.lower()


def test_state_auth_logout_yes_flag_skips_prompt() -> None:
    """logout --yes skips confirmation, exits 0."""
    runner = CliRunner()

    with patch(
        "src.state_cli.auth.ops_logout",
        new=AsyncMock(return_value=1),
    ):
        result = runner.invoke(auth_app, ["logout", "anthropic", "--yes"])

    assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
    assert "Removed 1" in result.output


def test_state_auth_logout_all_flag_requires_yes() -> None:
    """'state auth logout anthropic --all' without --yes prompts confirmation."""
    runner = CliRunner()

    with patch(
        "src.state_cli.auth.ops_logout",
        new=AsyncMock(return_value=2),
    ):
        # Respond "y" to the confirmation
        result = runner.invoke(auth_app, ["logout", "anthropic", "--all"], input="y\n")

    assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
    # Confirmation prompt should mention ALL or "all"
    assert "ALL" in result.output or "all" in result.output.lower() or "All" in result.output


def test_state_auth_status_human_table_5_columns() -> None:
    """'state auth status' renders Rich table with exactly 5 columns:
    provider | type | account | expires | source."""
    runner = CliRunner()
    report = _make_status_report()

    with patch(
        "src.state_cli.auth.ops_status",
        new=AsyncMock(return_value=report),
    ):
        result = runner.invoke(auth_app, ["status"])

    assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
    output = result.output
    # The table header row should contain the 5 column names
    assert "Provider" in output
    assert "Type" in output
    assert "Account" in output
    assert "Expires" in output
    assert "Source" in output


def test_state_auth_status_json_schema_field() -> None:
    """'state auth status --json' output has schema field == 'state.auth.status/v1'."""
    runner = CliRunner()
    report = _make_status_report()

    with patch(
        "src.state_cli.auth.ops_status",
        new=AsyncMock(return_value=report),
    ):
        result = runner.invoke(auth_app, ["status", "--json"])

    assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
    data = json.loads(result.output)
    assert data["schema"] == "state.auth.status/v1"


def test_state_auth_status_provider_filter() -> None:
    """'state auth status --provider anthropic' returns only anthropic rows."""
    runner = CliRunner()
    report = _make_status_report("anthropic")

    with patch(
        "src.state_cli.auth.ops_status",
        new=AsyncMock(return_value=report),
    ) as mock_status:
        result = runner.invoke(auth_app, ["status", "--provider", "anthropic"])

    assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
    # ops_status should be called with provider_id='anthropic'
    mock_status.assert_called_once()
    call_kwargs = mock_status.call_args.kwargs
    assert call_kwargs.get("provider_id") == "anthropic"


def test_state_auth_status_no_color_disables_ansi() -> None:
    """'state auth status --no-color' output contains no ANSI escape sequences."""
    runner = CliRunner()
    report = _make_status_report()

    with patch(
        "src.state_cli.auth.ops_status",
        new=AsyncMock(return_value=report),
    ):
        result = runner.invoke(auth_app, ["status", "--no-color"])

    assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    assert not ansi_escape.search(result.output), (
        f"ANSI escape sequences found in --no-color output: {result.output!r}"
    )


def test_auth_app_registered_in_main() -> None:
    """'state auth --help' succeeds (auth_app is registered in main.py)."""
    from src.state_cli.main import app
    runner = CliRunner()
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0, f"exit_code={result.exit_code}, output={result.output}"
    assert "auth" in result.output.lower() or "login" in result.output.lower()


def test_login_no_arg_shows_picker() -> None:
    """'state auth login' (no arg, TTY) shows 16-row numbered picker.

    4 oauth rows + 12 api_key rows. anthropic appears at both index 0 (oauth)
    and index 4 (api_key). KeyboardInterrupt during prompt exits 130.
    """
    runner = CliRunner()

    # Simulate TTY: mock sys.stdin.isatty() to return True
    with patch("src.state_cli.auth.sys") as mock_sys:
        mock_sys.stdin = MagicMock()
        mock_sys.stdin.isatty.return_value = True

        # Raise KeyboardInterrupt during the numbered prompt
        with patch("typer.prompt", side_effect=KeyboardInterrupt()):
            result = runner.invoke(auth_app, ["login"])

    # KeyboardInterrupt from picker should exit 130
    assert result.exit_code == 130, f"exit_code={result.exit_code}, output={result.output}"

    # The output should show the numbered list (16 rows)
    output = result.output
    assert "Select a provider:" in output
    # anthropic should appear as oauth (index 0)
    assert "[0] anthropic (oauth)" in output
    # anthropic should also appear as api_key (index 4)
    assert "[4] anthropic (api_key)" in output
    # Should have 16 entries total ([0] through [15])
    assert "[15]" in output
