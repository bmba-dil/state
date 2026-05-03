"""Phase 018 — VALIDATION rows 04–08 (RED scaffolding).

Wave 0 — every test fails on `from state_core.auth.loader import …`
until Wave 2 lands `state_core/auth/loader.py`.

Vault×env precedence matrix:

    | vault   | env     | result                          |
    |---------|---------|---------------------------------|
    | non-empty | any   | vault wins (row 04)             |
    | empty   | set     | env synthesizes (row 05)        |
    | missing | set     | env synthesizes (row 06)        |
    | missing | unset   | empty list, no error (row 07)   |
    | any     | empty   | env treated as unset (row 08)   |
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from state_core.auth.base import ApiKeyCredential
from state_core.auth.errors import UnknownApiKeyProviderError
from state_core.auth.store import AuthVault, AuthVaultPermissionError, save_vault

# Wave 0: this import fails — that is the RED signal.
from state_core.auth.loader import load_credentials


# ── VALIDATION row 04 — vault wins over env ──────────────────────────────


def test_vault_wins_over_env(
    isolated_vault_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VALIDATION row 04 — vault non-empty wins; env ignored."""
    vault = AuthVault(
        providers={
            "openai": [ApiKeyCredential(key="VAULT-KEY", provider_id="openai")],
        }
    )
    save_vault(isolated_vault_path, vault)
    monkeypatch.setenv("OPENAI_API_KEY", "ENV-KEY")

    creds = load_credentials("openai")
    assert len(creds) == 1
    assert creds[0].key == "VAULT-KEY"


# ── VALIDATION row 05 — vault empty, env synthesizes ─────────────────────


def test_env_synthesizes_when_vault_empty(
    isolated_vault_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VALIDATION row 05 — vault file exists but no openai bucket; env synthesizes.

    T-018-10 mitigation: synthesizing from env MUST NOT mutate the vault file.
    """
    vault = AuthVault(providers={})
    save_vault(isolated_vault_path, vault)
    monkeypatch.setenv("OPENAI_API_KEY", "ENV-KEY")

    creds = load_credentials("openai")
    assert len(creds) == 1
    assert creds[0].key == "ENV-KEY"
    assert creds[0].provider_id == "openai"

    # Vault file must remain untouched after synth.
    from state_core.auth.store import load_vault as _reload

    after = _reload(isolated_vault_path)
    assert after.providers == {}


# ── VALIDATION row 06 — vault missing, env synthesizes ───────────────────


def test_env_synthesizes_when_vault_missing(
    isolated_vault_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VALIDATION row 06 — vault file does not exist; env synthesizes.

    Loader MUST handle FileNotFoundError identically to "missing bucket".
    Loader MUST NOT create the vault file as a side-effect.
    """
    # isolated_vault_path is created with parent dir but file does not exist.
    if isolated_vault_path.exists():
        isolated_vault_path.unlink()
    monkeypatch.setenv("OPENAI_API_KEY", "ENV-KEY")

    creds = load_credentials("openai")
    assert len(creds) == 1
    assert creds[0].key == "ENV-KEY"
    assert creds[0].provider_id == "openai"

    assert not isolated_vault_path.exists(), (
        "loader must not create the vault file when synthesizing from env"
    )


# ── VALIDATION row 07 — empty list when nothing anywhere ─────────────────


def test_returns_empty_when_no_creds_anywhere(
    isolated_vault_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """VALIDATION row 07 — vault missing + env unset → empty list, no error."""
    if isolated_vault_path.exists():
        isolated_vault_path.unlink()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    creds = load_credentials("openai")
    assert creds == []


# ── VALIDATION row 08 — empty env treated as unset ───────────────────────


@pytest.mark.parametrize("env_value", ["", "   ", "\t", "\n"])
def test_empty_env_treated_as_unset(
    env_value: str,
    isolated_vault_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VALIDATION row 08 — empty / whitespace env var counts as unset (12-factor)."""
    if isolated_vault_path.exists():
        isolated_vault_path.unlink()
    monkeypatch.setenv("OPENAI_API_KEY", env_value)

    assert load_credentials("openai") == []


# ── Additional tests (RESEARCH §Test Scaffolding test_loader.py) ─────────


def test_loader_unknown_provider_id_raises(
    isolated_vault_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loader MUST proxy the registry lookup; unknown provider raises."""
    with pytest.raises(UnknownApiKeyProviderError):
        load_credentials("not-a-real-provider")


@pytest.mark.skipif(os.name != "posix", reason="POSIX-only mode bits")
def test_loader_propagates_vault_permission_error(
    isolated_vault_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-018-6 mitigation — wrong-mode vault file propagates as AuthVaultPermissionError.

    The loader MUST NOT silently fall back to env when the vault file is
    present-but-wrong-mode; that would mask a security incident.
    """
    isolated_vault_path.write_bytes(b"{}")
    os.chmod(isolated_vault_path, 0o644)

    with pytest.raises(AuthVaultPermissionError):
        load_credentials("openai")


# ── T-018-5 mitigation: cross-provider env-var leak ──────────────────────

# Each provider's canonical env var name — must match
# state_core.auth.providers.api_key._REGISTRY[pid].env_var byte-for-byte.
# See Plan 02 SUMMARY: google.ai_studio canonicalizes on GEMINI_API_KEY
# (not GOOGLE_API_KEY — the wave-0 stub had the wrong name; Phase 022 may
# alias GOOGLE_API_KEY if pain materializes).
_PROVIDER_ENV_VARS: dict[str, str] = {
    "anthropic.api_key": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google.ai_studio": "GEMINI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "xai": "XAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "anyscale": "ANYSCALE_API_KEY",
    "cohere": "COHERE_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "together": "TOGETHER_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
}


@pytest.mark.parametrize("provider_id", list(_PROVIDER_ENV_VARS.keys()))
def test_loader_consults_only_matching_env_var(
    provider_id: str,
    isolated_vault_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-018-5 mitigation — each provider reads ONLY its own canonical env var.

    Sub-A: setting only this provider's env var produces exactly one cred.
    Sub-B: unsetting this provider's env var while setting all others
    produces an empty list (no cross-provider leak).
    """
    # Clear vault file and ALL canonical env vars to start clean.
    if isolated_vault_path.exists():
        isolated_vault_path.unlink()
    for env_name in _PROVIDER_ENV_VARS.values():
        monkeypatch.delenv(env_name, raising=False)

    own_env_name = _PROVIDER_ENV_VARS[provider_id]

    # Sub-A: only this provider's env var is set.
    monkeypatch.setenv(own_env_name, "OWN-KEY")
    creds = load_credentials(provider_id)
    assert len(creds) == 1
    assert creds[0].key == "OWN-KEY"

    # Sub-B: unset own, set all others, expect empty.
    monkeypatch.delenv(own_env_name, raising=False)
    for other_id, other_env in _PROVIDER_ENV_VARS.items():
        if other_id == provider_id:
            continue
        monkeypatch.setenv(other_env, "OTHER-KEY")

    creds_after = load_credentials(provider_id)
    assert creds_after == [], (
        f"{provider_id} leaked from a sibling env var: {creds_after!r}"
    )
