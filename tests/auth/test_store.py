"""Tests for state_core.auth.store — the .state/auth.json vault layer.

STORE-01..STORE-21 from
.planning/milestones/v2/phases/012-auth-json-vault-chmod-0600/012-RESEARCH.md
plus a STORE-22 symlink-defense placeholder (deferred to Phase 022 audit).

Owns:
  * AUTH-06 — chmod-0600 verified on every read; refuse-to-proceed on drift
  * P0-13   — mode-permission drift / array-shape collapse
  * P1-7    — array-per-provider shape preserved even for n=1

These tests are RED until Plan 02 lands `state_core.auth.store`. We use a
conditional import + `pytestmark = pytest.mark.skipif(...)` so collection
ALWAYS succeeds; every test is SKIPPED until Plan 02 exposes the public
surface, at which point each must turn GREEN.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

import orjson
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from state_core.auth.base import (
    ApiKeyCredential,  # noqa: F401  (kept for parity with discriminator tests)
    Credential,  # noqa: F401  (re-exported for Plan 02 callers)
    CredentialAdapter,
    OAuthCredential,
)

# ── Conditional import of Plan 02's surface ──────────────────────────────
# Direct ImportError on collection is acceptable RED state, but the preferred
# shape per the plan is collection-passes-then-skips so we get visibility
# into the test catalogue from `--collect-only` without forcing red bars
# that mask actual bugs.

try:
    from state_core.auth.store import (  # type: ignore[import-not-found]
        VAULT_MODE,
        AuthVault,
        AuthVaultPermissionError,
        _atomic_write,
        _verify_mode,  # noqa: F401  (private; tested via load_vault)
        ensure_initialized,
        get_auth_json_path,
        load_vault,
        save_vault,
    )

    _STORE_AVAILABLE = True
    _IMPORT_ERROR: ImportError | None = None
except ImportError as _e:  # pragma: no cover — RED state for Wave 0
    _STORE_AVAILABLE = False
    _IMPORT_ERROR = _e


pytestmark = pytest.mark.skipif(
    not _STORE_AVAILABLE,
    reason=f"Plan 02 not yet landed: {_IMPORT_ERROR}",
)


# ── Helpers ──────────────────────────────────────────────────────────────


def _mode_of(path: Path) -> int:
    """Return the file's mode bits (low 9 bits) for chmod assertions."""
    return os.stat(path).st_mode & 0o777


# ── STORE-01 ─────────────────────────────────────────────────────────────
def test_atomic_write_mode(auth_json_path: Path) -> None:
    """`_atomic_write` produces a 0o600 file (kernel-applied via os.open).

    Single-process proxy for the kernel-applied-mode guarantee: after
    `_atomic_write` returns we MUST observe 0o600 — there is no
    intermediate 0o644 window observable from this thread.
    """
    _atomic_write(auth_json_path, b'{"schema_version": 1}')
    assert auth_json_path.exists()
    assert _mode_of(auth_json_path) == 0o600
    assert VAULT_MODE == 0o600


# ── STORE-02 ─────────────────────────────────────────────────────────────
def test_atomic_write_overwrite_mode(auth_json_path: Path) -> None:
    """`_atomic_write` over a pre-existing 0o644 target results in 0o600.

    `os.replace` preserves the SOURCE inode (the 0o600 tmp file), so the
    destination's prior mode is irrelevant. RESEARCH Pitfall 2.
    """
    auth_json_path.write_bytes(b'{"old": true}')
    os.chmod(auth_json_path, 0o644)
    assert _mode_of(auth_json_path) == 0o644

    _atomic_write(auth_json_path, b'{"schema_version": 1}')

    assert _mode_of(auth_json_path) == 0o600


