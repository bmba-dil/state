---
phase: 012-auth-json-vault-chmod-0600
plan: 01
subsystem: state_core.auth (vault test contract)
tags: [tests, RED-stubs, AUTH-06, P0-13, P1-7]
dependency-graph:
  requires:
    - 011-state-core-auth-base (Credential discriminated union + CredentialAdapter)
  provides:
    - Wave-0 RED test contract for state_core.auth.store (22 stubs)
    - Vault-aware conftest fixtures (auth_json_path, clean_state_auth_json_env, vault_with_one_oauth)
  affects:
    - 012-02 (must turn every STORE-01..STORE-21 test GREEN to ship)
tech-stack:
  added: []
  patterns:
    - "Conditional import + pytestmark.skipif keeps collection clean while preserving RED state until implementation lands"
    - "Hypothesis property test with HealthCheck.function_scoped_fixture suppression for the auth_json_path fixture"
    - "Autouse env-scrub fixture (clean_state_auth_json_env) prevents STATE_AUTH_JSON leakage between tests (Pitfall 8)"
key-files:
  created:
    - tests/auth/test_store.py
  modified:
    - tests/auth/conftest.py  # Task 1, committed previously at fa70d3c
decisions:
  - id: D-012-01-1
    summary: "Use conditional-import + pytestmark.skipif (not direct ImportError) so 22 tests are visible to --collect-only as a public catalogue Plan 02 must satisfy"
  - id: D-012-01-2
    summary: "Symlink-attack mitigation tracked as a skipped placeholder (test_symlink_attack_rejected) rather than dropped — keeps the gap traceable to Phase 022 audit"
metrics:
  duration: ~10 minutes
  tasks-completed: 2  # Task 1 (conftest) at fa70d3c, Task 2 (test_store.py) in this run
  completed-date: 2026-04-28
---

# Phase 012 Plan 01: Wave-0 RED Test Suite for state_core.auth.store — Summary

22 RED test stubs covering STORE-01..STORE-21 plus a Phase-022 symlink-defense placeholder, plus three vault-aware conftest fixtures. The test file is the executable contract Plan 02 must satisfy.

## Plan Objective vs Outcome

| Aspect | Plan | Outcome |
|--------|------|---------|
| `tests/auth/conftest.py` extended with `clean_state_auth_json_env`, `auth_json_path`, `vault_with_one_oauth` | Task 1 | Done — committed at `fa70d3c` (prior session) |
| `tests/auth/test_store.py` with 22 tests covering STORE-01..STORE-21 + symlink placeholder | Task 2 | Done — committed at `f67b4e4` (this session) |
| Phase 011 tests still GREEN (no regression) | Required | Verified: `tests/auth/test_base.py` 11/11 passing |
| 22 tests collect with zero collection errors | Required | Verified: `pytest --collect-only -q` lists all 22 |
| Tests are RED (skipped or failed) until Plan 02 lands | Required | Verified: 22 SKIPPED — Plan 02 surface not yet exported |

## Commits in This Plan

| Hash | Task | Message |
|------|------|---------|
| `fa70d3c` | 1 | `test(012-01): extend auth conftest with vault fixtures` (prior session) |
| `f67b4e4` | 2 | `test(012-01): add STORE-01..STORE-21 RED stubs for state_core.auth.store` (this session) |

## Tests Authored (22 total)

| ID | Test name | What it locks down |
|----|-----------|--------------------|
| STORE-01 | `test_atomic_write_mode` | `_atomic_write` produces a 0o600 file (kernel-applied via `os.open`) |
| STORE-02 | `test_atomic_write_overwrite_mode` | Overwrite of 0o644 target → result is 0o600 (rename inherits source mode; Pitfall 2) |
| STORE-03 | `test_atomic_write_crash_safety` | `os.replace` failure → original content preserved; no half-written file |
| STORE-04 | `test_load_missing_returns_empty` | `load_vault` on missing path → `AuthVault()`, file NOT created |
| STORE-05 | `test_load_wrong_mode_raises` | 0o644 file → `AuthVaultPermissionError(observed_mode=0o644)`; mode unchanged after rejection |
| STORE-06 | `test_load_round_trip` | `save_vault` → `load_vault` returns structurally-equal `AuthVault` |
| STORE-07 | `test_load_empty_file` | 0o600 zero-byte file → `AuthVault()` (Pitfall 3) |
| STORE-08 | `test_round_trip_single_cred_array` | n=1 → `providers[anthropic]` is a JSON array, never bare dict (P0-13/P1-7) |
| STORE-09 | `test_round_trip_multi_cred` | n=5 → list order preserved across save/load |
| STORE-10 | `test_validator_coerces_bare_dict` | `model_validate` coerces bare-dict → 1-element list |
| STORE-11 | `test_ensure_initialized_creates` | Missing file → 0o600 empty vault created |
| STORE-12 | `test_ensure_initialized_rejects_bad_mode` | Existing 0o644 file → raise; NO auto-chmod |
| STORE-13 | `test_ensure_initialized_idempotent` | Twice on valid file → byte-identical, mode still 0o600 |
| STORE-14 | `test_path_resolution_env_override` | `STATE_AUTH_JSON` env var honored |
| STORE-15 | `test_path_resolution_default` | Default = `<cwd>/.state/auth.json` |
| STORE-16 | `test_permission_error_carries_mode` | `.path` + `.observed_mode` exposed; message contains path + mode but NOT credential substrings |
| STORE-17 | `test_no_mode_imports` | Importing `state_core.auth.store` does NOT pull `state_build.*` / `state_teach.*` |
| STORE-18 | `test_hypothesis_round_trip` | Property: any `AuthVault` survives save→load→save→load (≤25 examples, deadline 2s) |
| STORE-19 | `test_discriminator_preserved` | Saved `OAuthCredential` loads back as `OAuthCredential` (not `ApiKeyCredential`) |
| STORE-20 | `test_deterministic_serialization` | Two `save_vault` calls → byte-identical output |
| STORE-21 | `test_last_rotation_round_trip` | Empty AND populated `last_rotation` round-trips cleanly |
| (bonus) | `test_symlink_attack_rejected` | `@pytest.mark.skip(reason="symlink TOCTOU mitigation deferred to Phase 022 audit")` placeholder for traceability |

