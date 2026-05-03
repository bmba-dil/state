"""Round-robin credential selection across `vault.providers[provider_id]`.

Phase 019 (M-A2 / AUTH-08 owner): consumes Phase 012's `last_rotation`
field, Phase 013's filelock, and Phase 018's vault-vs-env loader to
pick the next credential for a provider — with cool-down skip on 429
fallback, time-bucketed fairness against refresh-lock convoy (P1-8),
and array-shape preservation through every selection (P1-7).

Cardinal rules (mirrors loader.py / refresh.py):

  1. Mode isolation — imports limited to stdlib + filelock + structlog
     + state_core.auth.{base, store, refresh, errors}. NO state.build.*
     NO state.teach.*. ROTATE-21 enforces.

  2. Determinism — no datetime.now() / random.* reads internally. The
     clock is injected via `now: float` parameters; the public-default
     arm reads `time.time()` ONCE at the public-API boundary (mirrors
     refresh.refresh_credential's `now=_now()` line).

  3. last_rotation as SEED for time-bucketed rotation (RESEARCH §Pattern 1):
     `(int(now*1000) // BUCKET_MS + seed) % n`. Bumped on every selection
     so successive calls in the same time bucket fan out via cool-down
     skip. Modulo clamp on the seed read (`seed % n`) defends against
     stale `last_rotation >= len(creds)` after Phase 022 logout shrinks
     the array (Pitfall 5 / ROTATE-11).

  4. Cool-down is in-memory only (RESEARCH §Pattern 3). The
     `_COOL_DOWN: dict[tuple[str, int], float]` module-level singleton
     maps `(provider_id, idx)` to `until_epoch_seconds`. Daemon restart
     clears all cool-downs (acceptable per Pitfall 6 — documented).
     Pytest tests must use the `_clear_cool_down` autouse fixture
     (tests/auth/conftest.py) for isolation.

  5. Reentrant deadlock (RESEARCH §Pitfall 2 / ROTATE-20) — DO NOT call
     `select_credential` from inside an externally-held `new_async_lock`
     block. Each public function constructs a fresh AsyncFileLock;
     instances are NOT cross-aware, so re-entry from the same coroutine
     deadlocks until the 10s acquire timeout fires.

  6. Caller-driven 429 fallback (RESEARCH §Pattern 4) — `select_credential`
     returns ONE `(idx, cred)` pair. Caller invokes the API; on 429 the
     caller calls `mark_rate_limited(provider_id, idx, until=...)` and
     re-calls `select_credential`. Rotation module owns no httpx; v3
     Provider Routing owns the retry loop.

Downstream consumers:
  * v3 milestone (Provider Routing) — primary consumer; injects
    `select_credential` + `refresh_credential` + httpx into one call site.
  * Phase 022 CLI — `state auth status` uses `iter_active_credentials`
    for diagnostic rendering.

See .planning/milestones/v2/phases/019-multi-cred-round-robin-across/
019-RESEARCH.md for the full rationale, 14 pitfalls, and the
P0/P1/P2/P3 ratings of every concurrency edge case.
"""

from __future__ import annotations

from pathlib import Path
from time import perf_counter, time as _now
from typing import Iterator

import filelock
import structlog

from state_core.auth.base import Credential
from state_core.auth.errors import NoCredentialsAvailableError
from state_core.auth.refresh import (
    RefreshLockTimeout,
    _lock_path_for,
    new_async_lock,
)
from state_core.auth.store import (
    AuthVault,
    get_auth_json_path,
    load_vault,
    save_vault,
)

log = structlog.get_logger(__name__)

BUCKET_MS: int = 60_000
"""Bucket width in milliseconds. 60s balances rotation responsiveness
against last_rotation write churn. RESEARCH §Pattern 1."""

# Daemon-process-local — see RESEARCH §Pattern 3. NEVER persisted.
# Pytest tests clear via the `_clear_cool_down` autouse fixture
# (tests/auth/conftest.py).
_COOL_DOWN: dict[tuple[str, int], float] = {}


# Re-bind the lock factory locally so tests can monkeypatch
# `state_core.auth.rotation._new_async_lock` without touching the refresh
# module's binding (ROTATE-19, ROTATE-20). The public alias `new_async_lock`
# is the documented import path; `_new_async_lock` is the rebindable
# private mirror.
_new_async_lock = new_async_lock


# ── Helpers (private) ────────────────────────────────────────────────────


def _bucket_index(now_seconds: float, n: int, seed: int) -> int:
    """Return the cred-array index for the current time bucket.

    Pure function. `seed` is `vault.last_rotation.get(provider_id, 0)` —
    rotates the bucket origin so daemons starting at the same wall-clock
    moment don't all pick idx 0 simultaneously (anti-monopoly fairness).

    Raises ValueError on n <= 0 (caller must guard).
    """
    if n <= 0:
        raise ValueError("cannot bucket-index an empty credential array")
    bucket = int(now_seconds * 1000) // BUCKET_MS
    return (bucket + seed) % n


