---
phase: 019-multi-cred-round-robin-across
plan: 01
subsystem: state_core.auth.rotation (test scaffolding)
tags: [auth, multi-cred, rotation, tdd, wave-0, red]
requires:
  - state_core.auth.base (ApiKeyCredential, OAuthCredential)
  - state_core.auth.store (AuthVault, load_vault, save_vault)
  - state_core.auth.refresh (RefreshLockTimeout, _new_async_lock, _lock_path_for)
provides:
  - tests/auth/test_rotation.py (25 RED test stubs for ROTATE-01..20, 22..26)
  - tests/auth/conftest.py (Phase 019 fixtures appended)
  - tests/auth/test_import_graph.py (ROTATE-21 mode-isolation lint)
affects:
  - Wave 2 (Plan 02) — adds NoCredentialsAvailableError to state_core.auth.errors
  - Wave 3 (Plan 03) — creates state_core/auth/rotation.py
  - Wave 4 (Plan 04) — verifies all 26 GREEN
tech-stack:
  added: []
  patterns:
    - Late-bind try/except ImportError for autouse fixtures touching not-yet-existent modules
    - filelock factory monkeypatch (timeout=0.5s) for lock-busy timeout tests
    - Hypothesis @given + @settings(deadline=None) for async property tests with pytest-asyncio auto mode
key-files:
  created:
    - tests/auth/test_rotation.py
  modified:
    - tests/auth/conftest.py
    - tests/auth/test_import_graph.py
decisions:
  - rotation imports placed BEFORE errors imports so Wave 0 ImportError surfaces state_core.auth.rotation specifically (matches the planner-specified RED criterion grep)
  - ROTATE-22 spy installs at state_core.auth.rotation.save_vault (not state_core.auth.store.save_vault) because rotation.py will rebind via `from state_core.auth.store import save_vault`
  - ROTATE-19/20 use a filelock factory monkeypatch rather than reaching into LOCK_TIMEOUT_SECONDS (constant is captured at import time in refresh.py)
  - ROTATE-18 uses sync filelock.FileLock(timeout=0) — confirmed iter_active does not acquire the lock, since the sync handle holding it doesn't block read-only iteration
metrics:
  duration_minutes: ~25
  tasks: 3
  commits: 3
  files_created: 1
  files_modified: 2
  lines_added: 866
  completed_date: 2026-04-30
---

# Phase 019 Plan 01: Wave 0 RED Scaffolding for Multi-Cred Round-Robin Summary

**One-liner:** 26 named ROTATE-XX RED test stubs (25 in `test_rotation.py` + 1 in `test_import_graph.py`) plus 4 supporting fixtures in `conftest.py` — collection RED at `state_core.auth.rotation` ImportError, exactly as the TDD cardinal rule requires.

---

## Objective

Create Wave 0 RED scaffolding for Phase 019 (AUTH-08 / multi-cred round-robin). Every ROTATE-XX row in `019-RESEARCH.md §Validation Architecture` (26 rows) gets a corresponding failing test stub. Tests fail by design — they import `state_core.auth.rotation` (Wave 3) and `NoCredentialsAvailableError` (Wave 2), neither of which exists yet. Forces visible GREEN→RED→GREEN trajectory enforced by the plan-checker.

## Outcome

- 1 new test file: `tests/auth/test_rotation.py` (700 lines, 25 test functions)
- `tests/auth/conftest.py` extended with 4 Phase 019 fixtures (1 autouse + 3 plain)
- `tests/auth/test_import_graph.py` extended with 2 new tests (62 lines added)
- Wave 0 RED state confirmed: collection ImportError on `state_core.auth.rotation`
- 0 GREEN flukes — `pytest tests/auth/test_rotation.py 2>&1 | tail -5 | grep -cE "passed"` returns `0`
- Pre-existing 291 auth tests still pass (1 skipped, no new regressions)

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend `tests/auth/conftest.py` with Phase 019 fixtures | `1278fc2` | `tests/auth/conftest.py` |
| 2 | Write `tests/auth/test_rotation.py` — ROTATE-01..26 (Wave 0 RED) | `191f1bc` | `tests/auth/test_rotation.py` |
| 3 | Extend `tests/auth/test_import_graph.py` with ROTATE-21 (Wave 0 RED) | `44481e4` | `tests/auth/test_import_graph.py` |

## ROTATE → Test Function Mapping

