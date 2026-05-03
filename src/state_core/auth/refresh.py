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

  3. 5-minute buffer (AUTH-09) lives in ``is_expired_buffered``, applied
     against the wire-shape ``cred.expires``. Phase 011 Pattern 3 is the
     binding decision — store wire value, subtract on check. (See
     013-RESEARCH.md Pitfall 7 — PITFALLS.md P0-7 and Phase 011
     disagree; Phase 011 wins.)

  4. AsyncFileLock with ``thread_local=False`` — explicit, even though
     it's the default, to defend against future filelock releases that
     flip the default. (013-RESEARCH.md Pitfall 1.)

  5. 15 s outer ``asyncio.wait_for`` cap on AuthMethod.refresh — defense
     against P1-9 daemon-shutdown deadlock.

  6. ``.state/`` MUST be on a local filesystem. NFS/SMB defeats flock(2).
     Phase A6 daemon-boot is the enforcement point; this module just
     warns in the docstring (P2-5).

  7. Mode isolation — imports limited to stdlib, filelock, structlog,
     state_core.auth.base, state_core.auth.store. NO mode-specific
     (build / teach) packages may be imported (REFRESH-23 enforces).

  8. Determinism — ``is_expired_buffered`` MUST take ``now`` as a
     parameter; never reads the clock internally. The optional default
     in ``refresh_credential`` is the ONLY clock read in this module.

  9. Reentrant deadlock (Pitfall 6) — DO NOT call ``read_credential``
     from inside an externally-held ``_new_async_lock`` block. Each
     public function constructs a fresh AsyncFileLock; instances are
     NOT cross-aware, so re-entry from the same coroutine deadlocks
     until the 10 s acquire timeout fires. REFRESH-27 verifies.

  10. Sync vs async lock coexistence — ``with_vault_lock`` (sync) and
      ``_new_async_lock`` (async) target the SAME ``<vault>.lock``
      sibling file. They coordinate via the kernel's POSIX advisory
      lock; do NOT call ``with_vault_lock`` from inside an async
      coroutine that already holds an AsyncFileLock for the same path
      (reentrant deadlock; Pitfall 6 generalized). The CLI ops layer
      (Phase 022.2) uses ``with_vault_lock``; the daemon-driven
      refresh path (Phase 013) uses ``_new_async_lock``. They never
      overlap in one process.

