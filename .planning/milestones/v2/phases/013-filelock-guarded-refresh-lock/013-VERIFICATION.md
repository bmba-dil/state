---
phase: 013-filelock-guarded-refresh-lock
verified: 2026-04-28T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification:
  is_re_verification: false
---

# Phase 013: Filelock-guarded refresh lock — Verification Report

**Phase Goal:** "10s acquire, re-read auth.json, double-check expiry, refresh only if still stale, write, release; reader-path blocks refresher."

**Requirements:** AUTH-07, AUTH-09 (and internal REFRESH-01..REFRESH-30)

**P0 pitfalls owned:** P0-6 (concurrent refresh / token clobber), P0-7 (5-minute expiry buffer)

**Verified:** 2026-04-28
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                                                                       | Status     | Evidence                                                                                                                                                                                                                                                |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Two concurrent refresh_credential calls on the same expired credential trigger exactly ONE outbound AuthMethod.refresh (P0-6 owned)                                          | ✓ VERIFIED | `test_double_check_prevents_thundering_herd` PASSED — 5 concurrent `asyncio.gather` calls produce `mock_auth_method.refresh_calls == 1` and identical `expires` across all 5 results.                                                                    |
| 2   | `is_expired_buffered(cred, now)` returns True iff `now >= cred.expires - 300.0`; `OAuthCredential.expires` retains wire value (no buffer subtracted at storage; AUTH-09 / P0-7) | ✓ VERIFIED | `test_is_expired_buffered_boundary` + `test_hypothesis_buffer_boundary` PASSED. `EXPIRY_BUFFER_SECONDS = 300.0` (refresh.py:77). Buffer applied only in `is_expired_buffered` (refresh.py:154-167); `cred.expires` is never mutated in storage path.       |
| 3   | When the lock cannot be acquired within 10s, `refresh_credential` raises `RefreshLockTimeout` (subclass of `filelock.Timeout` AND `TimeoutError`) naming the lockfile path (AUTH-07) | ✓ VERIFIED | `test_refresh_lock_timeout_hierarchy` + `test_refresh_lock_timeout_message` + `test_refresh_credential_lock_timeout` PASSED. `LOCK_TIMEOUT_SECONDS = 10.0` (refresh.py:75). MRO confirmed; `__str__` includes `lock_path` and `10`.                       |
| 4   | When AuthMethod.refresh hangs >15s, `refresh_credential` raises `TimeoutError` (NOT `RefreshLockTimeout`); the lock is released (P1-9 mitigated)                              | ✓ VERIFIED | `test_refresh_credential_http_timeout` PASSED in <16s; `not isinstance(excinfo.value, RefreshLockTimeout)` asserted. `asyncio.wait_for(method.refresh(cred), timeout=REFRESH_HTTP_TIMEOUT_SECONDS)` (refresh.py:272-274). `async with` releases on raise. |
| 5   | `read_credential` briefly acquires the same lock, blocking only during an active refresh window (no half-written-vault reads)                                                  | ✓ VERIFIED | `test_read_credential_acquires_lock` PASSED — spy `__aenter__`/`__aexit__` awaited. Same `_new_async_lock(vault_path)` used in both readers and writers. `test_no_self_reentry` (slow ~10s) confirms reader contends on the same lockfile.            |
| 6   | On exception inside the held lock, the async-with releases the lock — a subsequent `refresh_credential` call acquires within timeout (no deadlock)                            | ✓ VERIFIED | `test_refresh_credential_releases_lock_on_exception` PASSED — RuntimeError surfaces, second call within `asyncio.wait_for(..., timeout=10.0)` succeeds.                                                                                                  |
| 7   | All 30 REFRESH-NN tests GREEN — including REFRESH-17 (concurrent herd), REFRESH-19 (HTTP timeout), REFRESH-20 (release on exception); integration+slow tests pass when selected | ✓ VERIFIED | `pytest tests/auth/test_refresh.py -v` → 30 passed in 35.85s. Integration + slow markers collected/run successfully (3 marked).                                                                                                                          |
| 8   | `state_core.auth.refresh` imports only stdlib + filelock + structlog + state_core.auth.{base,store} — NO state_build/state_teach imports (mode isolation)                      | ✓ VERIFIED | `test_no_mode_imports` PASSED — `importlib.reload` of `state_core.auth.refresh` introduces zero `state_build.*`/`state_teach.*` keys. Confirmed by inspection of refresh.py:51-70 imports.                                                                |
| 9   | `state_core.auth` re-exports `refresh_credential, read_credential, is_expired_buffered, RefreshLockTimeout, EXPIRY_BUFFER_SECONDS` (plus `LOCK_TIMEOUT_SECONDS`, `REFRESH_HTTP_TIMEOUT_SECONDS`) | ✓ VERIFIED | `test_public_exports` PASSED. `__init__.py` lines 22-30 import all 7 symbols; `__all__` lines 54-61 list them.                                                                                                                                            |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact                              | Expected                                                                                                                                                              | Status     | Details                                                                                                                                                                                       |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/state_core/auth/refresh.py`      | `refresh_credential, read_credential, is_expired_buffered, RefreshLockTimeout, _new_async_lock, _lock_path_for, _extract_cred, EXPIRY_BUFFER_SECONDS, LOCK_TIMEOUT_SECONDS, REFRESH_HTTP_TIMEOUT_SECONDS` (≥130 lines, contains `async def refresh_credential`) | ✓ VERIFIED | 318 lines. All public + private symbols present. `async def refresh_credential` at line 204. Module docstring carries `NFS/SMB` warning (line 29).                                              |
| `src/state_core/auth/__init__.py`     | Re-exports of Phase 013 surface alongside Phase 011/012                                                                                                              | ✓ VERIFIED | 62 lines; section "# Phase 013 — refresh" lists all 7 names in `__all__` (lines 54-61). Imports at lines 22-30.                                                                              |
| `tests/auth/test_refresh.py`           | 30 RED→GREEN tests for REFRESH-01..REFRESH-30, ≥350 lines, contains `def test_is_expired_buffered_boundary`                                                            | ✓ VERIFIED | 780 lines. All 30 tests present and PASSING. `test_is_expired_buffered_boundary` at line 102.                                                                                                |
| `tests/auth/conftest.py`               | `expired_oauth_cred`, `vault_with_expired_oauth`, `mock_auth_method` fixtures appended; existing 6 fixtures preserved                                               | ✓ VERIFIED | 161 lines; Phase 013 fixtures at lines 82-160. `mock_auth_method` self-asserts `isinstance(instance, AuthMethod)` (line 157). Phase 011/012 fixtures untouched.                                  |
| `pyproject.toml`                       | `[tool.pytest.ini_options].markers` registers `integration` and `slow`                                                                                                | ✓ VERIFIED | Both markers present; `integration: multi-process or cross-process tests`, `slow: tests that intentionally wait for timeouts`.                                                                  |

All artifacts: ✓ EXIST, ✓ SUBSTANTIVE, ✓ WIRED.

---

### Key Link Verification

| From                                | To                                | Via                                                                                                          | Status   | Details                                                                                                                                                              |
| ----------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------ | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/state_core/auth/refresh.py`    | `src/state_core/auth/store.py`    | `from state_core.auth.store import AuthVault, get_auth_json_path, load_vault, save_vault`                     | ✓ WIRED  | refresh.py:65-70. `load_vault` invoked at lines 233 + 258; `save_vault` at line 290; `get_auth_json_path` at lines 184, 226.                                          |
| `src/state_core/auth/refresh.py`    | `src/state_core/auth/base.py`     | `from state_core.auth.base import ApiKeyCredential, AuthMethod, Credential`                                  | ✓ WIRED  | refresh.py:60-64. `ApiKeyCredential` checked at lines 165, 235, 260; `AuthMethod` typed in `refresh_credential` signature; `Credential` typed in helpers.            |
| `src/state_core/auth/refresh.py`    | `filelock`                        | `filelock.AsyncFileLock(timeout=10.0, thread_local=False, poll_interval=0.05)`                                | ✓ WIRED  | refresh.py:124-129. All three kwargs explicit. `filelock.Timeout` caught at lines 192, 298; subclassed by `RefreshLockTimeout` at line 83.                          |
| `src/state_core/auth/refresh.py`    | `asyncio`                         | `asyncio.wait_for(method.refresh(cred), timeout=15.0)`                                                       | ✓ WIRED  | refresh.py:272-274. `REFRESH_HTTP_TIMEOUT_SECONDS = 15.0` (line 76). `asyncio.TimeoutError` caught at line 276; converted to plain `TimeoutError`.                    |
| `src/state_core/auth/__init__.py`   | `src/state_core/auth/refresh.py`  | `from state_core.auth.refresh import refresh_credential, read_credential, is_expired_buffered, RefreshLockTimeout, EXPIRY_BUFFER_SECONDS` | ✓ WIRED  | `__init__.py:22-30` imports all 7 symbols (incl. `LOCK_TIMEOUT_SECONDS`, `REFRESH_HTTP_TIMEOUT_SECONDS`). REFRESH-30 test passes.                                     |
| `tests/auth/test_refresh.py`        | `src/state_core/auth/refresh`     | `from state_core.auth import refresh`                                                                          | ✓ WIRED  | test_refresh.py:55. `_REFRESH_AVAILABLE` is True; module-level `pytestmark.skipif` does NOT skip — all 30 tests run and pass.                                          |
| `tests/auth/test_refresh.py`        | `tests/auth/conftest.py`          | pytest fixture lookup (oauth_cred, api_key_cred, now_frozen, auth_json_path, vault_with_one_oauth, expired_oauth_cred, vault_with_expired_oauth, mock_auth_method) | ✓ WIRED  | All 8 fixtures consumed across the 30 tests. `mock_auth_method` self-check passes at fixture build time.                                                              |

