# Phase 013: Filelock-guarded refresh lock (`refresh.py`) — Research

**Researched:** 2026-04-28
**Domain:** Cross-process refresh coordination — `filelock.AsyncFileLock` + double-checked stale-credential refresh + reader-side blocking
**Confidence:** HIGH

## Summary

Phase 013 owns `state_core.auth.refresh` — the cross-process refresh-coordinator that wraps every credential mutation in a `filelock` so two `state` processes (daemon + per-session worker, or two opencode sessions) can never clobber each other's just-refreshed token (P0-6). It also owns the canonical home for the 5-minute expiry buffer (`is_expired_buffered`, AUTH-09 / P0-7) — a deliberately *separate* function from any provider's `is_expired`, so callers that don't have an `AuthMethod` instance handy (Phase 022 CLI, Phase 020 redactor's "is this token close to expiry?" hint) can answer the question without reaching into the provider registry.

Three concerns must be solved together, not separately:

1. **Cross-process serialization** — `filelock>=3.20.3` (we have 3.29.0 installed) ships a native `AsyncFileLock` that polls the lockfile every 50 ms in an executor thread; the asyncio event loop never blocks during the 10-second acquire. The lock is reentrant *within a single thread* but not across asyncio coroutines unless `thread_local=False` is set explicitly. AsyncFileLock's default already does this — but we set it explicitly anyway for documentation and to defend against the surprise default-flip a future filelock release could introduce.
2. **Double-checked refresh** — between "I observed cred is expiring" and "I acquired the lock," another process may have already refreshed. Re-read the vault inside the lock, re-extract the credential at the same `(provider_id, idx)` slot, re-check `is_expired_buffered` against a *fresh* `now`. If still stale, refresh; otherwise return what we found. Without this, every waiter behind a lock gets a self-imposed thundering-herd refresh.
3. **Reader-side blocking** — opencode's hot path is "read credential, mint outbound HTTP request." If a refresh is in flight, naive readers race against the writer's `os.replace`. Phase 012's atomic-rename guarantees the reader sees *either* old-or-new, never half-written — but they may still see the *old* (about-to-expire) credential and then 401 mid-stream. The fix is for the reader to *briefly* acquire the same lock (read-side critical section is sub-millisecond — just `load_vault` + slice), guaranteeing the reader sees the post-refresh value once a writer finishes.

The non-obvious design decision is **per-vault lock vs per-provider lock**. We choose per-vault (`auth.json.lock`). Two refreshes on different providers will serialize, but the refresh path is rare (5 min × N providers per hour) and the lock-held duration is bounded (15 s HTTP timeout per P1-9). Per-provider locks would require N lockfiles, N stale-lock detection paths, and a directory-walk to enumerate them at daemon shutdown — for a benefit (simultaneous multi-provider refresh) we never observably need.

**Primary recommendation:** Implement `state_core.auth.refresh` as a ~120-line module exposing `refresh_credential(method, provider_id, idx, now=None)` (the writer entry point), `read_credential(provider_id, idx, now=None)` (the reader entry point that briefly takes the lock), `is_expired_buffered(cred, now, buffer=300.0)` (pure function, no I/O), and `RefreshLockTimeout(filelock.Timeout)`. Use `filelock.AsyncFileLock` directly with `thread_local=False`, `timeout=10.0`, `poll_interval=0.05`. Lockfile sits next to the vault at `<auth.json>.lock`. The lock is acquired around `load_vault → check → refresh → save_vault`; `AuthMethod.refresh()` is awaited *inside* the held lock. No `asyncio.to_thread` wrapping — `AsyncFileLock` already does its blocking work in an executor.

## User Constraints (from CONTEXT.md)

### Locked Decisions
*(none — discuss phase was skipped via `workflow.skip_discuss`)*

### Claude's Discretion
All implementation choices at Claude's discretion — discuss skipped per workflow.skip_discuss. Use ROADMAP, RESEARCH, AUTH-07/AUTH-09 specs, P0-6/P0-7 pitfalls, Phase 012's `load_vault`/`save_vault` API, and Phase 011's `Credential`/`AuthMethod` Protocol.

### Specific Ideas (from CONTEXT.md)
- `filelock.FileLock(path / "auth.json.lock", timeout=10.0)` — 10-second acquire
- Double-checked refresh pattern: acquire lock → re-read vault → check expiry AGAIN → refresh only if still stale (defends against thundering herd of waiters)
- 5-minute buffer (AUTH-09) lives HERE in `is_expired_buffered(cred, now, buffer=300.0)`, not in `OAuthCredential.expires` field (kept as wire-shape per Phase 011 Pattern 3)
- Reader-side `read_credential(path, provider_id)` MUST acquire the same lock briefly to block during refresh window (avoid reading half-written vault)
- Async-friendly: filelock is sync; wrap in `asyncio.to_thread` for the lock acquisition; `AuthMethod.refresh()` is awaited normally inside
- `RefreshLockTimeout` exception on 10s timeout (subclass of TimeoutError)

### Deferred Ideas (OUT OF SCOPE)
None — discuss phase skipped.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **AUTH-07** | Filelock-guarded refresh: acquire lock (10s timeout), re-read `auth.json`, double-check expiry, refresh only if stale, write, release | Pattern 1 (double-checked refresh inside `AsyncFileLock`), Pattern 2 (reader-side brief lock acquisition), Pitfall 1 (thread_local default), Pitfall 2 (no thundering-herd refresh), Pitfall 3 (HTTP timeout INSIDE lock to prevent P1-9 deadlock), Pitfall 6 (reentrancy between `read_credential` and `refresh_credential`). `RefreshLockTimeout(filelock.Timeout)` is the dedicated 10s-acquisition signal. |
| **AUTH-09** | Access token renewal 5 minutes before `expires_in` (never verbatim) | Pattern 3 (`is_expired_buffered(cred, now, buffer=300.0)`), determinism: `now: float` injected, never `time.time()` internally; ApiKeyCredential always returns False; cleanly callable without an `AuthMethod` instance (decouples Phase 020 redactor's "is_expiring_soon" hint and Phase 022 CLI's `state auth status` from provider lookups). Pitfall 7 documents the upstream tension (PITFALLS.md P0-7 says "subtract before storing"; Phase 011 Pattern 3 says "store wire value, subtract on check") — we follow Phase 011 (binding decision; PITFALLS.md was written before Phase 011 Pattern 3 was adopted). |
| **P0-6 (owned)** | Concurrent refresh / token clobber | The whole module. Cross-process `filelock.AsyncFileLock` serializes all writes. Double-check pattern inside the lock prevents thundering-herd (Pattern 1 step 4). Reader-side lock (Pattern 2) prevents stale reads after a refresh window. P1-9 deadlock defense via 15 s HTTP timeout inside the held lock. P2-5 NFS warning carried in module docstring. |
| **P0-7 (owned)** | 5-minute expiry buffer | `is_expired_buffered(cred, now, buffer=300.0)` is the canonical check. Anthropic provider's `is_expired` (Phase 014) delegates to this same function so the math lives in exactly one place. AUTH-13 captured-header regression (Phase 022) verifies the wire-shape `expires` round-trips unchanged. |

**Downstream consumers (research must enable, not implement):**

