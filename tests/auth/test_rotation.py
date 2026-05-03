"""Phase 019 — VALIDATION rows ROTATE-01..ROTATE-26 (RED scaffolding).

Wave 0 — every test in this file MUST FAIL until Wave 2 (Plan 02) lands
`state_core.auth.errors.NoCredentialsAvailableError` AND Wave 3 (Plan 03)
lands `state_core.auth.rotation`. Failure modes:
  * ImportError on the top-level `from state_core.auth.rotation import …`
  * AttributeError on test bodies referencing not-yet-existent attributes
  * AssertionError when stub returns a placeholder value

See 019-RESEARCH.md §Validation Architecture for the row→test mapping.

ROTATE-21 lives in tests/auth/test_import_graph.py (mode-isolation lint).
"""

from __future__ import annotations

import asyncio
import importlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

import filelock
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from state_core.auth.base import ApiKeyCredential, OAuthCredential
from state_core.auth.refresh import (
    RefreshLockTimeout,
    _lock_path_for,
    _new_async_lock,
)
from state_core.auth.store import AuthVault, load_vault, save_vault

# The next imports WILL FAIL in Wave 0. That is the RED signal.
# rotation comes first so collection ImportError surfaces state_core.auth.rotation.
from state_core.auth.rotation import (  # Wave 3 (Plan 03)
    BUCKET_MS,
    _bucket_index,
    _COOL_DOWN,
    clear_rate_limited,
    iter_active_credentials,
    mark_rate_limited,
    save_vault as _rotation_save_vault,  # noqa: F401 — used by ROTATE-22 spy install path
    select_credential,
)
from state_core.auth.errors import NoCredentialsAvailableError  # Wave 2 (Plan 02)

if TYPE_CHECKING:
    from collections.abc import Iterator


# Frozen `now` for deterministic bucket math. Year 2026.
NOW_FROZEN: float = 1_770_000_000.0


# ── ROTATE-01 ─────────────────────────────────────────────────────────────


async def test_select_n1_returns_idx0_and_bumps(isolated_vault_path: Path) -> None:
    """ROTATE-01 — n=1 vault returns idx 0 and last_rotation rolls to 0 modulo n."""
    vault = AuthVault(
        providers={
            "anthropic": [
                OAuthCredential(
                    access="sk-ant-oat-TEST-only",
                    refresh="rt-TEST-only",
                    expires=NOW_FROZEN + 86400.0,
                    provider_id="anthropic",
                    account_id="acct-TEST-only",
                )
            ],
        },
        last_rotation={"anthropic": 0},
    )
    save_vault(isolated_vault_path, vault)

    idx, cred = await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
    )
    assert idx == 0
    assert cred.provider_id == "anthropic"

    reloaded = load_vault(isolated_vault_path)
    # (0 + 1) % 1 == 0
    assert reloaded.last_rotation["anthropic"] == 0


# ── ROTATE-02 ─────────────────────────────────────────────────────────────


async def test_select_empty_raises(isolated_vault_path: Path) -> None:
    """ROTATE-02 — empty list raises NoCredentialsAvailableError(reason='empty')."""
    save_vault(isolated_vault_path, AuthVault(providers={"anthropic": []}))

    with pytest.raises(NoCredentialsAvailableError) as exc_info:
        await select_credential(
            "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
        )

    assert exc_info.value.reason == "empty"
    assert exc_info.value.provider_id == "anthropic"


# ── ROTATE-03 ─────────────────────────────────────────────────────────────


async def test_select_missing_provider_raises(isolated_vault_path: Path) -> None:
    """ROTATE-03 — missing provider key raises NoCredentialsAvailableError."""
    save_vault(isolated_vault_path, AuthVault())

    with pytest.raises(NoCredentialsAvailableError) as exc_info:
        await select_credential(
            "openai", vault_path=isolated_vault_path, now=NOW_FROZEN
        )

    assert exc_info.value.reason == "empty"
    assert exc_info.value.provider_id == "openai"