All key links: ✓ WIRED.

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                                                                              | Status      | Evidence                                                                                                                                                                              |
| ----------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AUTH-07     | 013-01, 013-02 | "Filelock-guarded refresh: acquire lock (10s timeout), re-read auth.json, double-check expiry, refresh only if stale, write, release"                  | ✓ SATISFIED | All 6 sub-steps implemented in `refresh_credential` (refresh.py:204-307): acquire (line 245) → re-read (line 258) → double-check (line 262) → refresh-if-stale (line 272) → write (line 290) → release (`async with` exit). 10s timeout via `LOCK_TIMEOUT_SECONDS = 10.0`. Verified by REFRESH-13..21. |
| AUTH-09     | 013-01, 013-02 | "Access token renewal 5 minutes before expires_in (never verbatim)"                                                                                       | ✓ SATISFIED | `EXPIRY_BUFFER_SECONDS = 300.0` (line 77); `is_expired_buffered` at line 154-167 applies `now >= cred.expires - buffer`. Phase 011 Pattern 3 (wire-shape `expires`) preserved — no field mutation in storage. Verified by REFRESH-01, REFRESH-02, REFRESH-03, REFRESH-26. |
| REFRESH-01..30 | 013-01, 013-02 | Internal contract IDs from RESEARCH.md / VALIDATION.md                                                                                                   | ✓ SATISFIED | All 30 tests in `tests/auth/test_refresh.py` PASS (30/30 in 35.85s). Each test maps 1:1 to a REFRESH-NN ID via inline comment.                                                       |

