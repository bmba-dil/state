"""RED tests for Phase 013 — state_core.auth.refresh.

Plan 01 ships these stubs so Plan 02's implementation has a locked
AUTH-07 / AUTH-09 / P0-6 / P0-7 contract to satisfy.

Test naming convention: every test maps to a REFRESH-NN entry in
.planning/milestones/v2/phases/013-filelock-guarded-refresh-lock/013-VALIDATION.md
(see also 013-RESEARCH.md §Validation Architecture).

Markers ``integration`` and ``slow`` gate the heavy concurrency tests
(REFRESH-18, REFRESH-21, REFRESH-27) — registered in pyproject.toml
under ``[tool.pytest.ini_options].markers``.

RED-state strategy:
    Plan 01 ships these tests BEFORE ``state_core.auth.refresh`` exists.
    The module is imported via ``try / except ImportError`` and a
    ``pytestmark = pytest.mark.skipif(...)`` ensures collection always
    succeeds — every test is SKIPPED with a clear reason until Plan 02
    lands the production module. This mirrors the canonical pattern in
    ``tests/auth/test_store.py``.

    Once Plan 02 ships, the import resolves and any missing attribute
    inside an individual test surfaces as ``AttributeError`` and turns
    that test RED — exactly the contract Plan 02 must satisfy.
"""
from __future__ import annotations

import asyncio
import multiprocessing as mp
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import filelock
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from state_core.auth.base import (
    ApiKeyCredential,
    AuthMethod,  # noqa: F401  (kept for parity with mock_auth_method fixture)
    Credential,
    OAuthCredential,
)
from state_core.auth.store import AuthVault, load_vault, save_vault

# ── Conditional import of Plan 02's surface ──────────────────────────────
# Direct ImportError on collection would also be acceptable RED, but the
# preferred shape per the plan is collection-passes-then-skips so the
# `--collect-only` catalogue surfaces exactly 30 items.

try:
    from state_core.auth import refresh  # type: ignore[import-not-found, attr-defined]

    _REFRESH_AVAILABLE = True
    _IMPORT_ERROR: ImportError | None = None
except ImportError as _e:  # pragma: no cover — RED state for Wave 0
    _REFRESH_AVAILABLE = False
    _IMPORT_ERROR = _e
    refresh = None  # type: ignore[assignment]


pytestmark = pytest.mark.skipif(
    not _REFRESH_AVAILABLE,
    reason=f"Plan 02 not yet landed: {_IMPORT_ERROR}",
)


# ── Cross-process subprocess helpers (top-level for pickle compatibility) ─


def _hold_lock_subprocess(lock_path: str, hold_seconds: float) -> None:
    """Acquire ``lock_path`` and hold it for ``hold_seconds``.

    Top-level so ``mp.Process(target=...)`` can pickle the function on
    macOS spawn. Imports inside the function for subprocess-safety.
    """
    import time as _time

    import filelock as _filelock

    with _filelock.FileLock(lock_path, timeout=-1):
        _time.sleep(hold_seconds)


def _acquire_lock_then_exit(lock_path: str) -> None:  # pragma: no cover
    """Acquire ``lock_path`` and sleep forever — parent SIGKILLs us.

    Used by REFRESH-21 to prove flock(2) auto-releases on process death.
    """
    import time as _time

    import filelock as _filelock

    with _filelock.FileLock(lock_path, timeout=-1):
        _time.sleep(60)


# ── REFRESH-01: 5-min buffer boundary (AUTH-09) ──────────────────────────
def test_is_expired_buffered_boundary(oauth_cred: OAuthCredential) -> None:
    """`is_expired_buffered` returns False at -301 s and True at -300/-299."""
    expires = oauth_cred.expires
    assert refresh.is_expired_buffered(oauth_cred, now=expires - 301) is False
    assert refresh.is_expired_buffered(oauth_cred, now=expires - 300) is True
    assert refresh.is_expired_buffered(oauth_cred, now=expires - 299) is True