# ── ROTATE-04 ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("now_offset_ms", [0, 60_000, 120_000, 180_000])
async def test_bucket_advances_with_time(
    now_offset_ms: int,
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-04 — wall-clock advance walks bucket idx; pure helper proves +1."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    indices: list[int] = []
    for offset in (0, 60_000, 120_000, 180_000):
        save_vault(isolated_vault_path, vault_with_three_oauth)  # reset state
        idx, _ = await select_credential(
            "anthropic",
            vault_path=isolated_vault_path,
            now=NOW_FROZEN + offset / 1000,
        )
        indices.append(idx)

    # We saw at least 2 distinct bucket indices across 4 advances.
    assert len({*indices}) >= 2

    # Pure helper: +60s ⇒ +1 bucket modulo n.
    base = _bucket_index(NOW_FROZEN, n=3, seed=0)
    advanced = _bucket_index(NOW_FROZEN + 60.0, n=3, seed=0)
    assert (advanced - base) % 3 == 1

    # Use the parametrized argument so pytest doesn't flag it unused.
    _ = now_offset_ms


# ── ROTATE-05 ─────────────────────────────────────────────────────────────


async def test_last_rotation_persisted(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-05 — last_rotation written to disk after select; survives reload."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
    )

    reloaded = load_vault(isolated_vault_path)
    # (0 + 1) % 3 == 1
    assert reloaded.last_rotation["anthropic"] == 1

    # Reload AGAIN — proves disk roundtrip, not in-memory caching.
    reloaded_again = load_vault(isolated_vault_path)
    assert reloaded_again.last_rotation["anthropic"] == 1


# ── ROTATE-06 ─────────────────────────────────────────────────────────────


async def test_array_shape_preserved_after_selection(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-06 — providers[anthropic] is still a list of 3 after selection (P1-7)."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
    )

    reloaded = load_vault(isolated_vault_path)
    assert isinstance(reloaded.providers["anthropic"], list)
    assert len(reloaded.providers["anthropic"]) == 3


# ── ROTATE-07 ─────────────────────────────────────────────────────────────


async def test_cool_down_skipped_on_next_selection(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-07 — cool-down idx is skipped; selector chooses a different active."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    start = _bucket_index(NOW_FROZEN, n=3, seed=0)
    mark_rate_limited("anthropic", start, until=NOW_FROZEN + 60.0)

    idx, _ = await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
    )
    assert idx != start
    assert idx in {0, 1, 2}


# ── ROTATE-08 ─────────────────────────────────────────────────────────────


async def test_cool_down_auto_expires(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-08 — cool-down past `until` is GC'd from _COOL_DOWN; idx selectable."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    mark_rate_limited("anthropic", 0, until=NOW_FROZEN + 60.0)

    # Inside cool-down window: idx 0 not selected.
    idx_active, _ = await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN + 30.0
    )
    assert idx_active != 0

    # Reset persisted last_rotation so the bucket math is clean.
    save_vault(isolated_vault_path, vault_with_three_oauth)

    # Past cool-down: idx 0 is allowed AND map is GC'd.
    await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN + 90.0
    )
    assert ("anthropic", 0) not in _COOL_DOWN


# ── ROTATE-09 ─────────────────────────────────────────────────────────────