| Phase | Consumes from 013 | What 013 must guarantee |
|-------|-------------------|-------------------------|
| 014–017 (OAuth providers) | Their `refresh()` is called *inside* the lock by `refresh_credential` | `refresh_credential(method, provider_id, idx)` accepts an `AuthMethod` instance and the slot index; provider's async `refresh()` is awaited inside the held lock; the returned new `Credential` is what gets persisted. |
| 018 (API-key vault) | Reads via `read_credential` | `is_expired_buffered` returns False unconditionally for `ApiKeyCredential`; `read_credential` short-circuits the refresh path for API keys (no lock contention churn). |
| 019 (multi-cred round-robin) | Calls `refresh_credential(method, provider_id, idx)` for each rotated slot | Lock is per-vault; round-robin can iterate slots inside a single held lock OR re-acquire per slot. Recommend: round-robin holds the lock once and iterates (one lock per "pick a credential" call). |
| 020 (root-logger redactor) | May call `is_expired_buffered` for "expires soon" log fields | Pure function, no I/O — safe from inside log filters (no recursion). |
| 022 (CLI `state auth refresh <provider>`) | Calls `refresh_credential` directly (force refresh) | Provide a `force=True` parameter that skips the expiry double-check (always refreshes) — CLI users want guaranteed-fresh tokens for support diagnostics. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `filelock` | **>=3.20.3** (installed: 3.29.0) | Cross-process file lock with native `AsyncFileLock` | Pinned in `pyproject.toml`; CVE-2026-22701 floor enforced; the *only* committed cross-platform file-lock library. AsyncFileLock dispatches blocking acquire to executor (asyncio-safe out of the box). |
| `state_core.auth.store` | (Phase 012) | `load_vault`, `save_vault`, `get_auth_json_path`, `AuthVault` | Provides the sync vault I/O `refresh.py` wraps. Sync API is correct here — file I/O on ~1 KB JSON is cheaper than async overhead. |
| `state_core.auth.base` | (Phase 011) | `Credential`, `OAuthCredential`, `ApiKeyCredential`, `AuthMethod` | Type contracts. `AuthMethod.refresh()` is async; we await it inside the held lock. |
| `structlog` | ≥25.1 (pinned) | Per-acquisition logging (lock duration, double-check outcome, refresh outcome) | Per P1-9 mitigation: "Log every lock acquisition with duration." Same logger pattern as `state_core.auth.store` (`structlog.get_logger(__name__)`). |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio` (stdlib) | 3.12 | `asyncio.wait_for` to enforce 15 s HTTP timeout INSIDE the lock | P1-9 deadlock defense. Wrap `await method.refresh(cred)` in `asyncio.wait_for(..., timeout=15.0)` so a hung network call cannot pin the lock indefinitely. |
| `time` (stdlib) | 3.12 | `time.time()` ONLY at the public-API boundary when caller passes `now=None` | Determinism rule: internal functions take `now: float`. Public entry points may default `now` to `time.time()` once at the boundary, then pass it down. Pure functions inside (`is_expired_buffered`) NEVER read the clock. |
| `contextlib.AbstractAsyncContextManager` | 3.12 stdlib | Type hint for any helper that yields a held lock (optional) | If we want to expose `held_vault_lock()` as a context manager helper for round-robin (Phase 019). Optional. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `filelock.AsyncFileLock` (native async) | `asyncio.to_thread(FileLock(...).acquire)` + manual release | **Rejected** — `AsyncFileLock` is the documented async path (filelock 3.x), already does the executor dispatch internally, and supports `async with` natively. Manual `to_thread` wrapping is what older code did before `AsyncFileLock` existed (filelock <3.10). The CONTEXT.md hint to "wrap in `asyncio.to_thread`" is from a research session before AsyncFileLock was confirmed; AsyncFileLock supersedes it. |
| `filelock.FileLock` (sync) inside `asyncio.to_thread` | `AsyncFileLock` | **Rejected** — works but bypasses AsyncFileLock's `cancel_check` parameter (potentially useful for SIGTERM-aware acquisition; see Open Question 2). Use AsyncFileLock and keep options open. |
| `filelock.SoftFileLock` (PID-based, atomic-link-free) | `FileLock` (kernel `flock`/`LockFileEx`) | **Rejected** — SoftFileLock has *better* stale-lock recovery (PID + hostname stored inside the lockfile; auto-broken on contention if PID is dead). But its TOCTOU CVE-2026-22701 was the precise reason for our >=3.20.3 floor. We trust the patched SoftFileLock for stale-recovery hygiene but use `FileLock`/`AsyncFileLock` (kernel-backed) as the primary because it's atomic by syscall, not by file existence. Document SoftFileLock as the fallback if NFS detection hits (P2-5). |
| Per-provider lockfiles (`<auth.json>.<provider>.lock`) | Single per-vault `<auth.json>.lock` | **Rejected** — N lockfiles is N stale-lock paths to clean up at shutdown, and the contention benefit is theoretical (refresh is rare). Per-vault lock is simpler. Re-evaluate if benchmarks ever show ≥3 simultaneous refresh attempts. |
| `RefreshLockTimeout(TimeoutError)` (custom subclass) | Re-raise `filelock.Timeout` directly | **Compromise:** define `RefreshLockTimeout` as a subclass of `filelock.Timeout` (which is itself a `TimeoutError` subclass — verified). Catch `filelock.Timeout` from `lock.acquire()`, raise `RefreshLockTimeout` with the human-readable message ("could not acquire `.state/auth.json.lock` within 10 s — another process may be refreshing"). Callers can `except RefreshLockTimeout` (specific) or `except TimeoutError` (broad). |
| `asyncio.Lock` for in-process serialization | `AsyncFileLock` only | **Rejected** — `asyncio.Lock` doesn't cross processes. Even within a single daemon, two opencode sessions are different processes — `asyncio.Lock` would not coordinate. Use `AsyncFileLock` consistently and skip the in-process lock layer (it's redundant with the file lock and adds ordering complexity). |
| Encrypted lockfile contents (PID + hostname) | Empty lockfile | **Rejected** — `FileLock` doesn't write to the lockfile; it relies on `flock(2)` / `LockFileEx`. The lockfile is empty by design. No chmod-0600 needed (no secrets in there). |

**Installation:** No new deps. `filelock>=3.20.3` is already pinned in `pyproject.toml`.

## Architecture Patterns

### Recommended Project Structure

```
src/state_core/auth/
├── __init__.py              # Re-export refresh_credential, read_credential, is_expired_buffered, RefreshLockTimeout
├── base.py                  # Phase 011 — DO NOT EDIT
├── store.py                 # Phase 012 — DO NOT EDIT
├── refresh.py               # ← THIS PHASE
└── providers/               # Phases 014–018
```

**Constraint (mode isolation):** `state_core.auth.refresh` MUST NOT import from `state_build.*` or `state_teach.*`. Imports limited to: stdlib (`asyncio`, `time`, `pathlib`), `filelock`, `structlog`, `state_core.auth.base`, `state_core.auth.store`. Test REFRESH-NN ("test_no_mode_imports") enforces.

### Pattern 1: Double-Checked Refresh inside `AsyncFileLock`

**What:** Acquire the file lock with a 10 s timeout, re-read the vault, re-check expiry, refresh only if still stale, save, release.

**Why:** Without the double-check, every waiter behind the lock issues its own refresh after the first finishes — thundering-herd against the OAuth endpoint. Anthropic invalidates older refresh tokens on issue, so only one of the herd survives; the rest get 401s on their *next* request. With the double-check, every waiter after the first sees the freshly-saved credential and exits without a network call.

**When to use:** Every credential mutation. Every phase below 013 that needs a "current usable credential" (Phase 014–019, Phase 022 CLI) calls into this layer; no caller takes the lock directly.

**Example:**

```python
# src/state_core/auth/refresh.py
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import filelock
import structlog

from state_core.auth.base import ApiKeyCredential, AuthMethod, Credential
from state_core.auth.store import (
    AuthVault,
    get_auth_json_path,
    load_vault,
    save_vault,
)

log = structlog.get_logger(__name__)

LOCK_SUFFIX = ".lock"
"""Lockfile sits next to the vault: .state/auth.json → .state/auth.json.lock."""

LOCK_TIMEOUT_SECONDS = 10.0
"""Per AUTH-07 + P1-9: 10 s acquire timeout."""

REFRESH_HTTP_TIMEOUT_SECONDS = 15.0
"""Per P1-9: 15 s timeout for the AuthMethod.refresh() HTTP call inside the lock."""

EXPIRY_BUFFER_SECONDS = 300.0
"""Per AUTH-09 / P0-7: refresh 5 minutes before wire-shape expiry."""


class RefreshLockTimeout(filelock.Timeout):
    """Raised when the refresh lock could not be acquired within 10 s.

    Subclass of filelock.Timeout (which is a TimeoutError subclass).
    Carries a remediation hint pointing the user at the offending lockfile.
    """

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        # filelock.Timeout's __init__ takes the lockfile path string
        super().__init__(str(lock_path))

    def __str__(self) -> str:
        return (
            f"Could not acquire {self.lock_path} within "
            f"{LOCK_TIMEOUT_SECONDS}s — another process may be refreshing. "
            f"If this persists, check for a stale process holding the lock."
        )


def _lock_path_for(vault_path: Path) -> Path:
    """Resolve the lockfile path next to the vault."""
    return vault_path.with_name(vault_path.name + LOCK_SUFFIX)


def _new_async_lock(vault_path: Path) -> filelock.AsyncFileLock:
    """Construct an AsyncFileLock for the vault.

    thread_local=False is the AsyncFileLock default but we set it
    explicitly to (a) document the intent and (b) defend against any
    future filelock release that flips the default. With thread_local=
    True, two coroutines on the same thread can corrupt the reentrant
    lock counter (Pitfall 1).
    """
    return filelock.AsyncFileLock(
        str(_lock_path_for(vault_path)),
        timeout=LOCK_TIMEOUT_SECONDS,
        thread_local=False,
        poll_interval=0.05,
    )


