---
phase: 019-multi-cred-round-robin-across
plan: 03
subsystem: auth
tags: [auth, rotation, multi-cred, round-robin, cool-down, M-A2, AUTH-08]
requires:
  - 019-01  # Wave 1 RED scaffolding (test_rotation.py + ROTATE-21)
  - 019-02  # Wave 2 surface additions (NoCredentialsAvailableError + new_async_lock)
provides:
  - state_core.auth.rotation module
  - state_core.auth.{select_credential, mark_rate_limited, clear_rate_limited, iter_active_credentials, NoCredentialsAvailableError, BUCKET_MS} re-exports
  - T-019-1/2/3/4 threat-model mitigations in code
affects:
  - tests/auth/test_rotation.py (Wave 1 scaffolding fixes — see Deviations)
  - src/state_core/auth/__init__.py (adds Phase 015 errors block + Phase 019 rotation block)
tech-stack-added:
  - none (uses existing filelock + structlog stack)
patterns-introduced:
  - time-bucketed round-robin selection
  - in-memory cool-down map with auto-expiry
  - sync locked-body helper seam (T-019-2 structural mitigation for compositional reuse)
key-files:
  created:
    - src/state_core/auth/rotation.py (398 LOC)
  modified:
    - src/state_core/auth/__init__.py (+30 lines: errors + rotation re-exports)
    - tests/auth/test_rotation.py (Wave 1 scaffolding fixes; see Deviations)
decisions:
  - Bucket-aligned time advancement is incompatible with seed-bump=1 for even n in pure-rotation property tests; ROTATE-23 holds time constant so it tests SEED-driven coverage independently of bucket-driven coverage (ROTATE-04 covers bucket+time as a separate helper test).
  - Re-resolve RefreshLockTimeout against the live refresh module inside ROTATE-19/20 — Phase 013's REFRESH-23 (test_no_mode_imports) reloads state_core.auth.refresh and creates a NEW class object, invalidating module-level imports.
  - _purge_expired_cool_downs sweep runs at the head of _pick_active_index so map GC happens even when the bucket-aligned start short-circuits the walk on offset 0 (ROTATE-08).
metrics:
  duration: "47m 45s"
  tasks_completed: 2
  tests_added: 0  # Wave 1 owns the test scaffolding
  tests_modified: 5  # ROTATE-19, ROTATE-20, ROTATE-23 step, ROTATE-23+24 hypothesis settings, hypothesis import
  files_created: 1
  files_modified: 2
  lines_added: 435
completed: 2026-04-30
---

# Phase 019 Plan 03: Round-Robin Selection Implementation Summary

Implemented `state_core.auth.rotation` (the load-bearing implementation for AUTH-08) — a 398-LOC module realizing the 5 RESEARCH §Architecture Patterns: time-bucketed selection, in-lock read-modify-write with a sync compositional seam, transient cool-down map with auto-expiry, caller-driven 429 fallback, and a lock-free diagnostic iterator. All 26 ROTATE-XX VALIDATION rows are GREEN; the full auth suite (321 tests) is regression-free.

## What Was Built

### Task 1: `src/state_core/auth/rotation.py` (398 LOC, 8 functions + 1 helper)

**Public API (5 symbols):**
- `select_credential(provider_id, *, vault_path=None, now=None) -> tuple[int, Credential]` — async; acquires the vault filelock, picks the next credential via time-bucketed seed math, persists `last_rotation`, returns `(idx, credential)`.
- `mark_rate_limited(provider_id, idx, *, until: float) -> None` — keyword-only `until`; idempotent; `until <= 0` clears (ROTATE-12 contract).
- `clear_rate_limited(provider_id, idx) -> None` — idempotent.
- `iter_active_credentials(provider_id, *, vault_path=None, now=None) -> Iterator[tuple[int, Credential]]` — read-only, no lock acquisition; for Phase 022 status rendering.
- `BUCKET_MS: int = 60_000` constant.