| ROTATE row | File | Test function |
|---|---|---|
| ROTATE-01 | test_rotation.py | `test_select_n1_returns_idx0_and_bumps` |
| ROTATE-02 | test_rotation.py | `test_select_empty_raises` |
| ROTATE-03 | test_rotation.py | `test_select_missing_provider_raises` |
| ROTATE-04 | test_rotation.py | `test_bucket_advances_with_time` (parametrized x4) |
| ROTATE-05 | test_rotation.py | `test_last_rotation_persisted` |
| ROTATE-06 | test_rotation.py | `test_array_shape_preserved_after_selection` |
| ROTATE-07 | test_rotation.py | `test_cool_down_skipped_on_next_selection` |
| ROTATE-08 | test_rotation.py | `test_cool_down_auto_expires` |
| ROTATE-09 | test_rotation.py | `test_all_cooled_down_raises_with_earliest` (+ T-019-3 leak guard) |
| ROTATE-10 | test_rotation.py | `test_clear_rate_limited_removes_entry` |
| ROTATE-11 | test_rotation.py | `test_last_rotation_modulo_clamp` |
| ROTATE-12 | test_rotation.py | `test_mark_zero_until_clears` |
| ROTATE-13 | test_rotation.py | `test_bare_dict_coerced_p1_7` |
| ROTATE-14 | test_rotation.py | `test_migration_preserves_last_rotation` |
| ROTATE-15 | test_rotation.py | `test_cool_down_lost_on_module_reimport` |
| ROTATE-16 | test_rotation.py | `test_iter_active_yields_bucket_order` |
| ROTATE-17 | test_rotation.py | `test_iter_active_skips_cool_down` |
| ROTATE-18 | test_rotation.py | `test_iter_active_does_not_lock` |
| ROTATE-19 | test_rotation.py | `test_select_lock_timeout_raises` |
| ROTATE-20 | test_rotation.py | `test_select_reentrant_deadlock_raises` |
| **ROTATE-21** | **test_import_graph.py** | **`test_rotation_no_mode_imports`** + `test_rotation_imports_only_allowed_targets` |
| ROTATE-22 | test_rotation.py | `test_select_calls_save_vault_once` |
| ROTATE-23 | test_rotation.py | `test_every_cred_selected_over_n_rounds` (hypothesis) |
| ROTATE-24 | test_rotation.py | `test_last_rotation_invariant` (hypothesis) |
| ROTATE-25 | test_rotation.py | `test_select_deterministic_for_fixed_now` |
| ROTATE-26 | test_rotation.py | `test_public_reexports` |

26 rows; 25 tests in `test_rotation.py`, 1 (ROTATE-21) in `test_import_graph.py` (plus a companion `test_rotation_imports_only_allowed_targets` to keep the pattern consistent with the Phase 018 `test_loader_imports_only_allowed_targets`).

## Fixtures Added (conftest.py)

| Fixture | Scope | Purpose |
|---|---|---|
| `_clear_cool_down` | autouse function | Clears `state_core.auth.rotation._COOL_DOWN` before AND after each test (Pitfall 14 defense). Late-bind safe via `try/except ImportError`. |
| `busy_lock_holder` | function async | `@asynccontextmanager` factory that holds `_new_async_lock(vault_path)`. Used by ROTATE-19/20 lock-busy + reentrant-deadlock tests. |
| `vault_with_three_oauth` | function | In-memory `AuthVault` with 3 anthropic OAuth creds (far-future expires, `last_rotation={"anthropic": 0}`). |
| `vault_with_three_api_keys` | function | In-memory `AuthVault` with 3 openai `ApiKeyCredential`s (no expiry — pure rotation). |

All Phase 011/012/013/018 fixtures preserved byte-for-byte; total fixture count went from 15 → 19 (`@pytest.fixture` markers count: 19).

## Wave 0 RED Confirmation

```
$ pytest tests/auth/test_rotation.py 2>&1 | tail -8
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/auth/test_rotation.py:37: in <module>
    from state_core.auth.rotation import (  # Wave 3 (Plan 03)
E   ModuleNotFoundError: No module named 'state_core.auth.rotation'
=========================== short test summary info ============================
ERROR tests/auth/test_rotation.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.09s ===============================
```

```
$ pytest tests/auth/test_import_graph.py 2>&1 | tail -5
FAILED tests/auth/test_import_graph.py::test_rotation_no_mode_imports - Failed: Wave 0 RED: src/state_core/auth/rotation.py does not exist yet
FAILED tests/auth/test_import_graph.py::test_rotation_imports_only_allowed_targets - Failed: Wave 0 RED: src/state_core/auth/rotation.py does not exist yet
========================= 2 failed, 2 passed in 0.06s ==========================
```

```
$ pytest tests/auth/ --ignore=tests/auth/test_rotation.py 2>&1 | tail -3
================== 2 failed, 291 passed, 1 skipped in 45.03s ===================
```