async def refresh_credential(
    method: AuthMethod,
    provider_id: str,
    idx: int = 0,
    *,
    vault_path: Path | None = None,
    now: float | None = None,
    force: bool = False,
) -> Credential:
    """Refresh the credential at (provider_id, idx) inside the file lock.

    Double-checked pattern (P0-6):
      1. Quick check OUTSIDE the lock — if not stale, return immediately.
         Avoids lock contention on the hot read path.
      2. Acquire the lock with 10 s timeout. RefreshLockTimeout on timeout.
      3. Re-load the vault inside the lock.
      4. Re-extract cred at (provider_id, idx). Re-check is_expired_buffered
         with a FRESH `now` (clock advances during the wait — using stale
         `now` would mis-classify a now-actually-expired cred as fresh).
      5. If `force=True` OR still stale, await method.refresh(cred) with
         a 15 s asyncio.wait_for timeout (P1-9 defense). Persist the
         result via save_vault. Otherwise (someone beat us to it), return
         the freshly-loaded cred.
      6. Release lock (handled by `async with`).

    For ApiKeyCredential: short-circuit step 1 (never expires). force=True
    is ignored for ApiKeyCredential (no refresh endpoint to call).

    `force=True` is the Phase 022 CLI hook — `state auth refresh <provider>`
    explicitly requests a network refresh regardless of expiry state.
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    if now is None:
        now = time.time()

    # Quick check #1 — read OUTSIDE the lock.
    vault = load_vault(vault_path)
    cred = _extract_cred(vault, provider_id, idx)
    if isinstance(cred, ApiKeyCredential):
        # API keys never expire and have no refresh endpoint.
        return cred
    if not force and not is_expired_buffered(cred, now):
        return cred

    # Acquire the per-vault lock.
    lock = _new_async_lock(vault_path)
    try:
        async with lock:
            t_acquired = time.perf_counter()
            log.debug(
                "refresh_lock.acquired",
                provider_id=provider_id,
                idx=idx,
                lock_path=str(_lock_path_for(vault_path)),
            )

            # Quick check #2 — re-read INSIDE the lock (P0-6 double-check).
            now2 = time.time()
            vault = load_vault(vault_path)
            cred = _extract_cred(vault, provider_id, idx)
            if isinstance(cred, ApiKeyCredential):
                return cred
            if not force and not is_expired_buffered(cred, now2):
                # Another process refreshed while we were waiting.
                log.info(
                    "refresh_lock.skipped_already_fresh",
                    provider_id=provider_id,
                    idx=idx,
                )
                return cred

            # Refresh with hard HTTP timeout (P1-9).
            try:
                new_cred = await asyncio.wait_for(
                    method.refresh(cred),
                    timeout=REFRESH_HTTP_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError as exc:
                log.error(
                    "refresh_lock.http_timeout",
                    provider_id=provider_id,
                    idx=idx,
                    timeout=REFRESH_HTTP_TIMEOUT_SECONDS,
                )
                raise TimeoutError(
                    f"AuthMethod.refresh for {provider_id}[{idx}] exceeded "
                    f"{REFRESH_HTTP_TIMEOUT_SECONDS}s"
                ) from exc

            # Persist atomically (Phase 012's save_vault handles fsync + rename).
            vault.providers[provider_id][idx] = new_cred
            save_vault(vault_path, vault)

            log.info(
                "refresh_lock.refreshed",
                provider_id=provider_id,
                idx=idx,
                lock_held_seconds=time.perf_counter() - t_acquired,
            )
            return new_cred
    except filelock.Timeout as exc:
        raise RefreshLockTimeout(_lock_path_for(vault_path)) from exc


def _extract_cred(vault: AuthVault, provider_id: str, idx: int) -> Credential:
    """Helper — extract cred at (provider_id, idx); KeyError-friendly."""
    try:
        return vault.providers[provider_id][idx]
    except KeyError as exc:
        raise KeyError(
            f"No credentials for provider_id={provider_id!r} in vault"
        ) from exc
    except IndexError as exc:
        raise IndexError(
            f"Credential index {idx} out of range for "
            f"provider_id={provider_id!r} (have {len(vault.providers.get(provider_id, []))})"
        ) from exc
```

### Pattern 2: Reader-Side Brief Lock Acquisition

**What:** `read_credential(provider_id, idx, now=None)` briefly acquires the same lock to load-and-slice the vault, then releases. Total held duration is sub-millisecond (no I/O beyond the local SSD read).

**Why:** Phase 012's `os.replace`-based atomic write guarantees readers see *either* old-or-new, never a half-written file (Pitfall 7 in Phase 012's research). But "old" means "the about-to-expire credential" — the reader will then issue an HTTPS request that 401s mid-stream. By acquiring the lock briefly, the reader blocks for at most one in-flight refresh window (≤15 s + overhead) and then sees the post-refresh credential. Throughput cost is negligible because refreshes are rare (every 5 min × N providers).

**When to use:** Every "give me a usable credential" call from Phase 014's HTTP path, Phase 019's round-robin selector, Phase 022's CLI. **NOT** from Phase 020's log filter (would deadlock — log filter runs inside `refresh.py`'s own log calls).

**Example:**

```python
async def read_credential(
    provider_id: str,
    idx: int = 0,
    *,
    vault_path: Path | None = None,
    now: float | None = None,
) -> Credential:
    """Read a credential, blocking briefly if a refresh is in flight.

    Does NOT trigger a refresh. Returns the credential as it sits in
    the vault. Caller is responsible for checking expiry and calling
    refresh_credential when needed (Phase 014's HTTP send-path follows
    "read → check_expiry → refresh_if_needed" in that order).

    The brief lock acquisition prevents the "read just-stale credential"
    race when a refresh is in progress: by waiting our turn, we either
    see the pre-refresh value (refresh hasn't started yet, fine — caller
    will trigger one), or the post-refresh value (refresh finished while
    we waited, perfect — caller skips the refresh on expiry check).
    """
    if vault_path is None:
        vault_path = get_auth_json_path()

    lock = _new_async_lock(vault_path)
    try:
        async with lock:
            vault = load_vault(vault_path)
            return _extract_cred(vault, provider_id, idx)
    except filelock.Timeout as exc:
        raise RefreshLockTimeout(_lock_path_for(vault_path)) from exc
```

**Note:** A future optimization (NOT for v2) would split into reader-writer locks via `filelock.AsyncReadWriteLock` — multiple concurrent readers, exclusive writers. For v2 we use the simple exclusive lock; the contention cost is invisible at our scale.

### Pattern 3: `is_expired_buffered` — the canonical 5-minute-buffer check

**What:** A pure function that takes a `Credential` + `now` + optional buffer, returns `True` iff the OAuth credential is within `buffer` seconds of expiring. ApiKeyCredential always returns `False`.

**Why:** Phase 011 deliberately put `is_expired` on the `AuthMethod` Protocol (per-provider) to allow provider-specific logic — but in practice every OAuth provider does the same thing: `now >= expires - 300.0`. Phase 014–017's `is_expired` should *delegate* to this function so the math lives in exactly one place. Phase 020's log redactor and Phase 022's CLI need an "expires soon?" check without an `AuthMethod` instance handy — they call `is_expired_buffered` directly.

**Example:**

```python
def is_expired_buffered(
    cred: Credential,
    now: float,
    buffer: float = EXPIRY_BUFFER_SECONDS,
) -> bool:
    """Return True iff cred is within `buffer` seconds of expiring.

    For OAuthCredential: `now >= cred.expires - buffer`. The wire-shape
    `expires` is the value returned by the OAuth server — Phase 011
    Pattern 3 mandates we store the wire value, not the buffer-shaved
    value, so captured-header regression tests (Phase 022 / AUTH-13)
    can verify `cred.expires - issue_time == response.expires_in`.

    For ApiKeyCredential: always False. API keys have no expiry concept.

    For provider implementations (Phase 014–017): your AuthMethod.is_expired
    should delegate here:

        def is_expired(self, cred, now):
            return is_expired_buffered(cred, now)

    This keeps the 300-second magic number in exactly one place. AUTH-09
    audit grep is a single-callsite check.
    """
    if isinstance(cred, ApiKeyCredential):
        return False
    # cred.type == "oauth" — OAuthCredential branch.
    return now >= cred.expires - buffer
```

**Critical:** `now` is always a parameter. Never `time.time()` inside this function. Determinism rule (Phase 011 cardinal). Public entry points (`refresh_credential`, `read_credential`) default `now=None` and bind once to `time.time()` at the boundary.

### Pattern 4: Public API surface

```python
# src/state_core/auth/refresh.py — public exports

__all__ = [
    "EXPIRY_BUFFER_SECONDS",
    "LOCK_TIMEOUT_SECONDS",
    "REFRESH_HTTP_TIMEOUT_SECONDS",
    "RefreshLockTimeout",
    "is_expired_buffered",
    "read_credential",
    "refresh_credential",
]
```

Re-exported from `state_core.auth.__init__`:

```python
from state_core.auth.refresh import (
    EXPIRY_BUFFER_SECONDS,
    RefreshLockTimeout,
    is_expired_buffered,
    read_credential,
    refresh_credential,
)
```

### Anti-Patterns to Avoid

- **`asyncio.to_thread(filelock.FileLock(...).acquire)`** — works but obsolete now that `AsyncFileLock` exists. Use the native async path.
- **Holding the lock during `method.login()`** — login is interactive (user types a code), takes minutes. Lock-and-await would block every other process for the duration of the user's typing. Login does NOT go through `refresh.py`; it hits `save_vault` directly under its own ad-hoc protection (Phase 014 owns this).
- **Per-coroutine `FileLock` instance vs shared instance** — `AsyncFileLock` is reentrant within the same instance (counter-based). Sharing one `_NEW_LOCK` module-global between coroutines would let one coroutine see another's "I have the lock" state. **Always construct a new `AsyncFileLock` per call** (`_new_async_lock(...)`). Cheap (no syscall until `__aenter__`).
- **Manual `acquire()` + `try/finally release()`** — works but error-prone. `async with lock:` is the supported form; release-on-exception is automatic.
- **`time.time()` in `is_expired_buffered`** — non-deterministic; breaks Phase 011's cardinal rule; breaks the test-injectability that Phase 014–017's tests depend on.
- **Catching `Exception` around the lock body** — `filelock.Timeout` is a `TimeoutError` subclass. A bare `except Exception` would swallow other bugs. Narrow to `except filelock.Timeout` for the re-raise, let everything else propagate (Pydantic ValidationError on a corrupted vault, OS errors on disk full, AuthRefreshError from the provider).
- **Storing `expires_buffered = expires - 300` on disk** — PITFALLS.md P0-7 says "subtract before storing"; Phase 011 Pattern 3 says "store wire value, subtract on check." Phase 011 is the binding decision. PITFALLS.md was written before Phase 011 Pattern 3 was adopted; document this clearly so future-you doesn't try to "fix" it. (Open Question 4.)
- **Calling `read_credential` from a `structlog` filter** — recursive lock acquisition from inside a log call would deadlock (the log filter runs inside `refresh_credential`, which already holds the lock). The "is_expiring_soon" log field, if needed, should be computed outside the filter (in the caller) and attached as a bound logger context.
- **Leaking the lockfile** — `filelock` cleans up on `__aexit__`. Never `os.unlink` the lockfile manually; the kernel lock state is bound to the inode.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-process file lock | `fcntl.flock` + custom Windows shim | `filelock.AsyncFileLock` | TOCTOU-patched (3.20.3 floor); cross-platform; reentrant; native async; the entire stack is a committed library lock |
| Async wrapping of a sync lock | `asyncio.to_thread(lock.acquire)` | `AsyncFileLock` | Native; supports `cancel_check`; matches stdlib async-context-manager idiom |
| Stale-lock detection | Manual PID-file + heartbeat | `filelock.SoftFileLock` (if needed; not for v2) | If we ever need explicit stale-lock cleanup (e.g., for daemon-startup audit), `SoftFileLock` ships PID + hostname inside the lockfile. For v2's `AsyncFileLock` we trust the OS's `flock(2)` automatic release on process death |
| Double-check refresh pattern | `if expired: refresh()` outside lock + repeat inside | The explicit re-load-re-check inside the lock (Pattern 1 step 4) | Without it, every waiter behind the lock issues its own (now-redundant) refresh — thundering-herd against the OAuth endpoint |
| Polling for "is refresh done?" | Custom condition variable + signal | `async with lock` | The lock IS the synchronization primitive. Acquiring it after another process releases means the previous refresh is fully persisted (save_vault's atomic-rename completed). No extra signaling needed |
| Timeout on the HTTP refresh call | A separate `httpx` timeout config | `asyncio.wait_for(method.refresh(cred), timeout=15.0)` | The provider's httpx client has its own timeout, but we want a hard outer cap for P1-9 (lock-deadlock-on-shutdown defense). `wait_for` cancels the task if the timeout expires |
| `RefreshLockTimeout` from scratch | `class RefreshLockTimeout(TimeoutError):` | `class RefreshLockTimeout(filelock.Timeout)` | `filelock.Timeout` IS a `TimeoutError`. Subclassing keeps it discoverable in callers' `except filelock.Timeout` clauses while letting our specific message surface in CLI output |
| 5-minute buffer arithmetic in 5 places | Inline `now >= cred.expires - 300` everywhere | `is_expired_buffered(cred, now)` | One callsite, one source of truth. AUTH-09 audit becomes a single-grep check |

**Key insight:** Phase 013 is ~120 lines because filelock does the heavy lifting. Every "improvement" beyond the recommended pattern is a vector for the exact bug the lock was supposed to prevent (P0-6).

## Common Pitfalls

### Pitfall 1: `thread_local=True` corrupts the lock counter under asyncio
**What goes wrong:** Two coroutines on the *same thread* both call `lock.acquire()`. With `thread_local=True` (default for `FileLock`), the reentrant counter is per-thread — both coroutines see "lock acquired by my thread, increment counter," counter goes to 2, neither releases properly.
**Why it happens:** Reentrancy counters were designed for blocking threaded code, before asyncio. The `BaseFileLock` default is `thread_local=True`; `AsyncFileLock` defaults to `thread_local=False` already, but the docstring buries this detail.
**How to avoid:** Always pass `thread_local=False` explicitly when constructing `AsyncFileLock`. Document the choice in code: `# AsyncFileLock default; explicit for safety vs. future filelock releases`. Add REFRESH-NN test that asserts the construct uses `thread_local=False`.
**Warning signs:** Two concurrent `refresh_credential` calls in the same daemon process both refresh the same credential (lock counter goes to 2, neither blocks).

### Pitfall 2: Single-check (no double-check) → thundering herd refresh
**What goes wrong:** Naïve flow: caller checks `is_expired`, sees True, acquires lock, refreshes, releases. Five waiters were behind the lock — each acquires in turn, each runs the same refresh, all five hit the OAuth endpoint, four get 401s on the now-rotated refresh token. Only the first succeeds; the rest leave the vault in a broken state.
**Why it happens:** It seems redundant to re-check inside the lock. It is not — between acquire and re-check, "the world has changed" (someone refreshed).
**How to avoid:** Pattern 1 step 4 is non-negotiable. Inside the lock: `now2 = time.time(); vault = load_vault(...); cred = vault.providers[provider_id][idx]; if not is_expired_buffered(cred, now2): return cred`. Test REFRESH-NN explicitly simulates 5 concurrent waiters and asserts only one provider.refresh() invocation happens (use a counting mock).
**Warning signs:** Refresh-token rotation tests (Phase 015 Gemini) intermittently fail in CI under load. AuthMethod.refresh() call counter exceeds expected count by ≥1.

### Pitfall 3: Lock pinned by hung HTTP refresh — daemon shutdown deadlock (P1-9)
**What goes wrong:** Process A holds the lock, calls `method.refresh(cred)`, the OAuth endpoint hangs (network partition). Process B is waiting on the lock. Daemon SIGTERM arrives. Process B's lock-wait blocks shutdown — pid-file lingers, supervisor force-kills.
**Why it happens:** No upper bound on the lock-held duration. The refresh's httpx client has its own timeout but it might be configured higher than 15 s, or the network might fail in a way the timeout doesn't catch (TLS handshake stuck).
**How to avoid:** `asyncio.wait_for(method.refresh(cred), timeout=REFRESH_HTTP_TIMEOUT_SECONDS=15.0)`. Hard outer cap. On timeout, raise `TimeoutError` from inside the lock — `async with` releases on exception, waiters unblock, B's wait fails fast on its 10 s acquire timeout (cumulative ≤25 s worst case for the whole stack, well under any sensible shutdown grace). Test REFRESH-NN simulates an `AuthMethod.refresh()` that `asyncio.sleep(60)` and asserts `wait_for` raises within 16 s.
**Warning signs:** Daemon shutdown logs show "lock acquisition pending for 30+ seconds." Forensics shows two processes with same `auth.json` file in their open-fd tables.

### Pitfall 4: Reading the lockfile contents → expects "useful" payload, finds nothing
**What goes wrong:** Developer assumes the lockfile contains PID/hostname (it would for `SoftFileLock`), opens it, finds 0 bytes, files a "lockfile is broken" bug.
**Why it happens:** `FileLock`/`AsyncFileLock` use the kernel's `flock(2)` (or `LockFileEx` on Windows) which operates on the file's *open file description*, not its contents. The lockfile is empty by design; lock state lives in kernel structures keyed by (inode, fd).
**How to avoid:** Module docstring: "The lockfile (`<auth.json>.lock`) is empty by design — `flock(2)` operates on the kernel-level file description. Do not chmod it to 0600 (no secrets), do not parse it, do not delete it manually." Test REFRESH-NN asserts the lockfile is 0 bytes.
**Warning signs:** A "fix" PR adds `os.chmod(lockfile, 0o600)` or PID-writing code.

### Pitfall 5: Stale lockfile after process kill (Unix vs Windows)
**What goes wrong:** Process A is killed -9 mid-refresh. The lockfile exists on disk. Process B comes along, sees the lockfile, blocks until 10 s timeout, raises `RefreshLockTimeout`. User can't recover without `rm .state/auth.json.lock`.
**Why it happens:** On Unix, `flock(2)` is automatically released by the kernel when the holder's process dies (file descriptors are closed, locks evaporate). The lockfile *itself* may persist on disk — but a fresh `flock` attempt by B succeeds because the lock state is gone. **So this isn't actually a bug on Unix.** On Windows, `LockFileEx` releases on process death too (CloseHandle on the file releases). The "stale lockfile blocking new acquires" scenario described above is a `SoftFileLock` concern — `FileLock`/`AsyncFileLock` are immune.
**How to avoid:** Trust the kernel. Don't add manual stale-lock cleanup logic for `AsyncFileLock`. Add an integration test (REFRESH-NN, expensive — `pytest.mark.integration`) that spawns a subprocess, has it acquire the lock, kills it -9, then asserts a new acquisition succeeds within timeout.
**Warning signs:** A "fix" PR adds `os.unlink(lockfile)` cleanup logic. NFS users (P2-5) report stale-lock issues — that's a different problem (NFS doesn't honor `flock(2)` reliably; document `.state/` must be local).

### Pitfall 6: Reentrant deadlock — `read_credential` called from inside `refresh_credential`
**What goes wrong:** Phase 019 round-robin's "is this credential usable?" check naïvely calls `read_credential(provider_id, idx)` from inside its already-held lock context. Even with `thread_local=False`, AsyncFileLock's reentrancy-by-instance means a *different* AsyncFileLock instance pointing at the same file blocks. Deadlock.
**Why it happens:** Reentrancy in AsyncFileLock is per-*instance*, not per-*lockfile*. Two instances pointing at the same path don't know about each other's holdings.
**How to avoid:** Document strictly: never call `read_credential` from inside `refresh_credential` (or from inside a held lock context). For round-robin (Phase 019), construct an internal helper (`_pick_credential_inside_lock(vault, ...)`) that takes the already-loaded `vault` and operates on the in-memory state. The public API (`refresh_credential`, `read_credential`) acquires the lock; helpers don't. Add REFRESH-NN test that imports `state_core.auth.refresh` and asserts the call graph: no public function ever calls another public function while holding the lock.
**Warning signs:** A test that calls `refresh_credential(...)` then `read_credential(...)` in sequence works; but `refresh_credential(...)` that internally re-enters dies with `RefreshLockTimeout`.

### Pitfall 7: AUTH-09 conflict between PITFALLS.md and Phase 011 RESEARCH.md
**What goes wrong:** PITFALLS.md P0-7 says "subtract 5 minutes (300s) from `expires_in` before storing." Phase 011 RESEARCH.md Pattern 3 says "store the wire value; subtract in `is_expired`." A reader of both could implement either, get inconsistent code, and break AUTH-13's captured-header regression test (which expects `cred.expires - issue_time == response.expires_in`).
**Why it happens:** PITFALLS.md was written before Phase 011's deliberate "store wire value" decision. The two docs disagree.
**How to avoid:** **Phase 011 is the binding decision** — `OAuthCredential.expires` stores the wire value. The 5-minute buffer lives in `is_expired_buffered` (this phase). Document the conflict in the module docstring ("see also: Phase 011 RESEARCH §Pattern 3") so future contributors find the resolution. Test REFRESH-NN asserts: `is_expired_buffered(cred, now=cred.expires - 301)` is False; `is_expired_buffered(cred, now=cred.expires - 299)` is True. Open question carried to PLAN.md for explicit confirmation.
**Warning signs:** A future PR "fixes P0-7" by subtracting 300 in Phase 014's `login()` path. AUTH-13 golden-file diff fails.

### Pitfall 8: NFS/SMB `.state/` defeats the lock (P2-5)
**What goes wrong:** User has `~/Projects/state` on NFS (corporate setup, network home). `flock(2)` on NFS is implementation-defined — may not be atomic; may not block across hosts. Two refreshes on different hosts race; P0-6 returns.
**Why it happens:** `flock(2)` on NFS pre-NFSv4 is broken. Even NFSv4's `OPEN_DELEGATION` doesn't fully implement Linux `flock` semantics.
**How to avoid:** Document in module docstring: "`.state/` MUST be on a local filesystem. NFS/SMB defeats `filelock`'s atomicity guarantee." Phase A6 daemon boot is the right place to detect (`/proc/mounts` parse on Linux, `mount` parse on macOS, `Get-PSDrive` on Windows) and warn/refuse. Phase 013 doesn't enforce — too far from the boot sequence — but the docstring carries the warning. Test REFRESH-NN is a documentation-comment check ("module docstring mentions NFS").
**Warning signs:** Multi-host setups report "token invalidation" issues. Forensics shows multiple `auth.json` writes within 1 second from different hostnames.

### Pitfall 9: Force-refresh path bypasses the double-check — fine in principle, surprise-edge in practice
**What goes wrong:** `state auth refresh anthropic` from the CLI with `force=True` always issues an HTTPS refresh. If the user ran the CLI three times in a row, three refreshes hit the endpoint, three sets of refresh tokens get rotated. Two tokens are now invalid (the user typed too many times).
**Why it happens:** `force=True` deliberately skips the double-check. That's the contract.
**How to avoid:** Document on the CLI side (Phase 022): `state auth refresh` should debounce or warn the user that consecutive force-refreshes invalidate the in-flight token. From Phase 013's perspective, document the contract clearly: "`force=True` always issues a refresh; caller is responsible for not calling it in tight loops." Test REFRESH-NN: with `force=True`, a non-expired credential triggers a refresh exactly once.
**Warning signs:** User's CLI history shows three `auth refresh` calls in 2 seconds; subsequent operations 401 on the now-invalidated middle tokens.

## Code Examples

### Example 1: Full refresh.py module skeleton (~120 lines)

```python
"""Cross-process refresh coordination via filelock.AsyncFileLock.