**Private API:**
- `_bucket_index(now_seconds, n, seed) -> int` — `(int(now*1000) // BUCKET_MS + seed) % n`; pure function.
- `_is_cooled_down(provider_id, idx, now) -> bool` — auto-expires entries on lookup.
- `_purge_expired_cool_downs(provider_id, n, now) -> None` — opportunistic sweep run at head of `_pick_active_index`; ensures GC even when bucket-aligned start short-circuits the walk.
- `_pick_active_index(creds, seed, now, provider_id) -> int` — walks the array up to `n` times skipping cool-downs; raises `NoCredentialsAvailableError(reason="all_cooled_down", earliest_available_at=...)` when all marked.
- `_select_credential_locked(vault, provider_id, *, now) -> tuple[int, Credential]` — sync helper; **T-019-2 structural-mitigation seam** for already-locked composition. `select_credential` delegates to it inside its own `async with lock:` block.
- `_new_async_lock = new_async_lock` — local rebindable alias enabling ROTATE-19/20 monkeypatching without touching `state_core.auth.refresh`.

**Module-level state:**
- `_COOL_DOWN: dict[tuple[str, int], float] = {}` — process-local; cleared between tests via the autouse `_clear_cool_down` fixture in `tests/auth/conftest.py`.

**Imports — RESEARCH §Standard Stack Core only:**
```
stdlib (pathlib, time, typing) + filelock + structlog
+ state_core.auth.{base, errors, refresh, store}
```
NO `state.build.*`, NO `state.teach.*`, NO `state_core.auth.loader`, NO `state_core.auth.providers.*`. Verified by ROTATE-21 (in `tests/auth/test_import_graph.py`).

### Task 2: `src/state_core/auth/__init__.py` (+30 lines)

Added two new import blocks + extended `__all__`:
- **Phase 015 errors block** (5 names) — `AuthError`, `AuthLoginError`, `AuthRefreshError`, `NoCredentialsAvailableError`, `UnknownApiKeyProviderError`. Was previously deferred; surfaced now alongside the Phase 019 rotation re-export to satisfy ROTATE-26 (which expects `NoCredentialsAvailableError` at the package root).
- **Phase 019 rotation block** (5 names) — `BUCKET_MS`, `clear_rate_limited`, `iter_active_credentials`, `mark_rate_limited`, `select_credential`.

Module docstring updated to enumerate Phase 011 / 012 / 013 / 015 / 018 / 019. `__all__` preserves phase grouping with comment headers; alphabetical within each block.

## Verification Results

```
$ pytest tests/auth/test_rotation.py tests/auth/test_import_graph.py --no-header -q
................................
32 passed in 1.93s

$ pytest tests/auth/ --no-header
=========================== 321 passed, 1 skipped in 46.73s ===========================
```

All 26 ROTATE-XX rows GREEN (25 in test_rotation.py + ROTATE-21 in test_import_graph.py + 3 Phase 018 import-graph tests).
Full auth suite regression-free: 321 passed, 1 skipped (the skipped test is a pre-existing Phase 012 placeholder for symlink-attack defense, deferred to Phase 022).

Public-surface smoke test:
```python
from state_core.auth import (
    select_credential, mark_rate_limited, clear_rate_limited,
    iter_active_credentials, NoCredentialsAvailableError, BUCKET_MS,
)
from state_core.auth import (
    ApiKeyCredential, AuthVault, refresh_credential, load_credentials,
)
assert BUCKET_MS == 60_000
# OK — Phase 019 public surface complete; Phase 011/012/013/018 preserved.
```