# ── REFRESH-02: API keys never expire ────────────────────────────────────
def test_is_expired_buffered_api_key_never_expires(
    api_key_cred: ApiKeyCredential,
) -> None:
    """`is_expired_buffered` on ApiKeyCredential returns False for any now."""
    assert refresh.is_expired_buffered(api_key_cred, now=0.0) is False
    assert refresh.is_expired_buffered(api_key_cred, now=1e12) is False
    assert refresh.is_expired_buffered(api_key_cred, now=-1e9) is False


# ── REFRESH-03: deterministic — no time.time() inside ────────────────────
def test_is_expired_buffered_no_clock_read(
    oauth_cred: OAuthCredential, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`is_expired_buffered` MUST take ``now`` from the parameter, never
    from ``time.time()`` (cardinal determinism rule). Patch ``time.time``
    to fail loudly and assert the function still returns the right answer.
    """
    def _forbidden() -> float:
        pytest.fail("is_expired_buffered must not read time.time()")
        return 0.0  # unreachable

    monkeypatch.setattr(time, "time", _forbidden)

    # Should still compute correctly using the supplied now.
    assert (
        refresh.is_expired_buffered(oauth_cred, now=oauth_cred.expires - 301)
        is False
    )
    assert (
        refresh.is_expired_buffered(oauth_cred, now=oauth_cred.expires - 100)
        is True
    )


# ── REFRESH-04: RefreshLockTimeout MRO ───────────────────────────────────
def test_refresh_lock_timeout_hierarchy() -> None:
    """`RefreshLockTimeout` subclasses both filelock.Timeout and TimeoutError."""
    assert issubclass(refresh.RefreshLockTimeout, filelock.Timeout)
    assert issubclass(refresh.RefreshLockTimeout, TimeoutError)


# ── REFRESH-05: RefreshLockTimeout carries lock_path + message ───────────
def test_refresh_lock_timeout_message() -> None:
    """The exception preserves the offending path and mentions the 10 s
    timeout in its string representation."""
    p = Path("/tmp/some.auth.json.lock")
    exc = refresh.RefreshLockTimeout(p)

    assert exc.lock_path == p
    msg = str(exc)
    assert "10" in msg
    assert str(p) in msg


# ── REFRESH-06: lock path lives next to the vault ────────────────────────
def test_lock_path_next_to_vault() -> None:
    """``_lock_path_for(vault) == <vault>.lock`` — sibling, not child dir."""
    fn = getattr(refresh, "_lock_path_for")
    assert fn(Path("/a/b/auth.json")) == Path("/a/b/auth.json.lock")
    # Defensive: a deeper path keeps the same shape.
    assert fn(Path("/x/.state/auth.json")) == Path("/x/.state/auth.json.lock")


# ── REFRESH-07: AsyncFileLock thread_local=False (Pitfall 1) ─────────────
def test_async_lock_thread_local_false(auth_json_path: Path) -> None:
    """The constructed AsyncFileLock disables thread-local reentrancy so
    coroutines on the same thread don't corrupt the reentrant counter."""
    fn = getattr(refresh, "_new_async_lock")
    lock = fn(auth_json_path)
    assert lock.is_thread_local() is False


# ── REFRESH-08: AsyncFileLock construct defaults (timeout + lockfile) ────
def test_async_lock_construct_defaults(auth_json_path: Path) -> None:
    """`_new_async_lock` returns a lock with timeout=10.0 and a lockfile
    path that ends in ``.lock`` (next-to-vault per REFRESH-06)."""
    fn = getattr(refresh, "_new_async_lock")
    lock = fn(auth_json_path)
    assert lock.timeout == refresh.LOCK_TIMEOUT_SECONDS == 10.0
    # filelock's public attribute for the path is `lock_file`; tolerate `_lock_file`.
    lock_file = getattr(lock, "lock_file", None) or getattr(lock, "_lock_file", None)
    assert lock_file is not None
    assert str(lock_file).endswith(".lock")


# ── REFRESH-09: read_credential returns the fresh cred ───────────────────
async def test_read_credential_returns_fresh(
    auth_json_path: Path, vault_with_one_oauth: AuthVault, oauth_cred: OAuthCredential
) -> None:
    """`read_credential` round-trips a saved fresh OAuth cred."""
    save_vault(auth_json_path, vault_with_one_oauth)

    got = await refresh.read_credential(
        "anthropic", 0, vault_path=auth_json_path
    )

    assert isinstance(got, OAuthCredential)
    assert got.access == oauth_cred.access
    assert got.expires == oauth_cred.expires


# ── REFRESH-10: read_credential KeyError on unknown provider ─────────────
async def test_read_credential_unknown_provider(
    auth_json_path: Path, vault_with_one_oauth: AuthVault
) -> None:
    """Unknown provider_id raises KeyError, never returns None."""
    save_vault(auth_json_path, vault_with_one_oauth)

    with pytest.raises(KeyError):
        await refresh.read_credential(
            "missing-provider", 0, vault_path=auth_json_path
        )


# ── REFRESH-11: read_credential IndexError on bad idx ────────────────────
async def test_read_credential_bad_index(
    auth_json_path: Path, vault_with_one_oauth: AuthVault
) -> None:
    """Out-of-range idx raises IndexError (Phase 019 round-robin contract)."""
    save_vault(auth_json_path, vault_with_one_oauth)

    with pytest.raises(IndexError):
        await refresh.read_credential(
            "anthropic", 99, vault_path=auth_json_path
        )


# ── REFRESH-12: read_credential briefly acquires the lock ────────────────
async def test_read_credential_acquires_lock(
    auth_json_path: Path,
    vault_with_one_oauth: AuthVault,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`read_credential` MUST enter the AsyncFileLock context (briefly)
    so it blocks during a refresh window. We mock ``_new_async_lock`` to
    return a spy whose ``__aenter__`` we can introspect."""
    save_vault(auth_json_path, vault_with_one_oauth)

    spy = MagicMock(spec=filelock.AsyncFileLock)
    spy.__aenter__ = AsyncMock(return_value=spy)
    spy.__aexit__ = AsyncMock(return_value=None)
    spy.timeout = 10.0
    monkeypatch.setattr(refresh, "_new_async_lock", lambda *a, **kw: spy)

    await refresh.read_credential(
        "anthropic", 0, vault_path=auth_json_path
    )

    spy.__aenter__.assert_awaited()
    spy.__aexit__.assert_awaited()


# ── REFRESH-13: refresh_credential skips network when fresh ──────────────
async def test_refresh_credential_skips_when_fresh(
    auth_json_path: Path,
    vault_with_one_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """A non-expired OAuth cred is returned without invoking method.refresh."""
    save_vault(auth_json_path, vault_with_one_oauth)

    cred = await refresh.refresh_credential(
        mock_auth_method,
        "anthropic",
        0,
        vault_path=auth_json_path,
        now=now_frozen,
    )

    assert mock_auth_method.refresh_calls == 0
    assert isinstance(cred, OAuthCredential)
    assert cred.expires == 2_000_000_000.0


# ── REFRESH-14: refresh_credential refreshes a stale cred ────────────────
async def test_refresh_credential_refreshes_stale(
    auth_json_path: Path,
    vault_with_expired_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """A stale OAuth cred triggers method.refresh exactly once and the
    new value is persisted to the vault on disk."""
    save_vault(auth_json_path, vault_with_expired_oauth)
    old_expires = vault_with_expired_oauth.providers["anthropic"][0].expires

    new_cred = await refresh.refresh_credential(
        mock_auth_method,
        "anthropic",
        0,
        vault_path=auth_json_path,
        now=now_frozen,
    )

    assert mock_auth_method.refresh_calls == 1
    assert isinstance(new_cred, OAuthCredential)
    assert new_cred.expires == old_expires + 3600.0

    reloaded = load_vault(auth_json_path)
    assert reloaded.providers["anthropic"][0].expires == old_expires + 3600.0


# ── REFRESH-15: force=True bypasses the quick-check ──────────────────────
async def test_refresh_credential_force_bypasses_quickcheck(
    auth_json_path: Path,
    vault_with_one_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """Even on a fresh cred, force=True triggers a single refresh call."""
    save_vault(auth_json_path, vault_with_one_oauth)

    await refresh.refresh_credential(
        mock_auth_method,
        "anthropic",
        0,
        vault_path=auth_json_path,
        now=now_frozen,
        force=True,
    )

    assert mock_auth_method.refresh_calls == 1


# ── REFRESH-16: ApiKey short-circuit (no refresh, no lock) ───────────────
async def test_refresh_credential_apikey_short_circuit(
    auth_json_path: Path,
    api_key_cred: ApiKeyCredential,
    mock_auth_method: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`ApiKeyCredential` is returned unchanged with NO refresh call AND
    NO lock acquisition — even when ``force=True``."""
    vault = AuthVault(providers={"anthropic": [api_key_cred]})
    save_vault(auth_json_path, vault)

    spy = MagicMock(spec=filelock.AsyncFileLock)
    spy.__aenter__ = AsyncMock(return_value=spy)
    spy.__aexit__ = AsyncMock(return_value=None)
    spy.timeout = 10.0
    monkeypatch.setattr(refresh, "_new_async_lock", lambda *a, **kw: spy)

    out = await refresh.refresh_credential(
        mock_auth_method,
        "anthropic",
        0,
        vault_path=auth_json_path,
        force=True,
    )

    assert isinstance(out, ApiKeyCredential)
    assert mock_auth_method.refresh_calls == 0
    spy.__aenter__.assert_not_called()
    spy.__aexit__.assert_not_called()


# ── REFRESH-17: double-check pattern prevents thundering herd (P0-6) ─────
async def test_double_check_prevents_thundering_herd(
    auth_json_path: Path,
    vault_with_expired_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """5 concurrent ``refresh_credential`` calls on a stale cred → exactly
    ONE invocation of ``method.refresh``. All 5 callers receive the same
    refreshed credential (P0-6 owned by Phase 013)."""
    save_vault(auth_json_path, vault_with_expired_oauth)

    results = await asyncio.gather(
        *[
            refresh.refresh_credential(
                mock_auth_method,
                "anthropic",
                0,
                vault_path=auth_json_path,
                now=now_frozen,
            )
            for _ in range(5)
        ]
    )

    assert mock_auth_method.refresh_calls == 1
    expires_set = {c.expires for c in results}
    assert len(expires_set) == 1, (
        f"All 5 callers should observe the same refreshed cred; got {expires_set}"
    )


# ── REFRESH-18: cross-process lock timeout → RefreshLockTimeout ──────────
@pytest.mark.integration
async def test_refresh_credential_lock_timeout(
    auth_json_path: Path,
    vault_with_expired_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """When another process holds the lock for >10 s, ``refresh_credential``
    raises ``RefreshLockTimeout`` (subclass of TimeoutError)."""
    save_vault(auth_json_path, vault_with_expired_oauth)
    lock_path = str(auth_json_path) + ".lock"

    ctx = mp.get_context("spawn")
    proc = ctx.Process(target=_hold_lock_subprocess, args=(lock_path, 20.0))
    proc.start()
    try:
        # Poll briefly for the child to actually acquire the lock.
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if Path(lock_path).exists():
                break
            await asyncio.sleep(0.05)

        with pytest.raises(refresh.RefreshLockTimeout):
            await refresh.refresh_credential(
                mock_auth_method,
                "anthropic",
                0,
                vault_path=auth_json_path,
                now=now_frozen,
            )
    finally:
        proc.terminate()
        proc.join(timeout=5.0)
        if proc.is_alive():
            proc.kill()
            proc.join()


# ── REFRESH-19: HTTP timeout → TimeoutError (NOT RefreshLockTimeout) ─────
async def test_refresh_credential_http_timeout(
    auth_json_path: Path,
    vault_with_expired_oauth: AuthVault,
    now_frozen: float,
) -> None:
    """When ``method.refresh`` hangs longer than 15 s, ``refresh_credential``
    raises ``TimeoutError`` — the lock-side ``RefreshLockTimeout`` is a
    DIFFERENT class (P1-9 deadlock defense)."""
    save_vault(auth_json_path, vault_with_expired_oauth)

    class HangingMethod:
        provider_id = "anthropic"
        def is_token(self, value: str) -> bool: return False
        def is_expired(self, cred: Credential, now: float) -> bool: return True
        def http_headers(self, cred: Credential) -> dict[str, str]: return {}
        async def login(self) -> Credential: raise NotImplementedError
        async def refresh(self, cred: Credential) -> Credential:
            await asyncio.sleep(60)
            return cred

    method = HangingMethod()
    start = time.perf_counter()
    with pytest.raises(TimeoutError) as excinfo:
        await refresh.refresh_credential(
            method,
            "anthropic",
            0,
            vault_path=auth_json_path,
            now=now_frozen,
        )
    elapsed = time.perf_counter() - start

    # Must NOT be a RefreshLockTimeout — that's a different code path.
    assert not isinstance(excinfo.value, refresh.RefreshLockTimeout)
    # Hard cap: REFRESH_HTTP_TIMEOUT_SECONDS is 15.0 — bound the wait at 16 s.
    assert elapsed < 16.0


# ── REFRESH-20: lock released on exception (next acquire succeeds) ───────
async def test_refresh_credential_releases_lock_on_exception(
    auth_json_path: Path,
    vault_with_expired_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """If ``method.refresh`` raises, the lock is released by ``async with``.
    A subsequent ``refresh_credential`` call must succeed within 10 s."""
    save_vault(auth_json_path, vault_with_expired_oauth)

    class BoomMethod:
        provider_id = "anthropic"
        called = 0
        def is_token(self, value: str) -> bool: return False
        def is_expired(self, cred: Credential, now: float) -> bool: return True
        def http_headers(self, cred: Credential) -> dict[str, str]: return {}
        async def login(self) -> Credential: raise NotImplementedError
        async def refresh(self, cred: Credential) -> Credential:
            BoomMethod.called += 1
            raise RuntimeError("boom")

    boom = BoomMethod()
    with pytest.raises(RuntimeError, match="boom"):
        await refresh.refresh_credential(
            boom, "anthropic", 0, vault_path=auth_json_path, now=now_frozen
        )

    # Second call uses a non-throwing method — must complete (lock free).
    out = await asyncio.wait_for(
        refresh.refresh_credential(
            mock_auth_method,
            "anthropic",
            0,
            vault_path=auth_json_path,
            now=now_frozen,
        ),
        timeout=10.0,
    )
    assert isinstance(out, OAuthCredential)
    assert mock_auth_method.refresh_calls == 1


# ── REFRESH-21: SIGKILL'd process releases lock (kernel auto-release) ────
@pytest.mark.integration
async def test_killed_process_releases_lock(
    auth_json_path: Path,
    vault_with_expired_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """A SIGKILL'd lock-holder triggers kernel-level flock(2) auto-release;
    the parent's next ``refresh_credential`` succeeds within timeout."""
    save_vault(auth_json_path, vault_with_expired_oauth)
    lock_path = str(auth_json_path) + ".lock"

    ctx = mp.get_context("spawn")
    proc = ctx.Process(target=_acquire_lock_then_exit, args=(lock_path,))
    proc.start()
    try:
        # Wait for the child to actually acquire the lock.
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if Path(lock_path).exists():
                break
            await asyncio.sleep(0.05)

        # SIGKILL the lock-holder.
        proc.kill()
        proc.join(timeout=5.0)
        assert not proc.is_alive()

        # Parent acquires within 10 s — kernel released the flock.
        out = await asyncio.wait_for(
            refresh.refresh_credential(
                mock_auth_method,
                "anthropic",
                0,
                vault_path=auth_json_path,
                now=now_frozen,
            ),
            timeout=10.0,
        )
        assert isinstance(out, OAuthCredential)
    finally:
        if proc.is_alive():  # pragma: no cover - defensive
            proc.kill()
            proc.join()


# ── REFRESH-22: lockfile is empty by design (Pitfall 4) ──────────────────
async def test_lockfile_is_empty(
    auth_json_path: Path,
    vault_with_expired_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """After ``refresh_credential``, the lockfile exists but contains 0 bytes
    — flock(2) operates on the file descriptor, not file contents."""
    save_vault(auth_json_path, vault_with_expired_oauth)

    await refresh.refresh_credential(
        mock_auth_method,
        "anthropic",
        0,
        vault_path=auth_json_path,
        now=now_frozen,
    )

    lockfile = auth_json_path.with_name(auth_json_path.name + ".lock")
    assert lockfile.exists()
    assert lockfile.stat().st_size == 0


# ── REFRESH-23: mode isolation — no state_build / state_teach pull-in ────
def test_no_mode_imports() -> None:
    """Importing ``state_core.auth.refresh`` does NOT pull build/teach
    modules into ``sys.modules`` (cardinal mode-isolation rule)."""
    import importlib

    before = set(sys.modules)
    importlib.reload(importlib.import_module("state_core.auth.refresh"))
    after = set(sys.modules)
    delta = after - before
    leaked = [
        m
        for m in delta
        if m.startswith(("state_build.", "state_teach."))
        or m in {"state_build", "state_teach"}
    ]
    assert not leaked, f"state_core.auth.refresh leaked mode imports: {leaked}"


# ── REFRESH-24: refresh writes the right slot ────────────────────────────
async def test_refresh_credential_updates_correct_slot(
    auth_json_path: Path,
    expired_oauth_cred: OAuthCredential,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """Two creds, both expired. Refreshing idx=1 leaves idx=0 untouched."""
    cred0 = expired_oauth_cred.model_copy(update={"account_id": "acct-zero"})
    cred1 = expired_oauth_cred.model_copy(update={"account_id": "acct-one"})
    vault = AuthVault(providers={"anthropic": [cred0, cred1]})
    save_vault(auth_json_path, vault)

    await refresh.refresh_credential(
        mock_auth_method,
        "anthropic",
        1,
        vault_path=auth_json_path,
        now=now_frozen,
    )

    reloaded = load_vault(auth_json_path)
    assert reloaded.providers["anthropic"][0].expires == cred0.expires  # untouched
    assert reloaded.providers["anthropic"][0].account_id == "acct-zero"
    assert reloaded.providers["anthropic"][1].expires == cred1.expires + 3600.0
    assert reloaded.providers["anthropic"][1].account_id == "acct-one"


# ── REFRESH-25: durable write — a fresh load_vault sees the new cred ─────
async def test_refresh_credential_durable_write(
    auth_json_path: Path,
    vault_with_expired_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """`save_vault`'s atomic-rename guarantees the new cred is on disk
    when ``refresh_credential`` returns."""
    save_vault(auth_json_path, vault_with_expired_oauth)
    old_expires = vault_with_expired_oauth.providers["anthropic"][0].expires

    await refresh.refresh_credential(
        mock_auth_method,
        "anthropic",
        0,
        vault_path=auth_json_path,
        now=now_frozen,
    )

    # Fresh load — bytes-on-disk, not in-memory closure.
    reloaded = load_vault(auth_json_path)
    cred = reloaded.providers["anthropic"][0]
    assert isinstance(cred, OAuthCredential)
    assert cred.expires == old_expires + 3600.0


# ── REFRESH-26: hypothesis property — buffer boundary ────────────────────
@settings(
    max_examples=50,
    deadline=2000,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    expires=st.floats(
        min_value=1.0,
        max_value=4e9,
        allow_nan=False,
        allow_infinity=False,
    ),
    delta=st.floats(
        min_value=-1000.0,
        max_value=1000.0,
        allow_nan=False,
        allow_infinity=False,
    ),
)
def test_hypothesis_buffer_boundary(expires: float, delta: float) -> None:
    """Property: now < expires - 300 → False; now >= expires - 300 → True."""
    cred = OAuthCredential(
        access="x",
        refresh="y",
        expires=expires,
        provider_id="anthropic",
    )
    now = expires - 300.0 + delta
    expected = now >= expires - 300.0
    assert refresh.is_expired_buffered(cred, now=now) is expected


# ── REFRESH-27: no self-reentry (slow ~10 s) ─────────────────────────────
@pytest.mark.slow
async def test_no_self_reentry(
    auth_json_path: Path,
    vault_with_one_oauth: AuthVault,
    mock_auth_method: Any,
) -> None:
    """Calling ``read_credential`` from inside an externally-held
    ``_new_async_lock`` block deadlocks (caught by 10 s lock timeout) —
    proves no public function reaches in via the lock unintentionally."""
    save_vault(auth_json_path, vault_with_one_oauth)
    fn = getattr(refresh, "_new_async_lock")
    outer = fn(auth_json_path)

    async with outer:
        # Inside the held lock — read_credential must contend on the same
        # lockfile and time out within ~10 s. Bound the wait at 11 s.
        with pytest.raises(refresh.RefreshLockTimeout):
            await asyncio.wait_for(
                refresh.read_credential(
                    "anthropic", 0, vault_path=auth_json_path
                ),
                timeout=11.0,
            )


# ── REFRESH-28: NFS warning lives in module / source docstring ───────────
def test_module_warns_about_nfs() -> None:
    """The module's docstring (or source text) must mention NFS — the
    P2-5 documentation defense surfaces filesystem-locality requirements."""
    doc = refresh.__doc__ or ""
    src = ""
    try:
        src = Path(refresh.__file__).read_text()
    except Exception:  # pragma: no cover - defensive
        pass
    assert "NFS" in doc or "NFS" in src, (
        "module docstring or source must mention NFS (P2-5)"
    )


# ── REFRESH-29: structlog observability of acquire + refresh events ──────
async def test_emits_acquisition_logs(
    auth_json_path: Path,
    vault_with_expired_oauth: AuthVault,
    mock_auth_method: Any,
    now_frozen: float,
) -> None:
    """`refresh_credential` emits ``refresh_lock.acquired`` AND
    ``refresh_lock.refreshed`` structlog events; the latter carries
    ``lock_held_seconds`` for observability (P1-9)."""
    save_vault(auth_json_path, vault_with_expired_oauth)

    from structlog.testing import capture_logs

    with capture_logs() as logs:
        await refresh.refresh_credential(
            mock_auth_method,
            "anthropic",
            0,
            vault_path=auth_json_path,
            now=now_frozen,
        )

    events = {e.get("event") for e in logs}
    assert "refresh_lock.acquired" in events
    assert "refresh_lock.refreshed" in events
    refreshed = next(e for e in logs if e.get("event") == "refresh_lock.refreshed")
    assert "lock_held_seconds" in refreshed


# ── REFRESH-30: public exports re-exposed from state_core.auth ───────────
def test_public_exports() -> None:
    """The ``state_core.auth`` package re-exports the refresh public API."""
    from state_core.auth import (  # noqa: F401
        EXPIRY_BUFFER_SECONDS,
        RefreshLockTimeout,
        is_expired_buffered,
        read_credential,
        refresh_credential,
    )