Phase 013 (M-A2 / AUTH-07 + AUTH-09 / P0-6 + P0-7 owner): the lock layer
that wraps every credential mutation, with a double-checked refresh
pattern to defend against thundering herd, and a reader-side brief
acquisition to prevent stale reads during the refresh window.

Cardinal rules:

  1. Lock per-vault, not per-provider — simpler, sufficient for v2.

  2. Double-checked refresh: re-load + re-check INSIDE the held lock
     before issuing the HTTPS refresh. Without it, every waiter behind
     the lock thunders the OAuth endpoint (P0-6).

  3. 5-minute buffer (AUTH-09) lives in `is_expired_buffered`, applied
     against the wire-shape `cred.expires`. Phase 011 Pattern 3 is the
     binding decision — store wire value, subtract on check. (See
     Pitfall 7 — PITFALLS.md P0-7 and Phase 011 disagree; Phase 011
     wins.)

  4. AsyncFileLock with thread_local=False — explicit, even though it's
     the default, to defend against future filelock releases that flip
     the default. (Pitfall 1.)

  5. 15s outer asyncio.wait_for cap on AuthMethod.refresh — defense
     against P1-9 daemon-shutdown deadlock.

  6. .state/ must be on a local filesystem. NFS/SMB defeats flock(2).
     Phase A6 daemon-boot is the enforcement point; this module just
     warns in the docstring (P2-5).

  7. Mode isolation — imports limited to stdlib, filelock, structlog,
     state_core.auth.base, state_core.auth.store. NO state_build/teach.