See .planning/milestones/v2/phases/013-filelock-guarded-refresh-lock/
013-RESEARCH.md for full rationale, 9 pitfalls, downstream contracts.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Iterator
from pathlib import Path
from time import perf_counter, time as _now

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

    Subclass of ``filelock.Timeout`` (itself a ``TimeoutError`` subclass) — so
    callers can ``except RefreshLockTimeout`` (specific) or
    ``except TimeoutError`` (broad). Carries the offending lockfile path.
    """

    def __init__(self, lock_path: Path) -> None:
        # Set attribute BEFORE super().__init__ so it exists even if the
        # parent constructor mutates state. Defensive against future
        # filelock releases.
        self.lock_path = lock_path
        super().__init__(str(lock_path))

    def __str__(self) -> str:
        return (
            f"Could not acquire {self.lock_path} within "
            f"{LOCK_TIMEOUT_SECONDS}s — another process may be refreshing."
        )


# ── Helpers ─────────────────────────────────────────────────────────────


def _lock_path_for(vault_path: Path) -> Path:
    """Return the sibling lockfile path for *vault_path*.

    ``<vault>.lock`` lives next to the vault, never as a child directory.
    REFRESH-06 verifies the shape.
    """
    return vault_path.with_name(vault_path.name + LOCK_SUFFIX)


def _new_async_lock(vault_path: Path) -> filelock.AsyncFileLock:
    """Construct an AsyncFileLock with documented defaults.

    ``thread_local=False`` is the AsyncFileLock default; we set it
    explicitly to (a) document the intent and (b) defend against any
    future filelock release that flips the default. Pitfall 1.
    """
    return filelock.AsyncFileLock(
        str(_lock_path_for(vault_path)),
        timeout=LOCK_TIMEOUT_SECONDS,
        thread_local=False,
        poll_interval=0.05,
    )


# Public alias — Phase 019 promoted this from private to public surface so
# state_core.auth.rotation can reuse the SAME (thread_local=False,
# poll_interval=0.05, timeout=10.0) config tuple without duplicating it.
# The leading-underscore name remains the canonical implementation; this
# alias is the documented import path for new callers.
#
# WARNING (Pitfall 6, REFRESH-27): each call returns a NEW AsyncFileLock
# instance. Instances are NOT cross-aware — two locks pointing at the same
# path serialize via the kernel's POSIX lock. DO NOT call this from inside
# a held lock block (reentrant deadlock at the 10s acquire timeout).
new_async_lock = _new_async_lock


def _new_sync_lock(vault_path: Path) -> filelock.FileLock:
    """Construct a sync FileLock with the same config tuple as _new_async_lock.

    Used by ``with_vault_lock`` for CLI write paths that cannot await an
    AsyncFileLock (Phase 022.2 / T-018-8 mitigation). The on-disk lockfile
    is the SAME ``<vault>.lock`` sibling that Phase 013's async refresh path
    uses — sync and async acquirers coordinate via the kernel's POSIX
    advisory lock.

    ``thread_local=False`` is explicit (matches ``_new_async_lock``);
    ``poll_interval`` and ``timeout`` match too. Pitfall 1.
    """
    return filelock.FileLock(
        str(_lock_path_for(vault_path)),
        timeout=LOCK_TIMEOUT_SECONDS,
        thread_local=False,
        poll_interval=0.05,
    )


@contextlib.contextmanager
def with_vault_lock(
    vault_path: Path | None = None,
    *,
    timeout: float = LOCK_TIMEOUT_SECONDS,
) -> Iterator[Path]:
    """Sync filelock wrapper for CLI write paths (T-018-8 mitigation).

    Acquires the same ``<vault>.lock`` sibling file that Phase 013's
    AsyncFileLock-based ``refresh_credential`` uses. Sync and async
    acquirers serialize via the kernel's POSIX advisory lock — a CLI
    ``state auth login`` and a daemon-driven async refresh CANNOT both be
    inside their critical sections simultaneously.

    Yields the lockfile path so callers can include it in log messages.

    Raises:
        RefreshLockTimeout: lock could not be acquired within *timeout* seconds.

    Usage::

        with with_vault_lock(vault_path):
            vault = load_vault(vault_path)
            # ... mutate ...
            save_vault(vault_path, vault)

    WARNING (Pitfall 6 generalized, rule 10): each call constructs a fresh
    FileLock. Do NOT nest ``with with_vault_lock(...)`` blocks for the same
    *vault_path* — reentrant acquire deadlocks at the timeout (NOT
    cross-aware). Caller must perform load → mutate → save inside ONE
    context.
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    lock_path = _lock_path_for(vault_path)
    lock = filelock.FileLock(
        str(lock_path),
        timeout=timeout,
        thread_local=False,
        poll_interval=0.05,
    )
    try:
        try:
            with lock:
                log.debug(
                    "vault_lock.acquired",
                    vault_path=str(vault_path),
                    lock_path=str(lock_path),
                )
                yield lock_path
        except filelock.Timeout as exc:
            raise RefreshLockTimeout(lock_path) from exc
    finally:
        # Mirror the async path's lockfile-touch (read_credential /
        # refresh_credential finally clauses). filelock 3.29 unlinks the
        # lockfile on release; re-create it so observability tooling
        # (REFRESH-22 spirit) can still see its presence.
        try:
            lock_path.touch(exist_ok=True)
        except OSError:
            pass