# ── STORE-03 ─────────────────────────────────────────────────────────────
def test_atomic_write_crash_safety(
    auth_json_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If `os.replace` fails mid-save, the destination is unchanged.

    Atomicity: `os.replace` is the commit point. If it raises, the
    pre-existing target keeps its prior contents — no half-written file.
    """
    auth_json_path.write_bytes(b'{"original": true}')
    os.chmod(auth_json_path, 0o600)
    original_bytes = auth_json_path.read_bytes()

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("simulated crash before atomic rename")

    monkeypatch.setattr("state_core.auth.store.os.replace", boom)

    with pytest.raises(OSError, match="simulated crash"):
        _atomic_write(auth_json_path, b'{"new": true}')

    # Target still holds the original payload; never partially written.
    assert auth_json_path.read_bytes() == original_bytes


# ── STORE-04 ─────────────────────────────────────────────────────────────
def test_load_missing_returns_empty(auth_json_path: Path) -> None:
    """`load_vault` on a missing path returns `AuthVault()` and DOES NOT
    create the file (read is observation-only)."""
    assert not auth_json_path.exists()

    vault = load_vault(auth_json_path)

    assert isinstance(vault, AuthVault)
    assert vault.providers == {}
    assert not auth_json_path.exists()


# ── STORE-05 ─────────────────────────────────────────────────────────────
def test_load_wrong_mode_raises(auth_json_path: Path) -> None:
    """`load_vault` on a 0o644 file raises `AuthVaultPermissionError`
    carrying the offending mode. No auto-fix."""
    _atomic_write(auth_json_path, b'{"schema_version": 1}')
    os.chmod(auth_json_path, 0o644)
    assert _mode_of(auth_json_path) == 0o644

    with pytest.raises(AuthVaultPermissionError) as excinfo:
        load_vault(auth_json_path)

    assert excinfo.value.observed_mode == 0o644
    # Confirm load did NOT silently chmod the file back to 0o600.
    assert _mode_of(auth_json_path) == 0o644


# ── STORE-06 ─────────────────────────────────────────────────────────────
def test_load_round_trip(
    auth_json_path: Path, oauth_cred: OAuthCredential
) -> None:
    """save_vault → load_vault returns a structurally-equal AuthVault."""
    vault = AuthVault(providers={"anthropic": [oauth_cred]})
    save_vault(auth_json_path, vault)

    loaded = load_vault(auth_json_path)

    assert loaded == vault
    assert loaded.model_dump(mode="json") == vault.model_dump(mode="json")


# ── STORE-07 ─────────────────────────────────────────────────────────────
def test_load_empty_file(auth_json_path: Path) -> None:
    """`load_vault` on a 0o600 zero-byte file returns `AuthVault()`.

    Pitfall 3 — empty-file edge case treats absent or empty as first-run.
    """
    _atomic_write(auth_json_path, b"")
    assert _mode_of(auth_json_path) == 0o600
    assert auth_json_path.read_bytes() == b""

    vault = load_vault(auth_json_path)

    assert isinstance(vault, AuthVault)
    assert vault.providers == {}
    assert vault.last_rotation == {}


# ── STORE-08 ─────────────────────────────────────────────────────────────
def test_round_trip_single_cred_array(
    auth_json_path: Path, oauth_cred: OAuthCredential
) -> None:
    """n=1 round-trip: providers[anthropic] is ALWAYS a list, never a dict.

    P0-13 / P1-7 owner test — array-shape preservation is the load-bearing
    invariant.
    """
    vault = AuthVault(providers={"anthropic": [oauth_cred]})
    save_vault(auth_json_path, vault)

    # Inspect raw JSON: providers[anthropic] MUST be a JSON array.
    raw = orjson.loads(auth_json_path.read_bytes())
    assert isinstance(raw["providers"]["anthropic"], list)
    assert len(raw["providers"]["anthropic"]) == 1

    loaded = load_vault(auth_json_path)
    assert isinstance(loaded.providers["anthropic"], list)
    assert len(loaded.providers["anthropic"]) == 1


# ── STORE-09 ─────────────────────────────────────────────────────────────
def test_round_trip_multi_cred(auth_json_path: Path) -> None:
    """n=5 round-trip preserves order across save/load."""
    creds = [
        OAuthCredential(
            access=f"acc-{i}",
            refresh=f"ref-{i}",
            expires=2_000_000_000.0 + i,
            provider_id="anthropic",
            account_id=f"acct-{i}",
        )
        for i in range(5)
    ]
    vault = AuthVault(providers={"anthropic": list(creds)})
    save_vault(auth_json_path, vault)

    loaded = load_vault(auth_json_path)

    assert loaded.providers["anthropic"] == creds
    # Order MUST match — round-robin (Phase 019) depends on stable indices.
    for i, c in enumerate(loaded.providers["anthropic"]):
        assert c.account_id == f"acct-{i}"


# ── STORE-10 ─────────────────────────────────────────────────────────────
def test_validator_coerces_bare_dict(oauth_cred: OAuthCredential) -> None:
    """`AuthVault.model_validate` coerces a bare-dict provider value into
    a 1-element list (P1-7 migration safety net)."""
    bare_oauth_dict = CredentialAdapter.dump_python(oauth_cred, mode="json")
    payload: dict[str, Any] = {
        "schema_version": 1,
        "providers": {"anthropic": bare_oauth_dict},
        "last_rotation": {},
    }

    vault = AuthVault.model_validate(payload)

    assert isinstance(vault.providers["anthropic"], list)
    assert len(vault.providers["anthropic"]) == 1
    assert vault.providers["anthropic"][0].provider_id == "anthropic"


# ── STORE-11 ─────────────────────────────────────────────────────────────
def test_ensure_initialized_creates(auth_json_path: Path) -> None:
    """`ensure_initialized` on missing file creates a 0o600 empty vault."""
    assert not auth_json_path.exists()

    returned = ensure_initialized(auth_json_path)

    assert returned == auth_json_path
    assert auth_json_path.exists()
    assert _mode_of(auth_json_path) == 0o600

    loaded = load_vault(auth_json_path)
    assert loaded.providers == {}
    assert loaded.last_rotation == {}


# ── STORE-12 ─────────────────────────────────────────────────────────────
def test_ensure_initialized_rejects_bad_mode(auth_json_path: Path) -> None:
    """`ensure_initialized` on existing 0o644 file raises
    `AuthVaultPermissionError` AND does NOT chmod (no auto-fix)."""
    _atomic_write(auth_json_path, b'{"schema_version": 1}')
    os.chmod(auth_json_path, 0o644)
    assert _mode_of(auth_json_path) == 0o644

    with pytest.raises(AuthVaultPermissionError) as excinfo:
        ensure_initialized(auth_json_path)

    assert excinfo.value.observed_mode == 0o644
    # Defense against silent auto-fix: mode is unchanged after rejection.
    assert _mode_of(auth_json_path) == 0o644


# ── STORE-13 ─────────────────────────────────────────────────────────────
def test_ensure_initialized_idempotent(auth_json_path: Path) -> None:
    """Calling `ensure_initialized` twice on a valid file is a no-op:
    same path, mode still 0o600, content byte-identical."""
    ensure_initialized(auth_json_path)
    first_bytes = auth_json_path.read_bytes()
    first_mode = _mode_of(auth_json_path)

    ensure_initialized(auth_json_path)

    assert auth_json_path.read_bytes() == first_bytes
    assert _mode_of(auth_json_path) == first_mode == 0o600


# ── STORE-14 ─────────────────────────────────────────────────────────────
def test_path_resolution_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`get_auth_json_path` honors `STATE_AUTH_JSON` when set."""
    custom = tmp_path / "custom.json"
    monkeypatch.setenv("STATE_AUTH_JSON", str(custom))

    resolved = get_auth_json_path()

    assert resolved == custom.resolve()


# ── STORE-15 ─────────────────────────────────────────────────────────────
def test_path_resolution_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default path is `<cwd>/.state/auth.json` when env is unset."""
    monkeypatch.chdir(tmp_path)
    # `clean_state_auth_json_env` autouse fixture already deleted the var.

    resolved = get_auth_json_path()

    assert resolved == tmp_path / ".state" / "auth.json"


# ── STORE-16 ─────────────────────────────────────────────────────────────
def test_permission_error_carries_mode() -> None:
    """`AuthVaultPermissionError` exposes `.path` and `.observed_mode`;
    the message contains the path and the offending mode but NOT any
    credential-shaped substring (defense against credential leak through
    exception text)."""
    p = Path("/x/auth.json")
    exc = AuthVaultPermissionError(p, 0o644)

    assert exc.path == p
    assert exc.observed_mode == 0o644

    msg = str(exc)
    assert str(p) in msg
    # Mode appears in some recognizable form (0o644 / 644).
    assert "0o644" in msg or "644" in msg
    # Credentials must NEVER leak through the exception message.
    assert "sk-ant" not in msg
    assert "sk-ant-oat" not in msg
    assert "sk-ant-api03" not in msg


# ── STORE-17 ─────────────────────────────────────────────────────────────
def test_no_mode_imports() -> None:
    """Importing `state_core.auth.store` MUST NOT pull in `state_build.*`
    or `state_teach.*` (mode-isolation cardinal rule)."""
    # Snapshot BEFORE the reload so we measure the delta caused by reload.
    before = set(sys.modules)

    importlib.reload(importlib.import_module("state_core.auth.store"))

    after = set(sys.modules)
    new = after - before
    leaked = [
        m
        for m in new
        if m.startswith(("state_build.", "state_teach."))
        or m in {"state_build", "state_teach"}
    ]
    assert not leaked, f"state_core.auth.store leaked mode imports: {leaked}"


# ── STORE-18 ─────────────────────────────────────────────────────────────
@settings(
    max_examples=25,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    providers=st.dictionaries(
        st.text(min_size=1, max_size=10).filter(str.isidentifier),
        st.lists(
            st.builds(
                OAuthCredential,
                access=st.text(min_size=1, max_size=20),
                refresh=st.text(min_size=1, max_size=20),
                expires=st.floats(
                    min_value=0.0,
                    max_value=4e9,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                provider_id=st.text(min_size=1, max_size=10),
            ),
            min_size=1,
            max_size=3,
        ),
        max_size=3,
    ),
)
def test_hypothesis_round_trip(
    auth_json_path: Path, providers: dict[str, list[OAuthCredential]]
) -> None:
    """Property: any AuthVault survives save → load → save → load with
    structural equality of the second-load result vs the first-load."""
    vault = AuthVault(providers=providers)

    save_vault(auth_json_path, vault)
    loaded_a = load_vault(auth_json_path)

    save_vault(auth_json_path, loaded_a)
    loaded_b = load_vault(auth_json_path)

    assert loaded_a.model_dump(mode="json") == loaded_b.model_dump(mode="json")


# ── STORE-19 ─────────────────────────────────────────────────────────────
def test_discriminator_preserved(
    auth_json_path: Path, oauth_cred: OAuthCredential
) -> None:
    """A saved `OAuthCredential` loads back as `OAuthCredential` (not
    `ApiKeyCredential`) — discriminator dispatch survives the round-trip."""
    vault = AuthVault(providers={"anthropic": [oauth_cred]})
    save_vault(auth_json_path, vault)

    loaded = load_vault(auth_json_path)
    cred = loaded.providers["anthropic"][0]

    assert cred.type == "oauth"
    assert isinstance(cred, OAuthCredential)
    assert not isinstance(cred, ApiKeyCredential)


# ── STORE-20 ─────────────────────────────────────────────────────────────
def test_deterministic_serialization(
    auth_json_path: Path, oauth_cred: OAuthCredential
) -> None:
    """Calling `save_vault` twice with the same vault produces byte-
    identical files (sorted keys, indent 2)."""
    vault = AuthVault(providers={"anthropic": [oauth_cred]})

    save_vault(auth_json_path, vault)
    first = auth_json_path.read_bytes()

    save_vault(auth_json_path, vault)
    second = auth_json_path.read_bytes()

    assert first == second
    # Sanity: indent-2 + sorted-keys produces non-empty output.
    assert b'"providers"' in first


# ── STORE-21 ─────────────────────────────────────────────────────────────
def test_last_rotation_round_trip(auth_json_path: Path) -> None:
    """`last_rotation: {}` round-trips (default empty dict survives serde).

    Phase 019 mutates this dict in place inside the filelock; storage must
    preserve the field even when no rotations have happened.
    """
    vault = AuthVault()
    assert vault.last_rotation == {}

    save_vault(auth_json_path, vault)
    loaded = load_vault(auth_json_path)

    assert loaded.last_rotation == {}
    # Field round-trips with non-empty content too.
    populated = AuthVault(last_rotation={"anthropic": 3})
    save_vault(auth_json_path, populated)
    loaded2 = load_vault(auth_json_path)
    assert loaded2.last_rotation == {"anthropic": 3}


# ── STORE-22 (placeholder) ───────────────────────────────────────────────
@pytest.mark.skip(
    reason="symlink TOCTOU mitigation deferred to Phase 022 audit"
)
def test_symlink_attack_rejected() -> None:
    """Placeholder — Phase 022 audit will add `O_NOFOLLOW` defense and
    `os.lstat`-based symlink rejection. Visible-but-deferred so the gap
    is traceable in `pytest --collect-only` output."""
    assert True  # Phase 022 owns this.