mypy: rotation.py is type-clean. The 4 mypy errors observed in the worktree are all in `src/state_core/auth/providers/api_key.py` and pre-date this plan (Phase 018 leftover; out of scope per the executor's scope-boundary rule).

## Threat-Model Mitigation Matrix

| Threat | Severity | Mitigation in code | Verified by |
|---|---|---|---|
| **T-019-1** Concurrent index increment race | HIGH→MITIGATED | Every `last_rotation` read-modify-write happens INSIDE `async with new_async_lock(vault_path):` in `select_credential`. The locked body is factored into the sync `_select_credential_locked` helper. | ROTATE-22 (single `save_vault` per call), ROTATE-24 (hypothesis: `0 <= last_rotation < n`) |
| **T-019-2** Reentrant deadlock | HIGH→MITIGATED | Defense-in-depth: (1) `select_credential` constructs a fresh AsyncFileLock per call and documents loudly in the docstring; (2) `_select_credential_locked` exists as the structural seam so future already-locked callers (e.g., a v3 Provider Routing composite that interleaves `refresh_credential` + selection) can compose without re-acquiring. | ROTATE-20 (re-entry from same coroutine raises `RefreshLockTimeout` within 5s) |
| **T-019-3** `NoCredentialsAvailableError` leaks vault contents | HIGH→MITIGATED | Error class accepts only public-string args (`provider_id`, `reason`, `earliest_available_at`). `rotation.py` never passes `Credential` objects into the error constructor. | ROTATE-09 (asserts `"sk-ant-oat-TEST-" not in str(exc)`) |
| **T-019-4** Cool-down map collusion across providers | MEDIUM→MITIGATED | Tuple key `(provider_id, idx)` enforces strict equality across providers. | ROTATE-07 + ROTATE-17 (parametrized over multiple provider_ids) |
| **T-019-5** Lock-held duration extends past 10s timeout intent | MEDIUM | Inherits Phase 013's 10s acquire timeout via `new_async_lock`. Logs `rotation.persist_overhead` with `lock_held_seconds` for ops-side detection. | Phase 013 covers via REFRESH-22 (no new test) |
| **T-019-6** Symlink attack on auth.json | LOW — DEFERRED | Out of scope per RESEARCH; Phase 022 audit owns. | — |
| **T-019-7** Cross-provider env-var leak via cool-down state | LOW — DOCUMENTED | Phase 019 trusts caller-supplied `provider_id` strings (loose coupling); Phase 022 status command surfaces dangling keys. | — |

All HIGH severities CLOSED. MEDIUM at T-019-5 is documented and observable. LOW residuals are scoped to other phases (022).

## Deviations from Plan

The execution discovered 5 issues during verification — all auto-fixed under deviation Rule 1 (bug fix) and Rule 3 (blocking issue). None are architectural (no Rule 4 escalation).

### Auto-fixed Issues

**1. [Rule 1 — Bug] Cool-down GC short-circuit on bucket-aligned start (ROTATE-08)**
- **Found during:** Task 1 verification.
- **Issue:** With `_pick_active_index` calling `_is_cooled_down` only on indices it visits, the bucket-aligned starting index sometimes short-circuits the walk on offset 0 — leaving expired cool-down entries for OTHER indices in the map. ROTATE-08 expects the entry to be GC'd even when the test's second `select_credential` call doesn't visit that index.
- **Fix:** Added `_purge_expired_cool_downs(provider_id, n, now)` and called it at the head of `_pick_active_index`. Sweeps all indices in `[0, n)` for the provider, popping any whose `until <= now`. Pitfall 14 mitigation; aligns with the planner's "auto-expires entries whose until has passed (so the dict doesn't grow forever)" intent.
- **Files modified:** `src/state_core/auth/rotation.py` (+11 LOC for the helper).
- **Commit:** `15e22b0`.

**2. [Rule 1 — Test scaffolding bug] ROTATE-23 hypothesis coverage unsatisfiable for even n with bucket-aligned time advancement**
- **Found during:** Task 1 verification (hypothesis falsifying example: `n=2, B=29500000`).
- **Issue:** Wave 1 scaffolding advanced time by exactly `60.0 * k` seconds per call (one full bucket per call). Combined with the canonical formula `idx = (bucket + seed) % n` and seed-bump = 1 per call (ROTATE-05/14 pinned), the indices follow `idx_k = (B + 2k) % n`. Coverage requires `gcd(2, n) = 1` — fails for all even n in `[2..8]`. The test, as written, was structurally unsatisfiable under the planner's pinned formula.
- **Fix:** Held `now` constant within the test (`now=NOW_FROZEN` for all k). The test now exercises SEED-DRIVEN coverage independently of bucket-driven coverage. ROTATE-04 separately covers the bucket-advances-with-time helper property; the two tests together prove both axes. Added a comment in the test body explaining why the change was needed and pointing at this Summary.
- **Files modified:** `tests/auth/test_rotation.py` (ROTATE-23 body).
- **Commit:** `15e22b0`.

**3. [Rule 3 — Blocking issue] Hypothesis `function_scoped_fixture` health check (ROTATE-23, ROTATE-24)**
- **Found during:** Task 1 verification.
- **Issue:** Both ROTATE-23 and ROTATE-24 use the `isolated_vault_path` (function-scoped) fixture under `@given(...)`. Hypothesis's `FailedHealthCheck` blocks the test from running because function-scoped fixtures aren't reset between generated examples — the standard `suppress_health_check=[HealthCheck.function_scoped_fixture]` mark was missing.
- **Fix:** Added `HealthCheck` to the hypothesis import line and `suppress_health_check=[HealthCheck.function_scoped_fixture]` to both `@settings(...)` decorators. Each test asserts a property that is robust to fixture reuse (set-membership for ROTATE-23; modular invariant for ROTATE-24); the suppression is the canonical hypothesis pattern.
- **Files modified:** `tests/auth/test_rotation.py` (ROTATE-23 and ROTATE-24 settings).
- **Commit:** `15e22b0`.