def _is_cooled_down(provider_id: str, idx: int, now: float) -> bool:
    """Return True iff `(provider_id, idx)` is currently in cool-down.

    Side effect: auto-expires entries whose `until` has passed (so the
    dict doesn't grow forever; Pitfall 14 GC).
    """
    until = _COOL_DOWN.get((provider_id, idx))
    if until is None:
        return False
    if until <= now:
        _COOL_DOWN.pop((provider_id, idx), None)
        return False
    return True


def _purge_expired_cool_downs(provider_id: str, n: int, now: float) -> None:
    """Sweep expired cool-down entries for *provider_id* across [0, n).

    Called at the head of `_pick_active_index` so that GC happens even
    when the time-bucket short-circuits the walk (ROTATE-08 — map GC
    must occur regardless of whether the expired index is visited).
    Pitfall 14 mitigation.
    """
    for i in range(n):
        until = _COOL_DOWN.get((provider_id, i))
        if until is not None and until <= now:
            _COOL_DOWN.pop((provider_id, i), None)


def _pick_active_index(
    creds: list[Credential],
    seed: int,
    now: float,
    provider_id: str,
) -> int:
    """Return the index of the next non-cool-down cred starting from
    `_bucket_index(now, len(creds), seed)`.

    Walks the array up to `len(creds)` times. If every cred is
    cool-down-marked, raises NoCredentialsAvailableError with
    `reason="all_cooled_down"` and `earliest_available_at` set to the
    minimum cool-down expiry across the array's marked indices.

    Pitfall 4 + ROTATE-09.
    """
    n = len(creds)
    # Opportunistic GC of expired entries for this provider before the
    # walk — guarantees ROTATE-08's "past cool-down: map is GC'd" even
    # when the bucket-aligned start short-circuits the walk on offset 0.
    _purge_expired_cool_downs(provider_id, n, now)
    start = _bucket_index(now, n, seed)
    for offset in range(n):
        idx = (start + offset) % n
        if not _is_cooled_down(provider_id, idx, now):
            return idx

    # All marked — compute earliest expiry for caller's back-off.
    marked_until = [
        _COOL_DOWN[(provider_id, idx)]
        for idx in range(n)
        if (provider_id, idx) in _COOL_DOWN
    ]
    earliest = min(marked_until) if marked_until else None
    raise NoCredentialsAvailableError(
        provider_id,
        reason="all_cooled_down",
        earliest_available_at=earliest,
    )


# ── Public API — cool-down map operations ────────────────────────────────


def mark_rate_limited(provider_id: str, idx: int, *, until: float) -> None:
    """Mark `vault.providers[provider_id][idx]` as cool-down-active until *until*.

    *until* is epoch seconds (require keyword-only — RESEARCH §Open
    Question 5: forces callers to think about cool-down duration per
    provider rather than masking provider-specific Retry-After signal).

    Idempotent. `until <= 0` clears the entry (equivalent to
    `clear_rate_limited`) per ROTATE-12 contract.

    In-memory only — daemon restart clears all cool-downs (Pitfall 6).
    Logs `rotation.rate_limited` with provider_id + idx + until.
    """
    if until <= 0:
        _COOL_DOWN.pop((provider_id, idx), None)
        log.debug(
            "rotation.rate_limit_cleared",
            provider_id=provider_id,
            idx=idx,
            reason="zero_or_negative_until",
        )
        return
    _COOL_DOWN[(provider_id, idx)] = until
    log.info(
        "rotation.rate_limited",
        provider_id=provider_id,
        idx=idx,
        until=until,
    )


def clear_rate_limited(provider_id: str, idx: int) -> None:
    """Clear any cool-down entry for `(provider_id, idx)`. Idempotent."""
    if _COOL_DOWN.pop((provider_id, idx), None) is not None:
        log.debug(
            "rotation.rate_limit_cleared",
            provider_id=provider_id,
            idx=idx,
            reason="explicit_clear",
        )


# ── Private API — locked-body helper (T-019-2 structural mitigation) ─────