See .planning/milestones/v2/phases/013-filelock-guarded-refresh-lock/
013-RESEARCH.md for full rationale, 9 pitfalls, downstream contracts.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import filelock
import structlog

from state_core.auth.base import (
    ApiKeyCredential,
    AuthMethod,
    Credential,
)
from state_core.auth.store import (
    AuthVault,
    get_auth_json_path,
    load_vault,
    save_vault,
)

log = structlog.get_logger(__name__)

LOCK_SUFFIX = ".lock"
LOCK_TIMEOUT_SECONDS = 10.0
REFRESH_HTTP_TIMEOUT_SECONDS = 15.0
EXPIRY_BUFFER_SECONDS = 300.0


# ── Exceptions ──────────────────────────────────────────────────────────


class RefreshLockTimeout(filelock.Timeout):
    """Raised when the refresh lock could not be acquired within 10 s.

    Subclass of filelock.Timeout (itself a TimeoutError subclass) — so
    callers can `except RefreshLockTimeout` (specific) or
    `except TimeoutError` (broad). Carries the offending lockfile path.
    """

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        super().__init__(str(lock_path))

    def __str__(self) -> str:
        return (
            f"Could not acquire {self.lock_path} within "
            f"{LOCK_TIMEOUT_SECONDS}s — another process may be refreshing."
        )


# ── Helpers ─────────────────────────────────────────────────────────────


def _lock_path_for(vault_path: Path) -> Path:
    return vault_path.with_name(vault_path.name + LOCK_SUFFIX)


def _new_async_lock(vault_path: Path) -> filelock.AsyncFileLock:
    """Construct an AsyncFileLock with documented defaults."""
    return filelock.AsyncFileLock(
        str(_lock_path_for(vault_path)),
        timeout=LOCK_TIMEOUT_SECONDS,
        thread_local=False,  # explicit; see Pitfall 1
        poll_interval=0.05,
    )


def _extract_cred(vault: AuthVault, provider_id: str, idx: int) -> Credential:
    if provider_id not in vault.providers:
        raise KeyError(f"No credentials for provider_id={provider_id!r}")
    bucket = vault.providers[provider_id]
    if idx < 0 or idx >= len(bucket):
        raise IndexError(
            f"Credential index {idx} out of range for "
            f"provider_id={provider_id!r} (have {len(bucket)})"
        )
    return bucket[idx]


# ── Public API ──────────────────────────────────────────────────────────


def is_expired_buffered(
    cred: Credential,
    now: float,
    buffer: float = EXPIRY_BUFFER_SECONDS,
) -> bool:
    """Pure: True iff *cred* is within `buffer` seconds of expiring.

    See module docstring rule 3. ApiKeyCredential always returns False.
    """
    if isinstance(cred, ApiKeyCredential):
        return False
    return now >= cred.expires - buffer


