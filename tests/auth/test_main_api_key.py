"""Phase 018 — VALIDATION rows 09–11, 19 (RED scaffolding).

Wave 0 — every test fails on `state_core.auth.providers.api_key._main`
until Wave 1 lands the argparse block.

Tests use isolated_vault_path (sets STATE_AUTH_JSON env override) so
__main__ writes to tmp_path and never touches the real .state/auth.json.

T-018-1 ASVS V8.3.4: keys MUST come from getpass or stdin pipe — never
argv. The login subcommand intentionally rejects --api-key (no flag).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from state_core.auth.base import ApiKeyCredential
from state_core.auth.store import load_vault

# Wave 0: this import fails — that is the RED signal.
from state_core.auth.providers.api_key import _main


# Mirrors EXPECTED_PROVIDER_IDS in test_api_key.py — used by the list subcommand test.
_EXPECTED_PROVIDER_IDS: tuple[str, ...] = (
    "anthropic.api_key",
    "openrouter",
    "openai",
    "anyscale",
    "xai",
    "groq",
    "google.ai_studio",
    "deepseek",
    "together",
    "mistral",
    "cohere",
    "cerebras",
)


# ── VALIDATION row 19 — getpass / stdin only, never argv ─────────────────


def test_login_uses_getpass_or_stdin(
    isolated_vault_path: Path,
    mock_api_key_getpass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VALIDATION row 19 — getpass path; key never appears in argv.

    T-018-1 ASVS V8.3.4 mitigation: argv exposed via /proc/$PID/cmdline
    (Linux) and ps(1) (every POSIX). The login flow MUST read the secret
    from getpass.getpass (or stdin pipe), never argv.
    """
    secret = "sk-test-via-getpass"
    mock_api_key_getpass(secret)
    monkeypatch.setattr(sys, "argv", ["prog", "login", "openai"])

    rc = _main()
    assert rc == 0

    # The secret MUST NOT have been on argv at any point.
    assert all(secret not in arg for arg in sys.argv), (
        f"key leaked into argv: {sys.argv!r}"
    )


def test_login_no_api_key_flag_exists(
    isolated_vault_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-018-1 — argparse MUST reject any --api-key flag (does not exist by design).

    SystemExit(2) is argparse's exit code for usage errors.
    """
    monkeypatch.setattr(
        sys, "argv", ["prog", "login", "openai", "--api-key", "sk-injected"]
    )
    with pytest.raises(SystemExit) as exc_info:
        _main()
    assert exc_info.value.code == 2


def test_login_via_stdin_pipe(
    isolated_vault_path: Path,
    mock_stdin_pipe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VALIDATION row 19 (cont.) — non-TTY stdin path stores the key."""
    monkeypatch.setattr(sys, "argv", ["prog", "login", "openai"])
    mock_stdin_pipe("sk-from-stdin")

    rc = _main()
    assert rc == 0

    vault = load_vault(isolated_vault_path)
    assert "openai" in vault.providers
    assert len(vault.providers["openai"]) == 1
    assert vault.providers["openai"][0].key == "sk-from-stdin"


# ── VALIDATION row 09 — append by default ────────────────────────────────


def test_login_appends_by_default(
    isolated_vault_path: Path,
    mock_api_key_getpass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VALIDATION row 09 — repeat login appends a second credential by default."""
    monkeypatch.setattr(sys, "argv", ["prog", "login", "openai"])

    mock_api_key_getpass("sk-key-1")
    assert _main() == 0

    mock_api_key_getpass("sk-key-2")
    assert _main() == 0

    vault = load_vault(isolated_vault_path)
    assert len(vault.providers["openai"]) == 2
    assert vault.providers["openai"][0].key == "sk-key-1"
    assert vault.providers["openai"][1].key == "sk-key-2"


# ── VALIDATION row 10 — --replace truncates ──────────────────────────────


def test_login_replace_truncates(
    isolated_vault_path: Path,
    mock_api_key_getpass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VALIDATION row 10 — --replace truncates the provider's array to one entry."""
    # First, append "sk-key-1".
    monkeypatch.setattr(sys, "argv", ["prog", "login", "openai"])
    mock_api_key_getpass("sk-key-1")
    assert _main() == 0

    # Then re-login with --replace and "sk-key-2".
    monkeypatch.setattr(sys, "argv", ["prog", "login", "openai", "--replace"])
    mock_api_key_getpass("sk-key-2")
    assert _main() == 0

    vault = load_vault(isolated_vault_path)
    assert len(vault.providers["openai"]) == 1
    assert vault.providers["openai"][0].key == "sk-key-2"


# ── VALIDATION row 11 — dedup on identical key ───────────────────────────


def test_login_dedups_identical_key(
    isolated_vault_path: Path,
    mock_api_key_getpass,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VALIDATION row 11 — identical key string is deduped (single entry)."""
    monkeypatch.setattr(sys, "argv", ["prog", "login", "openai"])

    mock_api_key_getpass("sk-same-key")
    assert _main() == 0

    mock_api_key_getpass("sk-same-key")
    assert _main() == 0

    vault = load_vault(isolated_vault_path)
    assert len(vault.providers["openai"]) == 1
    assert vault.providers["openai"][0].key == "sk-same-key"


# ── Additional tests ─────────────────────────────────────────────────────


def test_login_unknown_provider_fails_at_argparse(
    isolated_vault_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """argparse MUST reject unknown provider via choices=… → SystemExit(2)."""
    monkeypatch.setattr(sys, "argv", ["prog", "login", "not-a-provider"])
    with pytest.raises(SystemExit) as exc_info:
        _main()
    assert exc_info.value.code == 2


def test_keyboard_interrupt_returns_130(
    isolated_vault_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POSIX SIGINT during getpass → exit code 130."""

    def _raise(_prompt: str = "") -> str:
        raise KeyboardInterrupt

    try:
        monkeypatch.setattr(
            "state_core.auth.providers.api_key.getpass.getpass", _raise
        )
        # Force the getpass branch (under pytest, os.isatty(0) is False so
        # login() would otherwise fall through to sys.stdin and OSError on
        # the captured-input replacement).
        monkeypatch.setattr(
            "state_core.auth.providers.api_key.os.isatty", lambda _fd: True
        )
    except (AttributeError, ModuleNotFoundError):
        # Wave 0: module not yet created. The import at the top of this
        # file already fails before this test body executes.
        pass

    monkeypatch.setattr(sys, "argv", ["prog", "login", "openai"])
    rc = _main()
    assert rc == 130


def test_list_subcommand_prints_all_12_providers(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`list` subcommand enumerates all 12 known providers."""
    monkeypatch.setattr(sys, "argv", ["prog", "list"])
    rc = _main()
    assert rc == 0

    captured = capsys.readouterr().out
    for provider_id in _EXPECTED_PROVIDER_IDS:
        assert provider_id in captured, (
            f"provider {provider_id!r} missing from `list` output:\n{captured}"
        )


def test_refresh_subcommand_is_noop_for_api_key(
    isolated_vault_path: Path,
    mock_api_key_getpass,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`refresh` is a no-op for API keys — surfaces a friendly explanation."""
    # Seed an openai key first.
    monkeypatch.setattr(sys, "argv", ["prog", "login", "openai"])
    mock_api_key_getpass("sk-seed")
    assert _main() == 0

    # Then call refresh.
    monkeypatch.setattr(sys, "argv", ["prog", "refresh", "openai"])
    rc = _main()
    assert rc == 0

    out = capsys.readouterr().out.lower()
    assert "api key" in out
    assert "never expire" in out