def _select_credential_locked(
    vault: AuthVault,
    provider_id: str,
    *,
    now: float,
) -> tuple[int, Credential]:
    """Pick the next credential and bump `vault.last_rotation` IN-PLACE.

    Caller MUST already hold the vault filelock AND have just called
    `load_vault(vault_path)` to populate *vault*. This helper performs
    the index pick + cool-down skip + last_rotation bump but does NOT
    save the vault — caller is responsible for `save_vault` (and for
    wrapping the whole sequence in `async with new_async_lock(...)`).

    Sync (not async) because the work is pure CPU + dict mutation; no
    I/O. Mirrors how Phase 013 factors `_resolve_due_creds` out of
    `refresh_credential`.

    Returns (idx, credential).

    Raises NoCredentialsAvailableError on empty array or all-cooled-down.
    See T-019-2: this seam exists so future already-locked callers can
    compose without RefreshLockTimeout. Internal-only — not in __all__.
    """
    creds = list(vault.providers.get(provider_id, []))
    if not creds:
        raise NoCredentialsAvailableError(provider_id, reason="empty")
    # Modulo-clamp the seed (Pitfall 5 / ROTATE-11).
    n = len(creds)
    seed = vault.last_rotation.get(provider_id, 0) % n
    idx = _pick_active_index(creds, seed, now, provider_id)
    # Bump for the NEXT caller; post-cool-down rounds advance
    # independently of wall-clock buckets.
    vault.last_rotation[provider_id] = (seed + 1) % n
    return idx, creds[idx]


# ── Public API — selection (the core) ────────────────────────────────────


async def select_credential(
    provider_id: str,
    *,
    vault_path: Path | None = None,
    now: float | None = None,
) -> tuple[int, Credential]:
    """Pick the next credential for *provider_id*; persist last_rotation.

    Returns (idx, credential) — caller uses idx for `mark_rate_limited`
    on 429 fallback, then re-calls.

    Args:
        provider_id: Vault key to select from.
        vault_path: Override path resolution (defaults via
            `get_auth_json_path()` honoring STATE_AUTH_JSON env var).
        now: Override the wall clock (epoch seconds). Cardinal rule 2
            — production passes None and the public-API boundary calls
            `time.time()` once.

    Raises:
        NoCredentialsAvailableError: zero creds (`reason="empty"`) OR
            every cred is currently cool-down-marked
            (`reason="all_cooled_down"`, `earliest_available_at` set).
        RefreshLockTimeout: filelock unacquireable within 10s
            (LOCK_TIMEOUT_SECONDS in refresh.py — inherited).
        AuthVaultPermissionError: auth.json mode is not 0o600 (security
            incident — propagates from `load_vault`; Phase 022 surfaces).

    DO NOT call from inside an externally-held `new_async_lock` block —
    see Pitfall 2 / ROTATE-20. For already-locked composition, call
    `_select_credential_locked(vault, provider_id, now=now)` directly
    after your own `load_vault` (and remember to `save_vault` before
    releasing your lock).
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    if now is None:
        now = _now()

    lock_path = _lock_path_for(vault_path)
    lock = _new_async_lock(vault_path)
    try:
        try:
            async with lock:
                t0 = perf_counter()
                vault = load_vault(vault_path)
                idx, cred = _select_credential_locked(
                    vault, provider_id, now=now
                )
                save_vault(vault_path, vault)
                log.debug(
                    "rotation.selected",
                    provider_id=provider_id,
                    idx=idx,
                    n=len(vault.providers.get(provider_id, [])),
                )
                log.info(
                    "rotation.persist_overhead",
                    provider_id=provider_id,
                    idx=idx,
                    lock_held_seconds=perf_counter() - t0,
                )
                return idx, cred
        except filelock.Timeout as exc:
            raise RefreshLockTimeout(lock_path) from exc
    finally:
        # filelock 3.29 unlinks the lockfile on release; re-create it
        # so tooling (debugging, lockfile inspection) can still observe
        # its presence. Mirrors refresh.read_credential / refresh_credential.
        try:
            lock_path.touch(exist_ok=True)
        except OSError:
            pass


# ── Public API — diagnostic iterator ─────────────────────────────────────


def iter_active_credentials(
    provider_id: str,
    *,
    vault_path: Path | None = None,
    now: float | None = None,
) -> Iterator[tuple[int, Credential]]:
    """Yield (idx, cred) pairs for non-cool-down creds in bucket order.

    Read-only — does NOT acquire the lock (RESEARCH §Pattern 5 + Open
    Question 6). Cool-down map is consulted against *now*.

    Use case: Phase 022 `state auth status` rendering ("5 credentials
    configured for openai, 3 active, 2 cooled down").

    Args:
        provider_id: Vault key to iterate.
        vault_path: Override path (defaults via get_auth_json_path()).
        now: Override the wall clock.

    Yields nothing if the provider has no credentials.
    """
    if vault_path is None:
        vault_path = get_auth_json_path()
    if now is None:
        now = _now()
    vault = load_vault(vault_path)
    creds = list(vault.providers.get(provider_id, []))
    if not creds:
        return
    n = len(creds)
    seed = vault.last_rotation.get(provider_id, 0) % n
    start = _bucket_index(now, n, seed)
    for offset in range(n):
        idx = (start + offset) % n
        if not _is_cooled_down(provider_id, idx, now):
            yield idx, creds[idx]


__all__ = [
    "BUCKET_MS",
    "clear_rate_limited",
    "iter_active_credentials",
    "mark_rate_limited",
    "select_credential",
]