async def read_credential(
    provider_id: str,
    idx: int = 0,
    *,
    vault_path: Path | None = None,
) -> Credential:
    """Read a credential, briefly acquiring the lock to avoid stale reads.

    Does NOT trigger refresh. Caller checks expiry separately.
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    lock = _new_async_lock(vault_path)
    try:
        async with lock:
            vault = load_vault(vault_path)
            return _extract_cred(vault, provider_id, idx)
    except filelock.Timeout as exc:
        raise RefreshLockTimeout(_lock_path_for(vault_path)) from exc


async def refresh_credential(
    method: AuthMethod,
    provider_id: str,
    idx: int = 0,
    *,
    vault_path: Path | None = None,
    now: float | None = None,
    force: bool = False,
) -> Credential:
    """Refresh credential at (provider_id, idx) with double-check pattern.

    Returns the post-refresh credential (or the unchanged credential if
    another process beat us to it). Raises RefreshLockTimeout if the
    lock cannot be acquired within 10 s. Raises TimeoutError if the
    HTTPS refresh exceeds 15 s.
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    if now is None:
        now = time.time()

    # Quick check #1 — outside the lock, hot path.
    vault = load_vault(vault_path)
    cred = _extract_cred(vault, provider_id, idx)
    if isinstance(cred, ApiKeyCredential):
        return cred
    if not force and not is_expired_buffered(cred, now):
        return cred

    # Acquire and double-check inside.
    lock = _new_async_lock(vault_path)
    try:
        async with lock:
            t0 = time.perf_counter()
            now2 = time.time()
            vault = load_vault(vault_path)
            cred = _extract_cred(vault, provider_id, idx)
            if isinstance(cred, ApiKeyCredential):
                return cred
            if not force and not is_expired_buffered(cred, now2):
                log.info(
                    "refresh_lock.skipped_already_fresh",
                    provider_id=provider_id, idx=idx,
                )
                return cred

            try:
                new_cred = await asyncio.wait_for(
                    method.refresh(cred),
                    timeout=REFRESH_HTTP_TIMEOUT_SECONDS,
                )
            except asyncio.TimeoutError as exc:
                log.error(
                    "refresh_lock.http_timeout",
                    provider_id=provider_id, idx=idx,
                )
                raise TimeoutError(
                    f"AuthMethod.refresh for {provider_id}[{idx}] "
                    f"exceeded {REFRESH_HTTP_TIMEOUT_SECONDS}s"
                ) from exc

            vault.providers[provider_id][idx] = new_cred
            save_vault(vault_path, vault)
            log.info(
                "refresh_lock.refreshed",
                provider_id=provider_id, idx=idx,
                lock_held_seconds=time.perf_counter() - t0,
            )
            return new_cred
    except filelock.Timeout as exc:
        raise RefreshLockTimeout(_lock_path_for(vault_path)) from exc


__all__ = [
    "EXPIRY_BUFFER_SECONDS",
    "LOCK_TIMEOUT_SECONDS",
    "REFRESH_HTTP_TIMEOUT_SECONDS",
    "RefreshLockTimeout",
    "is_expired_buffered",
    "read_credential",
    "refresh_credential",
]
```

### Example 2: Provider delegation (Phase 014 preview)

```python
# Phase 014: src/state_core/auth/providers/anthropic_oauth.py
from state_core.auth.refresh import is_expired_buffered

class AnthropicOAuth:
    provider_id = "anthropic"

    def is_expired(self, cred: Credential, now: float) -> bool:
        # Delegate to the canonical buffer-aware check (Phase 013).
        return is_expired_buffered(cred, now)
```

### Example 3: Phase 019 round-robin call site

```python
# Phase 019 — preview only.
from state_core.auth.refresh import (
    is_expired_buffered, refresh_credential, read_credential,
)

async def get_usable_credential(provider_id: str, methods: dict[str, AuthMethod]) -> Credential:
    # Read briefly to inspect rotation index.
    cred = await read_credential(provider_id, idx=0)
    # Round-robin selects an idx; refresh_credential handles staleness.
    method = methods[provider_id]
    return await refresh_credential(method, provider_id, idx=picked_idx)
```

### Example 4: CLI force-refresh path (Phase 022 preview)

```python
# state auth refresh <provider>  --force / --idx N
async def cli_refresh(provider_id: str, idx: int = 0, force: bool = True) -> None:
    method = providers.match_provider(provider_id)
    new_cred = await refresh_credential(method, provider_id, idx, force=force)
    print(f"Refreshed {provider_id}[{idx}] — new expiry {new_cred.expires}")
```

### Example 5: Concurrent-refresh test harness pattern (asyncio.gather)

```python
# tests/auth/test_refresh.py — concurrency proof (REFRESH-NN)
async def test_double_check_prevents_thundering_herd(
    auth_json_path, vault_with_one_oauth, monkeypatch,
):
    """5 concurrent refresh_credential calls → exactly 1 method.refresh()."""
    save_vault(auth_json_path, vault_with_one_oauth)
    monkeypatch.setenv("STATE_AUTH_JSON", str(auth_json_path))

    refresh_calls = 0
    class CountingMethod:
        provider_id = "anthropic"
        async def refresh(self, cred):
            nonlocal refresh_calls
            refresh_calls += 1
            await asyncio.sleep(0.01)  # let other waiters queue
            return cred.model_copy(update={"expires": cred.expires + 3600})
        # ... other Protocol methods stub-implemented

    method = CountingMethod()
    # Make the cred expire NOW so all 5 see "stale" at quick check #1.
    expired_now = time.time() + 10  # within 5-min buffer
    # ... (modify vault to set cred.expires = expired_now) ...

    results = await asyncio.gather(*[
        refresh_credential(method, "anthropic", 0)
        for _ in range(5)
    ])

    assert refresh_calls == 1  # double-check prevented herd
    # All 5 callers got the same post-refresh credential.
    assert all(r.expires == results[0].expires for r in results)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `asyncio.to_thread(filelock.FileLock(...).acquire)` | `filelock.AsyncFileLock` | filelock 3.10+ (2024) | Native async; supports `cancel_check`; less boilerplate; matches stdlib idiom |
| Polling with `asyncio.sleep` between attempts | `await lock.acquire(timeout=10.0)` | Always best-practice | Single call; library handles backoff; cancellation-safe |
| Bare `try: yield; finally: release()` | `async with lock:` | Python 3.5+ | Release-on-exception is automatic; lock counter bookkeeping is the lock's responsibility |
| `time.time()` inside `is_expired` | `now: float` parameter | Phase 011 cardinal rule | Determinism; replay-bit-identicalness; test-injectable |
| Subtract buffer at storage | Subtract buffer at check | Phase 011 Pattern 3 (this project) | Wire-shape `expires` round-trips through AUTH-13 captured-header regression unmodified |
| Per-provider lockfiles | Per-vault single lock | Architectural choice (this project) | Simpler; fewer stale-lock paths; sufficient for our scale |
| `filelock.Timeout` re-raised verbatim | `RefreshLockTimeout(filelock.Timeout)` | Project convention | User-facing error message points at the lockfile + remediation |

**Deprecated/outdated:**
- `asyncio.wait_for` was removed-then-readded debates in 3.11 — in 3.12 it's stable and the recommended timeout primitive (we use it for the 15 s HTTP cap).
- `filelock.SoftFileLock` for our use case — better stale-lock recovery on paper, but `AsyncFileLock`'s kernel-backed `flock(2)` is atomic by syscall and that's worth more than the soft variant's PID-aware cleanup.

## Open Questions

1. **Should `refresh_credential` accept an explicit `lock_timeout` parameter?**
   - What we know: AUTH-07 mandates 10 s. The default-only API is simpler.
   - What's unclear: Phase 022 CLI's `state auth refresh --timeout 30` UX would be nice for slow networks.
   - Recommendation: Defer to Phase 022. Phase 013 ships fixed 10 s constant; Phase 022 may add a CLI flag that overrides at the call site (requires Phase 013 to expose `lock_timeout` as a kwarg with `LOCK_TIMEOUT_SECONDS` default — trivial future change).
   - **Status:** Recommend SHIPPING fixed; planner can defer the kwarg.

2. **Should `cancel_check` be wired for SIGTERM-aware acquisition?**
   - What we know: AsyncFileLock's `acquire(cancel_check=callable)` polls a callback during the wait. Returning True raises `Timeout` early.
   - What's unclear: Whether Phase A6 daemon shutdown should plumb a "shutdown-requested" predicate through to refresh.py.
   - Recommendation: Defer to Phase A6. The 10 s timeout is short enough that SIGTERM handlers will typically finish their grace period before the lock acquire times out. If SIGTERM-during-acquisition becomes a measured problem, Phase A6 owns the wiring.
   - **Status:** Defer.

3. **Should the lockfile path live under `.state/locks/auth.json.lock` instead of `.state/auth.json.lock`?**
   - What we know: Some systems (e.g., backup tools) treat dotfiles next to the protected file as "noise" and copy them; subdirectory placement is tidier.
   - What's unclear: Whether Phase 022's `state auth status` would prefer to ignore everything under `.state/locks/`.
   - Recommendation: Keep next-to-vault for v2 (matches GSD-pi precedent and ARCHITECTURE.md §10.3 example "filelock(auth_json_path)"). If a future phase wants to organize locks, move at that point.
   - **Status:** Resolved — next-to-vault.