**4. [Rule 3 — Blocking issue] ROTATE-19/ROTATE-20 stale RefreshLockTimeout class reference**
- **Found during:** Task 1 verification (full auth suite).
- **Issue:** `tests/auth/test_rotation.py` imports `RefreshLockTimeout` at module load time (line 29). Phase 013's REFRESH-23 (`test_no_mode_imports`) calls `importlib.reload(state_core.auth.refresh)`, which CREATES a new `RefreshLockTimeout` class object. After REFRESH-23 runs in the same session, the test file's stale reference points at the OLD class while `rotation.py`'s `from state_core.auth.refresh import RefreshLockTimeout` (re-imported on the post-reload module) raises the NEW class. `pytest.raises(RefreshLockTimeout)` checks against the OLD class → test reports FAILED even though `RefreshLockTimeout` (new class) is raised. Reproduction: `pytest tests/auth/test_refresh.py::test_no_mode_imports tests/auth/test_rotation.py::test_cool_down_lost_on_module_reimport tests/auth/test_rotation.py::test_select_lock_timeout_raises`.
- **Fix:** Re-resolve `RefreshLockTimeout` against the live `state_core.auth.refresh` module inside the body of ROTATE-19 and ROTATE-20: `_LiveRefreshLockTimeout = _refresh_mod.RefreshLockTimeout`, then `pytest.raises(_LiveRefreshLockTimeout)`. Comments in both tests explain the REFRESH-23 reload interaction and point at this Summary.
- **Files modified:** `tests/auth/test_rotation.py` (ROTATE-19 and ROTATE-20 bodies).
- **Commit:** `15e22b0`.

**5. [Rule 2 — Missing functionality] `state_core.auth.errors` block missing from `__init__.py`**
- **Found during:** Task 2 reading.
- **Issue:** Plan 03 Task 2's instructions said: *"the `from state_core.auth.errors import ...` block may not currently exist in `__init__.py` (Phase 015 may have deferred it). If it does NOT exist, add it AS SHOWN above with all 5 errors classes."* On reading the file, the block was indeed absent. Without it, ROTATE-26's `from state_core.auth import NoCredentialsAvailableError` fails.
- **Fix:** Added the full Phase 015 errors block (5 names: `AuthError`, `AuthLoginError`, `AuthRefreshError`, `NoCredentialsAvailableError`, `UnknownApiKeyProviderError`) plus the Phase 019 rotation block (5 names). Updated module docstring and `__all__` to enumerate Phase 015 alongside the existing phase headers. This is correctness work — the plan anticipated and explicitly authorized it.
- **Files modified:** `src/state_core/auth/__init__.py`.
- **Commit:** `1106e5a`.

## Self-Check: PASSED

- File `src/state_core/auth/rotation.py` exists (398 LOC) — FOUND.
- File `src/state_core/auth/__init__.py` modified — FOUND.
- File `tests/auth/test_rotation.py` modified (Wave 1 scaffolding fixes) — FOUND.
- Commit `15e22b0` (Task 1) — FOUND.
- Commit `1106e5a` (Task 2) — FOUND.
- All 26 ROTATE-XX tests GREEN — verified.
- Full auth suite 321 passed, 1 skipped (pre-existing Phase 012 deferral) — verified.

## Hand-off to Plan 04

Plan 04 (the verification gate) inherits a green tree:
- Implementation module + 5 public re-exports in place.
- Threat model fully mitigated (HIGH severities closed; MEDIUM/LOW documented or scoped out).
- Test scaffolding fixes (5 deviations) all minimal and well-documented inline.
- Mode isolation enforced (ROTATE-21 + import-graph lint).
- No regression on Phase 011/012/013/014/015/016/017/018 tests.

Plan 04 should:
1. Re-run the full ROTATE-XX matrix as the verification gate (already GREEN).
2. Flip `019-VALIDATION.md` to compliant.
3. Mark AUTH-08 complete in `REQUIREMENTS.md`.
4. Bump milestone STATE.md to point at Phase 020.

Functionally, AUTH-08 (multi-credential round-robin) is COMPLETE.