Reading: collection of `test_rotation.py` is RED via `ModuleNotFoundError`. The 2 `test_import_graph.py` ROTATE-21 tests fail with the explicit `Wave 0 RED:` `pytest.fail` message. Phase 011/012/013/018 fixtures and tests still pass (291 passes; 1 pre-existing skip).

## Deviations from Plan

None — plan executed exactly as written, with two minor notes the plan itself flagged as Wave-0 acceptable choices:

- **Import order in `test_rotation.py`:** the planned order placed `from state_core.auth.errors import NoCredentialsAvailableError` first, but that would surface an `ImportError: cannot import name 'NoCredentialsAvailableError' from 'state_core.auth.errors'` at collection rather than the planner-specified rotation-flavored `ModuleNotFoundError`. Reordered so `from state_core.auth.rotation import …` runs first; this directly satisfies the criterion `grep -cE "ModuleNotFoundError.*state_core.auth.rotation|ImportError.*state_core.auth.rotation"` returning `>= 1`. No semantic change — both imports still fail RED.
- **ROTATE-19/20 lock timeout strategy:** the plan flagged that the `LOCK_TIMEOUT_SECONDS` module constant is captured at import time in `refresh.py:75`, so a `monkeypatch.setattr` against the constant alone would not flow through to `_new_async_lock`. Used the planner-suggested fallback: monkeypatch `_new_async_lock` itself to construct an `AsyncFileLock` with `timeout=0.5`. Patched at both `state_core.auth.refresh._new_async_lock` and `state_core.auth.rotation._new_async_lock` (the latter with `raising=False` because Wave 0 has not yet rebound it).

## Issues Encountered

- The `--fixtures` listing does not show autouse fixtures whose name starts with an underscore (consistent with the existing `_isolate_structlog_for_auth_tests`). Verified `_clear_cool_down` is firing via `pytest --setup-show tests/auth/test_store.py::test_validator_coerces_bare_dict` — output confirms `SETUP F _clear_cool_down` and matching `TEARDOWN F _clear_cool_down`.

## Self-Check: PASSED

Files created:
- `tests/auth/test_rotation.py` — FOUND
- `.planning/milestones/v2/phases/019-multi-cred-round-robin-across/019-01-SUMMARY.md` — FOUND (this file)

Files modified:
- `tests/auth/conftest.py` — FOUND (commit `1278fc2`)
- `tests/auth/test_import_graph.py` — FOUND (commit `44481e4`)

Commits exist on this branch:
- `1278fc2` test(019-01): extend tests/auth/conftest.py with Phase 019 fixtures — FOUND
- `191f1bc` test(019-01): add tests/auth/test_rotation.py — ROTATE-01..26 (Wave 0 RED) — FOUND
- `44481e4` test(019-01): extend test_import_graph.py with ROTATE-21 (Wave 0 RED) — FOUND

## Hand-off

- **Wave 2 / Plan 02:** add `NoCredentialsAvailableError(AuthError)` to `state_core.auth.errors` with fields `provider_id: str`, `reason: Literal["empty", "all_cooled_down"]`, `earliest_available_at: float | None`. Promote `_new_async_lock` to a public symbol if rotation needs to consume it without leading-underscore access (current Plan 02 contract: `_new_async_lock` stays private; rotation imports the underscored name). After Plan 02, `from state_core.auth.errors import NoCredentialsAvailableError` should resolve and the rotation imports remain RED.
- **Wave 3 / Plan 03:** create `src/state_core/auth/rotation.py` exporting `BUCKET_MS`, `_bucket_index`, `_COOL_DOWN`, `mark_rate_limited`, `clear_rate_limited`, `select_credential`, `iter_active_credentials`. Re-export the public names from `state_core/auth/__init__.py` for ROTATE-26.
- **Wave 4 / Plan 04:** verifier — run all 26 ROTATE rows, assert all GREEN, write the VALIDATION.md compliance flip.

## Pre-existing Auth Tests

Confirmed no regression:

```
$ pytest tests/auth/ --ignore=tests/auth/test_rotation.py 2>&1 | tail -3
FAILED tests/auth/test_import_graph.py::test_rotation_no_mode_imports - Failed: Wave 0 RED: src/state_core/auth/rotation.py does not exist yet
FAILED tests/auth/test_import_graph.py::test_rotation_imports_only_allowed_targets - Failed: Wave 0 RED: src/state_core/auth/rotation.py does not exist yet
================== 2 failed, 291 passed, 1 skipped in 45.03s ===================
```

The only failures are the 2 intended Wave 0 RED rotation import-graph tests added in this plan. All 291 prior auth tests still pass; the 1 skip is the pre-existing `tests/auth/test_store.py` skip unrelated to this plan.