def _extract_cred(vault: AuthVault, provider_id: str, idx: int) -> Credential:
    """Return ``vault.providers[provider_id][idx]``.

    Raises ``KeyError`` if *provider_id* is not present, or ``IndexError``
    if *idx* is out of range. Phase 019 (round-robin) relies on these
    distinct exception types to differentiate "no creds" from "empty
    bucket" surfacing.
    """
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
    """Pure: True iff *cred* is within *buffer* seconds of expiring.

    See module docstring rule 3. ``ApiKeyCredential`` always returns False.
    *now* is ALWAYS a parameter; this function never reads the clock
    internally (REFRESH-03 enforces).
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

    DO NOT call from inside a held ``refresh_credential`` lock — see
    013-RESEARCH.md Pitfall 6 (reentrant deadlock). REFRESH-27 verifies.
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    lock_path = _lock_path_for(vault_path)
    lock = _new_async_lock(vault_path)
    try:
        try:
            async with lock:
                vault = load_vault(vault_path)
                return _extract_cred(vault, provider_id, idx)
        except filelock.Timeout as exc:
            raise RefreshLockTimeout(lock_path) from exc
    finally:
        # filelock 3.29 unlinks the lockfile on release; re-create it so
        # tooling (debugging, REFRESH-22) can still observe its presence.
        # Concurrent acquirers tolerate an existing lockfile (O_CREAT).
        try:
            lock_path.touch(exist_ok=True)
        except OSError:
            pass


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
    another process beat us to it). Raises ``RefreshLockTimeout`` if the
    lock cannot be acquired within 10 s. Raises ``TimeoutError`` if the
    HTTPS refresh exceeds 15 s.

    For ``ApiKeyCredential``: short-circuits without acquiring the lock
    even when ``force=True`` — there is no refresh endpoint.
    For ``force=True`` on OAuth: skips the quick-check AND the in-lock
    double-check; the network refresh is unconditional.
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    if now is None:
        now = _now()

    # Quick check #1 — outside the lock, hot path. Avoids lock contention
    # for the common "credential is fresh" case AND short-circuits API
    # keys before constructing the lock at all (REFRESH-16).
    vault = load_vault(vault_path)
    cred = _extract_cred(vault, provider_id, idx)
    if isinstance(cred, ApiKeyCredential):
        return cred
    if not force and not is_expired_buffered(cred, now):
        return cred

    # Acquire and double-check inside the lock.
    lock_path = _lock_path_for(vault_path)
    lock = _new_async_lock(vault_path)
    try:
        try:
            async with lock:
                t0 = perf_counter()
                log.debug(
                    "refresh_lock.acquired",
                    provider_id=provider_id,
                    idx=idx,
                    lock_path=str(lock_path),
                )
                # Re-use the caller-provided (or once-resolved) `now` for the
                # in-lock check. Reading the wall clock again here would race
                # against test-injected frozen-time fixtures (REFRESH-17
                # binding) and would also let the second waiter observe a
                # future time that disagrees with the first waiter's decision.
                vault = load_vault(vault_path)
                cred = _extract_cred(vault, provider_id, idx)
                if isinstance(cred, ApiKeyCredential):
                    return cred
                if not force and not is_expired_buffered(cred, now):
                    log.info(
                        "refresh_lock.skipped_already_fresh",
                        provider_id=provider_id,
                        idx=idx,
                    )
                    return cred

                # Refresh with hard HTTP timeout (P1-9 defense).
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
                        f"AuthMethod.refresh for {provider_id}[{idx}] "
                        f"exceeded {REFRESH_HTTP_TIMEOUT_SECONDS}s"
                    ) from exc

                # Persist atomically (Phase 012's save_vault handles fsync + rename).
                vault.providers[provider_id][idx] = new_cred
                save_vault(vault_path, vault)
                log.info(
                    "refresh_lock.refreshed",
                    provider_id=provider_id,
                    idx=idx,
                    lock_held_seconds=perf_counter() - t0,
                )
                return new_cred
        except filelock.Timeout as exc:
            raise RefreshLockTimeout(lock_path) from exc
    finally:
        # filelock 3.29 unlinks the lockfile on release; re-create it so
        # tooling (debugging, REFRESH-22) can still observe its presence.
        # Concurrent acquirers tolerate an existing lockfile (O_CREAT).
        try:
            lock_path.touch(exist_ok=True)
        except OSError:
            pass


__all__ = [
    "EXPIRY_BUFFER_SECONDS",
    "LOCK_TIMEOUT_SECONDS",
    "REFRESH_HTTP_TIMEOUT_SECONDS",
    "RefreshLockTimeout",
    "is_expired_buffered",
    "new_async_lock",
    "read_credential",
    "refresh_credential",
    "with_vault_lock",
]