4. **Is there a real disagreement between PITFALLS.md P0-7 and Phase 011 Pattern 3?**
   - What we know: PITFALLS.md P0-7 says "subtract 5 minutes from `expires_in` before storing." Phase 011 RESEARCH §Pitfall 3 explicitly chose option (b) — "store wire value, subtract on check."
   - What's unclear: Whether PITFALLS.md should be patched to reflect Phase 011's binding decision.
   - Recommendation: Phase 011 wins (it's later, more specific, owns the data model). Add a note to PITFALLS.md as a discrete planner action item, OR simply document in `refresh.py`'s docstring + Pitfall 7 here. Code-level test (REFRESH-NN: `is_expired_buffered(cred, cred.expires - 301)` is False; `... - 299` is True) prevents regression either way.
   - **Status:** Recommend Phase 013 implements Phase 011's decision; planner files a follow-up to patch PITFALLS.md (out of scope for this phase).

5. **Should `refresh_credential` log the `provider_id`'s human-readable name (e.g., "Anthropic") or the canonical id ("anthropic")?**
   - What we know: Structlog records use stable keys; `provider_id` is the canonical id everywhere else.
   - What's unclear: Phase 020's redactor will read these log records — does it need a friendly name?
   - Recommendation: Log canonical id only. Friendly names are a UI concern (Phase 022 CLI / Phase TUI). `provider_id="anthropic"` is grep-stable across log corpora.
   - **Status:** Resolved — canonical id.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest>=8.4.0` + `pytest-asyncio>=1.3.0` (`asyncio_mode = "auto"`) + `hypothesis>=6.120` + `pytest-mock>=3.14` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/auth/test_refresh.py -x -q` |
| Full suite command | `python3 -m pytest -q` |

### Phase Requirements → Test Map

| Test ID | Behavior | Test Type | Automated Command | File Exists? |
|---------|----------|-----------|-------------------|--------------|
| REFRESH-01 | `is_expired_buffered(oauth_cred, now=expires-301)` returns False; `now=expires-299` returns True (5-min buffer pure check, AUTH-09) | unit | `pytest tests/auth/test_refresh.py::test_is_expired_buffered_boundary -x` | Wave 0 |
| REFRESH-02 | `is_expired_buffered(api_key_cred, now=anything)` returns False unconditionally | unit | `pytest tests/auth/test_refresh.py::test_is_expired_buffered_api_key_never_expires -x` | Wave 0 |
| REFRESH-03 | `is_expired_buffered` does NOT call `time.time()` (determinism — patch `time.time` to raise; assert function still works) | unit | `pytest tests/auth/test_refresh.py::test_is_expired_buffered_no_clock_read -x` | Wave 0 |
| REFRESH-04 | `RefreshLockTimeout` is a subclass of `filelock.Timeout` AND `TimeoutError` (caller compatibility) | unit | `pytest tests/auth/test_refresh.py::test_refresh_lock_timeout_hierarchy -x` | Wave 0 |
| REFRESH-05 | `RefreshLockTimeout.lock_path` carries the offending path; `str(exc)` mentions both the path and the 10 s timeout | unit | `pytest tests/auth/test_refresh.py::test_refresh_lock_timeout_message -x` | Wave 0 |
| REFRESH-06 | `_lock_path_for(vault_path)` returns `<vault_path>.lock` (next-to-vault, NOT a subdir) | unit | `pytest tests/auth/test_refresh.py::test_lock_path_next_to_vault -x` | Wave 0 |
| REFRESH-07 | `_new_async_lock` constructs an AsyncFileLock with `thread_local=False` (Pitfall 1) | unit | `pytest tests/auth/test_refresh.py::test_async_lock_thread_local_false -x` | Wave 0 |
| REFRESH-08 | `_new_async_lock` constructs an AsyncFileLock with `timeout=10.0` and `poll_interval=0.05` | unit | `pytest tests/auth/test_refresh.py::test_async_lock_construct_defaults -x` | Wave 0 |
| REFRESH-09 | `read_credential` on existing fresh OAuth cred returns it without invoking `method.refresh` | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_read_credential_returns_fresh -x` | Wave 0 |
| REFRESH-10 | `read_credential` raises `KeyError` for unknown provider_id | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_read_credential_unknown_provider -x` | Wave 0 |
| REFRESH-11 | `read_credential` raises `IndexError` for out-of-range idx | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_read_credential_bad_index -x` | Wave 0 |
| REFRESH-12 | `read_credential` briefly acquires the lock (verified by mocking `_new_async_lock` to assert `__aenter__` was called) | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_read_credential_acquires_lock -x` | Wave 0 |
| REFRESH-13 | `refresh_credential` on fresh OAuth cred (not within buffer) does NOT call `method.refresh` (quick-check optimization) | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_refresh_credential_skips_when_fresh -x` | Wave 0 |
| REFRESH-14 | `refresh_credential` on stale OAuth cred calls `method.refresh` exactly once and persists the result | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_refresh_credential_refreshes_stale -x` | Wave 0 |
| REFRESH-15 | `refresh_credential` with `force=True` on a fresh cred still calls `method.refresh` | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_refresh_credential_force_bypasses_quickcheck -x` | Wave 0 |
| REFRESH-16 | `refresh_credential` on `ApiKeyCredential` returns it unchanged WITHOUT calling refresh (and WITHOUT acquiring the lock — performance + correctness) | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_refresh_credential_apikey_short_circuit -x` | Wave 0 |
| REFRESH-17 | Double-check pattern: 5 concurrent `refresh_credential` calls on the same stale cred → `method.refresh` invoked exactly ONCE; all 5 callers receive the same post-refresh cred (P0-6 owned) | unit (asyncio + counting mock) | `pytest tests/auth/test_refresh.py::test_double_check_prevents_thundering_herd -x` | Wave 0 |
| REFRESH-18 | `refresh_credential` raises `RefreshLockTimeout` when lock is held by another process for >10 s (simulated via `multiprocessing.Process` holding the lock) | integration | `pytest tests/auth/test_refresh.py::test_refresh_credential_lock_timeout -x -m integration` | Wave 0 |
| REFRESH-19 | `refresh_credential` raises `TimeoutError` (NOT `RefreshLockTimeout`) when `method.refresh` exceeds 15 s (P1-9 deadlock defense) | unit (asyncio + mock that sleeps) | `pytest tests/auth/test_refresh.py::test_refresh_credential_http_timeout -x` | Wave 0 |
| REFRESH-20 | After `refresh_credential` exception (e.g., method.refresh raises), the lock is RELEASED (next acquire succeeds within 10 s) | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_refresh_credential_releases_lock_on_exception -x` | Wave 0 |
| REFRESH-21 | After process kill mid-lock-hold (subprocess SIGKILL), a new `refresh_credential` call from the parent acquires within timeout (kernel auto-release of `flock`) | integration | `pytest tests/auth/test_refresh.py::test_killed_process_releases_lock -x -m integration` | Wave 0 |
| REFRESH-22 | Lockfile (`<vault>.lock`) is 0 bytes (Pitfall 4 — empty by design) | unit | `pytest tests/auth/test_refresh.py::test_lockfile_is_empty -x` | Wave 0 |
| REFRESH-23 | Mode isolation — `import state_core.auth.refresh` does NOT pull `state_build.*` or `state_teach.*` into `sys.modules` | unit | `pytest tests/auth/test_refresh.py::test_no_mode_imports -x` | Wave 0 |
| REFRESH-24 | `refresh_credential` updates the in-vault credential at the correct `(provider_id, idx)` slot (not slot 0 hard-coded) | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_refresh_credential_updates_correct_slot -x` | Wave 0 |
| REFRESH-25 | After `refresh_credential` completes, the saved vault round-trips: `load_vault` returns a vault whose cred-at-(provider_id, idx) is the new credential (writes are durable, P0-13 atomic-rename guarantee) | unit (asyncio) | `pytest tests/auth/test_refresh.py::test_refresh_credential_durable_write -x` | Wave 0 |
| REFRESH-26 | Hypothesis property: any `(now, expires)` pair where `now < expires - 300` returns False; `now >= expires - 300` returns True (boundary correctness) | unit (property) | `pytest tests/auth/test_refresh.py::test_hypothesis_buffer_boundary -x` | Wave 0 |
| REFRESH-27 | Reentrancy guard — calling `read_credential` from inside a `refresh_credential` `async with lock` block deadlocks (catches Pitfall 6 if someone re-introduces the bug — assert `RefreshLockTimeout` raised within 11 s) | unit (asyncio, slow ~10 s) | `pytest tests/auth/test_refresh.py::test_no_self_reentry -x -m slow` | Wave 0 |
| REFRESH-28 | Module docstring mentions NFS/SMB warning (P2-5 documentation defense) | unit (docstring grep) | `pytest tests/auth/test_refresh.py::test_module_warns_about_nfs -x` | Wave 0 |
| REFRESH-29 | Logging — `refresh_credential` emits `refresh_lock.acquired` + `refresh_lock.refreshed` structlog events with `lock_held_seconds` field (P1-9 observability) | unit (structlog capture) | `pytest tests/auth/test_refresh.py::test_emits_acquisition_logs -x` | Wave 0 |
| REFRESH-30 | Public exports: `state_core.auth` re-exports `refresh_credential, read_credential, is_expired_buffered, RefreshLockTimeout, EXPIRY_BUFFER_SECONDS` | unit | `pytest tests/auth/test_refresh.py::test_public_exports -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/auth/test_refresh.py -x -q -m "not integration"` (< 3 seconds expected; integration tests excluded for speed)
- **Per wave merge:** `python3 -m pytest tests/auth/ -q` (full auth subsuite including refresh)
- **Phase gate:** `python3 -m pytest -q && python3 -m pytest tests/auth/test_refresh.py -m integration -q && mypy src/state_core/auth/` clean before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/auth/test_refresh.py` — covers REFRESH-01..REFRESH-30 (does not exist; sibling to existing `test_base.py` and `test_store.py`)
- [ ] Extend `tests/auth/conftest.py` — add `expired_oauth_cred` fixture (cred with `expires = now_frozen + 10` so `is_expired_buffered(cred, now_frozen)` is True), `vault_with_expired_oauth` fixture, and `mock_auth_method` fixture (counting-mock `AuthMethod` for concurrency tests). All fixtures use `pytest.importorskip("state_core.auth.refresh")` per the conftest pattern established for Phase 012 (RED-then-GREEN test discipline).
- [ ] Add `pytest.mark.integration` and `pytest.mark.slow` markers to `pyproject.toml [tool.pytest.ini_options].markers` if not already present (REFRESH-18, REFRESH-21, REFRESH-27 are excluded by default).
- [ ] No new test framework install — `pytest`, `pytest-asyncio`, `hypothesis`, `pytest-mock` already in `pyproject.toml [project.optional-dependencies] dev`.

### Concurrency Test Strategy

**Question 10 from objective:** how to simulate concurrent refresh attempts deterministically?

Three layers, increasing in cost and realism:

1. **`asyncio.gather(*[refresh_credential(...) for _ in range(N)])` (REFRESH-17)** — fastest. All N coroutines run on the same event loop, the same process, and contend on the *same* `AsyncFileLock` instance via the shared on-disk lockfile. Reentrancy-by-instance means each construct gets a fresh AsyncFileLock object that contends through the kernel's `flock(2)`. Counting-mock for `method.refresh` proves the double-check works: assert `refresh_calls == 1` after all 5 return.

2. **Threaded test with `threading.Thread` + `asyncio.run` per thread (optional supplementary REFRESH-NN-T)** — proves cross-thread correctness. Each thread runs its own event loop; both contend on the same lockfile via separate AsyncFileLock instances. Slower (~50 ms) but stresses the kernel-level lock more than asyncio.gather does.

3. **`multiprocessing.Process`-based integration test (REFRESH-18, REFRESH-21)** — realistic. Parent spawns a child process; child acquires the lock and `time.sleep(15)` (longer than the 10 s timeout). Parent attempts `refresh_credential`, asserts `RefreshLockTimeout` raised within 10 s ± 1 s. REFRESH-21 variant: parent SIGKILLs child mid-hold, asserts subsequent acquire succeeds (kernel auto-release).

Hypothesis property tests are appropriate for REFRESH-26 (pure boundary math) and could optionally fuzz the `(now, expires, buffer)` triple. They are **not** appropriate for the concurrency tests — coroutine interleavings are not Hypothesis's strong suit; explicit barrier-based tests are clearer.

**Avoid:** `pytest-asyncio`'s `run_in_executor` with manual `Lock()` — that tests Python's threading, not our filelock. Use the real `AsyncFileLock` against a real lockfile in a `tmp_path`.

## Sources

### Primary (HIGH confidence)
- `/Users/tmac/Projects/state/.planning/PROJECT.md` — cardinal rules (mode isolation, determinism, library locks)
- `/Users/tmac/Projects/state/.planning/research/STACK.md` — `filelock>=3.20.3` (CVE-2026-22701 floor); pinning rationale
- `/Users/tmac/Projects/state/.planning/research/ARCHITECTURE.md` §10.3 — the canonical refresh-lock flow ("filelock(auth_json_path)" + double-check)
- `/Users/tmac/Projects/state/.planning/research/PITFALLS.md` — P0-6 (concurrent refresh race) [owned], P0-7 (5-min buffer) [owned], P1-8 (round-robin starvation, deferred to Phase 019), P1-9 (lock + shutdown deadlock) [defense], P2-5 (NFS lock weakness) [documented]
- `/Users/tmac/Projects/state/.planning/milestones/v2/REQUIREMENTS.md` — AUTH-07, AUTH-09 spec text
- `/Users/tmac/Projects/state/.planning/milestones/v2/phases/011-state-core-auth-base/011-RESEARCH.md` — Pattern 3 (deterministic clock injection); §Pitfall 3 ("store wire value, subtract on check") — the binding decision for AUTH-09
- `/Users/tmac/Projects/state/.planning/milestones/v2/phases/012-auth-json-vault-chmod-0600/012-RESEARCH.md` — Pattern 5 (Phase 013 preview) confirms `<auth.json>.lock` location and `from filelock import FileLock` import shape
- `/Users/tmac/Projects/state/src/state_core/auth/store.py` — actual `load_vault`, `save_vault`, `get_auth_json_path`, `AuthVault` (sync API; lock-friendly per Phase 012's design)
- `/Users/tmac/Projects/state/src/state_core/auth/base.py` — `Credential`, `OAuthCredential`, `ApiKeyCredential`, `AuthMethod` Protocol
- `/Users/tmac/Projects/state/src/state_core/auth/__init__.py` — re-export pattern Phase 013 must extend
- `/Users/tmac/Projects/state/tests/auth/conftest.py` — existing `auth_json_path`, `oauth_cred`, `api_key_cred`, `now_frozen`, `clean_state_auth_json_env` fixtures Phase 013 builds on
- `/Users/tmac/Projects/state/pyproject.toml` — `filelock>=3.20.3` already pinned; mypy strict; pytest-asyncio auto

### Secondary (MEDIUM confidence — verified by introspection of installed filelock 3.29.0)
- `filelock.AsyncFileLock.__init__` signature — `thread_local: bool = False`, `run_in_executor: bool = True`, `poll_interval: float = 0.05` (verified via `inspect.signature`)
- `filelock.Timeout.__mro__` — `(Timeout, TimeoutError, OSError, Exception, ...)` — verified `RefreshLockTimeout(filelock.Timeout)` is also a `TimeoutError` subclass
- `filelock.AsyncFileLock.__aenter__` / `__aexit__` exist — verified async context manager support
- [py-filelock readthedocs API](https://py-filelock.readthedocs.io/en/latest/api.html) — confirmed AsyncFileLock async-context-manager support, `cancel_check` parameter semantics, `flock(2)` kernel-backed primary mechanism
- [filelock changelog + CVE-2026-22701 advisory](https://py-filelock.readthedocs.io/en/latest/changelog.html) — version-floor justification

### Tertiary (LOW confidence — flagged for validation)
- Stale-lock auto-release on Unix process death — based on Linux `flock(2)` man page semantics (locks released on file-descriptor close; FDs close on process death); verified by behavior, not by official documentation. REFRESH-21 integration test will validate.
- AsyncFileLock under `pytest-asyncio strict mode` — no published incidents but no explicit pytest-asyncio docs either. Mitigation: REFRESH-17 stresses N=5 concurrent coroutines and is the canary.
- NFS `flock(2)` brokenness — well-known folklore (P2-5 documented). Behavior depends on NFS version and client/server combo. Out of scope for v2.

## Metadata

**Confidence breakdown:**
- Standard stack (`filelock`, `structlog`, `state_core.auth.base/store`): **HIGH** — all pinned, all verified by introspection, all consumed elsewhere in the codebase
- AsyncFileLock async-context-manager pattern: **HIGH** — verified in installed filelock 3.29.0, documented in readthedocs
- Double-checked refresh pattern (P0-6 owner): **HIGH** — direct mapping from PITFALLS.md prevention text + ARCHITECTURE.md §10.3 example
- 5-minute buffer placement (P0-7 owner, AUTH-09): **HIGH for the formula**, **MEDIUM for the upstream-doc resolution** (PITFALLS.md vs Phase 011 disagreement; Phase 011 binds, but the planner should explicitly confirm during planning)
- Reader-side brief lock (Pattern 2): **MEDIUM** — judgment call. Phase 012's atomic-rename means readers never see corruption; the brief lock prevents stale-read-then-401 only. Acceptable cost (≤15 s worst case during a refresh; refreshes happen every ~5 min). Alternative: skip the reader lock and rely on caller-side retry-on-401. Recommend pattern 2 for v2; revisit if benchmarks show contention.
- 15 s HTTP wait_for cap (P1-9 defense): **HIGH** — direct from PITFALLS.md prevention text
- Per-vault vs per-provider lock: **MEDIUM** — judgment call. Per-vault is simpler; per-provider is theoretically more concurrent but solves a problem we don't observably have.
- Concurrency test strategy: **HIGH** — `asyncio.gather` for the unit case + `multiprocessing.Process` for the integration case is the standard pattern; counting mocks prove correctness without flakiness

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (filelock API frozen at 3.x; PROJECT.md / Phase 011 binding decisions stable; only a Phase 011 reversal would invalidate Pitfall 7's resolution)

## RESEARCH COMPLETE