**P0 pitfalls owned:**

| Pitfall ID | Description                                                | Status      | Evidence                                                                                                                            |
| ---------- | ---------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| P0-6       | Concurrent refresh / token clobber                          | ✓ SATISFIED | Cross-process `filelock.AsyncFileLock` + double-checked re-read inside lock. Verified by REFRESH-17 (5-coroutine herd → 1 refresh) and REFRESH-18 (multi-process timeout). |
| P0-7       | 5-minute expiry buffer (placement)                          | ✓ SATISFIED | Buffer lives only in `is_expired_buffered`; wire-shape `OAuthCredential.expires` round-trips unchanged. Verified by REFRESH-01, REFRESH-26. |

No orphaned requirements detected.

---

### Anti-Patterns Found

| File                                          | Line | Pattern                                          | Severity | Impact                                                                                                                                                                             |
| --------------------------------------------- | ---- | ------------------------------------------------ | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/state_core/auth/refresh.py`              | 55   | `from time import perf_counter, time as _now`    | ℹ️ Info  | Executor used local-binding import instead of `import time`. Documented rule (cardinal rule 8) explicitly permits one clock read as the `now` default in `refresh_credential`. `is_expired_buffered` remains pure (never reads clock). REFRESH-03 monkeypatches `time.time` only on `is_expired_buffered`, which never invokes `_now()`. Tests always inject `now=now_frozen` explicitly, so the local-binding choice does not affect test outcomes. The PROJECT.md determinism rule targets event handlers / replay; `refresh_credential` is an I/O coordination function, not an event handler. **Not a circumvention** of the determinism rule but worth noting for downstream consumers (Phase 014–017 providers should always pass `now=` explicitly to keep behavior deterministic across replays). |

No blocker or warning anti-patterns. No `TODO`/`FIXME`/`PLACEHOLDER` markers. No empty handlers, no console-only implementations.

---

### Step 7b: Quality Findings

Skipped (quality.level: fast)

---

### Other Observations

- **013-01-SUMMARY.md missing.** Only `013-02-SUMMARY.md` exists in the phase directory. Plan 01 produced the test stubs + fixtures + markers without writing its summary. Not a blocker — both plans' artifacts are present and verified against the codebase, and Plan 02's summary covers the integrated outcome. Recommend creating `013-01-SUMMARY.md` retroactively for hygiene, but does not affect goal achievement.
- **Lockfile re-creation hack (refresh.py:198-201, 304-307).** `filelock` 3.29 unlinks the lockfile on release; the executor added a `finally` clause that re-creates a 0-byte lockfile via `Path.touch(exist_ok=True)` so REFRESH-22 (`test_lockfile_is_empty`) can observe its presence after the operation. This is a tooling/observability convenience and does not affect the lock semantics — `flock(2)` operates on the open file descriptor, not the inode. Worth documenting as a non-functional choice that could surprise future readers.
- **Test runtime: 35.85s** for 30 tests. Dominated by `test_no_self_reentry` (slow marker, ~10s deliberate wait) and `test_refresh_credential_lock_timeout` (integration, ~10s subprocess hold) and `test_refresh_credential_http_timeout` (~15s `wait_for` cap). Consistent with VALIDATION.md estimates.
- **Full auth suite (Phase 011 + 012 + 013):** 62 passed, 1 skipped — no regressions.
- **Non-auth suite:** 321 passed — no cross-package regressions.

---

### Human Verification Required

None — all phase contracts are programmatically verified through the 30 REFRESH-NN tests, including:
- Cross-process behavior (REFRESH-18, REFRESH-21 via `multiprocessing.spawn`)
- Concurrency (REFRESH-17 via `asyncio.gather`)
- Timing-sensitive behavior (REFRESH-19 HTTP-timeout cap, REFRESH-27 self-reentry deadlock)
- Filesystem state (REFRESH-22 lockfile size, REFRESH-25 durable write)
- Observability (REFRESH-29 via `structlog.testing.capture_logs`)

---

### Gaps Summary

No gaps. Phase 013 achieves its goal: filelock-guarded refresh with 10s acquire, re-read auth.json, double-check expiry, refresh only if stale, write, release; reader-path contends on the same lock. AUTH-07 + AUTH-09 + P0-6 + P0-7 all satisfied. Phases 014–017 (OAuth providers) can build against this stable, tested layer.

---

_Verified: 2026-04-28_
_Verifier: Claude (gsd-verifier)_