## Verification Evidence

```
$ /Users/tmac/Projects/state/.venv/bin/python -m pytest tests/auth/test_store.py --collect-only -q | tail -5
tests/auth/test_store.py::test_deterministic_serialization
tests/auth/test_store.py::test_last_rotation_round_trip
tests/auth/test_store.py::test_symlink_attack_rejected

22 tests collected in 0.06s
```

```
$ /Users/tmac/Projects/state/.venv/bin/python -m pytest tests/auth/test_store.py -q | tail -3
ssssssssssssssssssssss                                                   [100%]
22 skipped in 0.06s
```

Skipped, NOT errored — every test is RED-by-skip until Plan 02 implements `state_core.auth.store`. The skip reason carries the captured `ImportError` so the gap is self-documenting.

```
$ /Users/tmac/Projects/state/.venv/bin/python -m pytest tests/auth/test_base.py -q | tail -3
...........                                                              [100%]
11 passed in 0.13s
```

Phase 011 regression check: 11/11 passing. The new conftest fixtures did NOT break any existing test.

## Deviations from Plan

None — plan executed exactly as written. The conditional-import pattern (try/except ImportError + pytestmark.skipif) is exactly the recommended shape from `<action>` step 4 of Task 2.

## Auth Gates

None.

## Issues Encountered

1. **Worktree HEAD ancestry** — the agent worktree was checked out at the older v1-completion commit (`5acaf88`), but Task 1 lives on the Phase 011/012 branch at `fa70d3c`. Per the worktree branch-check directive, I `git reset --soft fa70d3c…` to align HEAD, then `git checkout HEAD -- tests/auth/ src/state_core/auth/` to restore the working tree. No content was lost; this only re-pointed the agent's worktree at the right ancestor.
2. **Initial Write went to main project tree, not worktree** — the absolute path I used for `Write` resolved to `/Users/tmac/Projects/state/tests/auth/test_store.py` (main project) rather than the worktree's `tests/auth/test_store.py`. I copied the file into the worktree and removed the main-project copy before staging. The committed change is in the agent's worktree only.

## Self-Check: PASSED

- File `/Users/tmac/Projects/state/.claude/worktrees/agent-a88d1958a26101b68/tests/auth/test_store.py` exists.
- Commit `f67b4e4` exists in `git log` of the worktree branch (`worktree-agent-a88d1958a26101b68`).
- 22 tests collected; 22 skipped (RED state); Phase 011 GREEN preserved.

## Notes for Plan 02

- `tests/auth/test_store.py` imports `_atomic_write` and `_verify_mode` directly — they MUST be exported from `state_core.auth.store` (even though they are nominally private), otherwise the conditional-import block fails and every test stays SKIPPED.
- `AuthVaultPermissionError` MUST expose `.path` and `.observed_mode` attributes; STORE-16 asserts this directly.
- `AuthVault.providers` field-validator MUST coerce a bare dict to a 1-element list (STORE-10 feeds a raw dict and expects success, not `ValidationError`).
- `get_auth_json_path()` MUST `.resolve()` the env-var path (STORE-14 compares against `Path(...).resolve()`).
- The hypothesis test (STORE-18) uses 25 examples with a 2s deadline; if Plan 02's `save_vault`/`load_vault` is meaningfully slower than ~80 ms per round-trip, the deadline may need a bump.
- The symlink-defense placeholder (`test_symlink_attack_rejected`) intentionally `assert True` — Phase 022 audit will replace the body with an actual attack scenario.