async def test_all_cooled_down_raises_with_earliest(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-09 — all cooled down ⇒ NoCredentialsAvailableError(earliest_available_at)."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    mark_rate_limited("anthropic", 0, until=NOW_FROZEN + 30.0)
    mark_rate_limited("anthropic", 1, until=NOW_FROZEN + 60.0)
    mark_rate_limited("anthropic", 2, until=NOW_FROZEN + 90.0)

    with pytest.raises(NoCredentialsAvailableError) as exc_info:
        await select_credential(
            "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
        )

    assert exc_info.value.reason == "all_cooled_down"
    assert exc_info.value.earliest_available_at == NOW_FROZEN + 30.0
    assert exc_info.value.provider_id == "anthropic"

    # T-019-3 (ASVS V8.3.1) — exception message must NOT leak access tokens.
    rendered = str(exc_info.value)
    assert "anthropic" in rendered
    assert "sk-ant-oat-TEST-" not in rendered


# ── ROTATE-10 ─────────────────────────────────────────────────────────────


async def test_clear_rate_limited_removes_entry(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-10 — clear_rate_limited(provider, idx) removes the cool-down entry."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    start = _bucket_index(NOW_FROZEN, n=3, seed=0)
    mark_rate_limited("anthropic", start, until=NOW_FROZEN + 60.0)
    clear_rate_limited("anthropic", start)

    idx, _ = await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
    )
    assert idx == start


# ── ROTATE-11 ─────────────────────────────────────────────────────────────


async def test_last_rotation_modulo_clamp(isolated_vault_path: Path) -> None:
    """ROTATE-11 — seed >= len(creds) is clamped via modulo; no IndexError."""
    vault = AuthVault(
        providers={
            "openai": [
                ApiKeyCredential(key="TEST-A", provider_id="openai"),
                ApiKeyCredential(key="TEST-B", provider_id="openai"),
            ],
        },
        last_rotation={"openai": 99},
    )
    save_vault(isolated_vault_path, vault)

    idx, _ = await select_credential(
        "openai", vault_path=isolated_vault_path, now=NOW_FROZEN
    )
    assert idx in {0, 1}

    reloaded = load_vault(isolated_vault_path)
    assert 0 <= reloaded.last_rotation["openai"] < 2


# ── ROTATE-12 ─────────────────────────────────────────────────────────────


def test_mark_zero_until_clears() -> None:
    """ROTATE-12 — mark_rate_limited(..., until=0) clears the entry."""
    mark_rate_limited("anthropic", 0, until=NOW_FROZEN + 60.0)
    assert ("anthropic", 0) in _COOL_DOWN

    mark_rate_limited("anthropic", 0, until=0)
    assert ("anthropic", 0) not in _COOL_DOWN


# ── ROTATE-13 ─────────────────────────────────────────────────────────────


async def test_bare_dict_coerced_p1_7(isolated_vault_path: Path) -> None:
    """ROTATE-13 — bare-dict on disk is coerced to a single-element list (Phase 012 P1-7)."""
    payload = (
        b'{"schema_version": 1, '
        b'"providers": {"openai": {"type": "api_key", "key": "TEST-K", '
        b'"provider_id": "openai", "extras": {}}}, '
        b'"last_rotation": {}}'
    )
    fd = os.open(
        str(isolated_vault_path),
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)

    idx, cred = await select_credential(
        "openai", vault_path=isolated_vault_path, now=NOW_FROZEN
    )
    assert idx == 0
    assert isinstance(cred, ApiKeyCredential)
    assert cred.key == "TEST-K"


# ── ROTATE-14 ─────────────────────────────────────────────────────────────


async def test_migration_preserves_last_rotation(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-14 — last_rotation seeded to 2 advances to 0 = (2+1) % 3."""
    seeded = vault_with_three_oauth.model_copy(
        update={"last_rotation": {"anthropic": 2}}
    )
    save_vault(isolated_vault_path, seeded)

    await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
    )

    reloaded = load_vault(isolated_vault_path)
    assert isinstance(reloaded.providers["anthropic"], list)
    assert len(reloaded.providers["anthropic"]) == 3
    assert reloaded.last_rotation["anthropic"] == (2 + 1) % 3 == 0


# ── ROTATE-15 ─────────────────────────────────────────────────────────────


def test_cool_down_lost_on_module_reimport() -> None:
    """ROTATE-15 — _COOL_DOWN is process-local; importlib.reload yields {} (daemon-restart sema)."""
    mark_rate_limited("anthropic", 0, until=NOW_FROZEN + 60.0)
    assert ("anthropic", 0) in _COOL_DOWN

    from state_core.auth import rotation

    importlib.reload(rotation)

    assert rotation._COOL_DOWN == {}


# ── ROTATE-16 ─────────────────────────────────────────────────────────────


def test_iter_active_yields_bucket_order(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-16 — iter_active_credentials yields all idx in bucket order."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    pairs = list(
        iter_active_credentials(
            "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
        )
    )

    assert len(pairs) == 3
    indices = [idx for idx, _ in pairs]
    assert sorted(indices) == [0, 1, 2]
    assert indices[0] == _bucket_index(NOW_FROZEN, 3, 0)


# ── ROTATE-17 ─────────────────────────────────────────────────────────────


def test_iter_active_skips_cool_down(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-17 — iter_active_credentials filters out cooled-down indices."""
    save_vault(isolated_vault_path, vault_with_three_oauth)
    mark_rate_limited("anthropic", 1, until=NOW_FROZEN + 60.0)

    pairs = list(
        iter_active_credentials(
            "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
        )
    )

    assert len(pairs) == 2
    assert 1 not in [idx for idx, _ in pairs]


# ── ROTATE-18 ─────────────────────────────────────────────────────────────


def test_iter_active_does_not_lock(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-18 — iter_active_credentials does NOT acquire the refresh lock."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    lock_path = _lock_path_for(isolated_vault_path)
    sync_lock = filelock.FileLock(str(lock_path), timeout=0)
    sync_lock.acquire()
    try:
        pairs = list(
            iter_active_credentials(
                "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
            )
        )
        assert len(pairs) == 3
    finally:
        try:
            sync_lock.release()
        except Exception:
            pass


# ── ROTATE-19 ─────────────────────────────────────────────────────────────


async def test_select_lock_timeout_raises(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
    busy_lock_holder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ROTATE-19 — when another holder owns the lock, select raises RefreshLockTimeout."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    # Patch the lock factory so all newly constructed locks have a tight timeout.
    from state_core.auth import refresh as _refresh_mod

    # Re-resolve RefreshLockTimeout against the live refresh module — Phase 013's
    # REFRESH-23 (`test_no_mode_imports`) reloads state_core.auth.refresh, which
    # creates a NEW class object. The top-level import on line 29 captured the
    # ORIGINAL class; if test_no_mode_imports already ran in this session, the
    # rotation.py implementation raises the post-reload class while
    # `pytest.raises(RefreshLockTimeout)` would check against the stale one.
    # (Phase 019 Wave 3 — see 019-03-SUMMARY.md "Deviations".)
    _LiveRefreshLockTimeout = _refresh_mod.RefreshLockTimeout

    _orig_factory = _refresh_mod._new_async_lock

    def _short_factory(vault_path: Path):
        lock_path = _lock_path_for(vault_path)
        return filelock.AsyncFileLock(str(lock_path), timeout=0.5)

    monkeypatch.setattr(_refresh_mod, "_new_async_lock", _short_factory)
    monkeypatch.setattr(
        "state_core.auth.rotation._new_async_lock",
        _short_factory,
        raising=False,
    )

    async with busy_lock_holder(isolated_vault_path):
        # The fixture used the original (timeout=10) lock to hold; our patched
        # factory will be used by select_credential → must timeout fast.
        with pytest.raises(_LiveRefreshLockTimeout):
            # Fence as a separate task so AsyncFileLock can race.
            await asyncio.wait_for(
                select_credential(
                    "anthropic",
                    vault_path=isolated_vault_path,
                    now=NOW_FROZEN,
                ),
                timeout=5.0,
            )

    # restore (monkeypatch will also restore at teardown)
    monkeypatch.setattr(_refresh_mod, "_new_async_lock", _orig_factory)


# ── ROTATE-20 ─────────────────────────────────────────────────────────────


async def test_select_reentrant_deadlock_raises(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
    busy_lock_holder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ROTATE-20 — same coroutine holding the lock then calling select deadlocks → timeout."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    # Re-resolve RefreshLockTimeout against the live refresh module — see
    # ROTATE-19 comment for the REFRESH-23 reload interaction rationale.
    from state_core.auth import refresh as _refresh_mod

    _LiveRefreshLockTimeout = _refresh_mod.RefreshLockTimeout

    def _short_factory(vault_path: Path):
        lock_path = _lock_path_for(vault_path)
        return filelock.AsyncFileLock(str(lock_path), timeout=0.5)

    monkeypatch.setattr(
        "state_core.auth.refresh._new_async_lock",
        _short_factory,
    )
    monkeypatch.setattr(
        "state_core.auth.rotation._new_async_lock",
        _short_factory,
        raising=False,
    )

    async with busy_lock_holder(isolated_vault_path):
        with pytest.raises(_LiveRefreshLockTimeout):
            await asyncio.wait_for(
                select_credential(
                    "anthropic",
                    vault_path=isolated_vault_path,
                    now=NOW_FROZEN,
                ),
                timeout=5.0,
            )


# ── ROTATE-22 ─────────────────────────────────────────────────────────────


async def test_select_calls_save_vault_once(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ROTATE-22 — select_credential persists exactly once per call."""
    save_vault(isolated_vault_path, vault_with_three_oauth)

    from state_core.auth import rotation as _rotation_mod
    from state_core.auth import store as _store_mod

    calls: list[Path] = []
    real_save = _store_mod.save_vault

    def _spy(path: Path, vault: AuthVault) -> None:
        calls.append(path)
        real_save(path, vault)

    # rotation.py imports save_vault locally; patch its bound name.
    monkeypatch.setattr(_rotation_mod, "save_vault", _spy)

    await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
    )

    # Filter for our isolated vault path (ignore unrelated saves if any).
    matching = [c for c in calls if c == isolated_vault_path]
    assert len(matching) == 1


# ── ROTATE-23 ─────────────────────────────────────────────────────────────


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    n=st.integers(min_value=2, max_value=8),
    rounds_multiplier=st.integers(min_value=10, max_value=30),
)
async def test_every_cred_selected_over_n_rounds(
    n: int,
    rounds_multiplier: int,
    isolated_vault_path: Path,
) -> None:
    """ROTATE-23 (hypothesis) — every credential gets selected over n*k rounds."""
    vault = AuthVault(
        providers={
            "openai": [
                ApiKeyCredential(key=f"TEST-key-{i}", provider_id="openai")
                for i in range(n)
            ],
        },
        last_rotation={"openai": 0},
    )
    save_vault(isolated_vault_path, vault)

    seen: set[int] = set()
    # Time step is held constant (within one bucket) so this test exercises
    # SEED-DRIVEN coverage independently of bucket-driven coverage. Using
    # a per-call clock advance equal to the bucket width (60.0s) would
    # combine bucket-advance-by-1 with seed-advance-by-1, yielding
    # `idx_k = (B + 2k) % n` — coverage fails for even n via gcd(2, n) > 1
    # under the canonical `(bucket + seed) % n` formula. ROTATE-04 covers
    # the bucket-advances-with-time property as a separate helper test.
    # (Phase 019 Wave 3 — see 019-03-SUMMARY.md "Deviations".)
    for k in range(n * rounds_multiplier):
        idx, _ = await select_credential(
            "openai",
            vault_path=isolated_vault_path,
            now=NOW_FROZEN,
        )
        seen.add(idx)

    assert seen == set(range(n))


# ── ROTATE-24 ─────────────────────────────────────────────────────────────


@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    n=st.integers(min_value=1, max_value=8),
    seed=st.integers(min_value=0, max_value=1000),
)
async def test_last_rotation_invariant(
    n: int,
    seed: int,
    isolated_vault_path: Path,
) -> None:
    """ROTATE-24 (hypothesis) — last_rotation is always 0 <= last < n after select."""
    vault = AuthVault(
        providers={
            "openai": [
                ApiKeyCredential(key=f"TEST-key-{i}", provider_id="openai")
                for i in range(n)
            ],
        },
        last_rotation={"openai": seed},
    )
    save_vault(isolated_vault_path, vault)

    await select_credential(
        "openai", vault_path=isolated_vault_path, now=NOW_FROZEN
    )

    reloaded = load_vault(isolated_vault_path)
    assert 0 <= reloaded.last_rotation["openai"] < n


# ── ROTATE-25 ─────────────────────────────────────────────────────────────


async def test_select_deterministic_for_fixed_now(
    isolated_vault_path: Path,
    vault_with_three_oauth: AuthVault,
) -> None:
    """ROTATE-25 — for fixed now and fixed seed, select returns same idx (no time.time() reads)."""
    save_vault(isolated_vault_path, vault_with_three_oauth)
    idx_a, _ = await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
    )

    # Reset to identical pre-state.
    save_vault(isolated_vault_path, vault_with_three_oauth)
    idx_b, _ = await select_credential(
        "anthropic", vault_path=isolated_vault_path, now=NOW_FROZEN
    )

    assert idx_a == idx_b


# ── ROTATE-26 ─────────────────────────────────────────────────────────────


def test_public_reexports() -> None:
    """ROTATE-26 — public API re-exported at state_core.auth root."""
    from state_core.auth import (
        NoCredentialsAvailableError,
        clear_rate_limited,
        iter_active_credentials,
        mark_rate_limited,
        select_credential,
    )

    assert callable(select_credential)
    assert callable(mark_rate_limited)
    assert callable(clear_rate_limited)
    assert callable(iter_active_credentials)
    assert issubclass(NoCredentialsAvailableError, Exception)


# ── BUCKET_MS sanity ──────────────────────────────────────────────────────

# Imported but otherwise unused at module top-level — assert here so the import
# is a load-bearing reference (the import itself fails RED in Wave 0).
_ = BUCKET_MS
