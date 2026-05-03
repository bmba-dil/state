---
phase: 012-auth-json-vault-chmod-0600
plan: 02
subsystem: auth
tags: [auth, vault, chmod, atomic-write, posix, pydantic, orjson]

# Dependency graph
requires:
  - phase: 011-state-core-auth-base
    provides: "Credential discriminated union + CredentialAdapter (round-tripped through AuthVault.providers)"
  - phase: 012-01
    provides: "tests/auth/test_store.py — 22 STORE-XX RED stubs + auth_json_path / vault_with_one_oauth fixtures"
provides:
  - "src/state_core/auth/store.py — AuthVault Pydantic model + load_vault/save_vault/ensure_initialized/get_auth_json_path"
  - "AuthVaultPermissionError(PermissionError) — refuse-to-proceed signal carrying .path + .observed_mode"
  - "_atomic_write — os.open(0o600) + os.fchmod + os.fsync + os.replace primitive (P0-13 owner)"
  - "_verify_mode — read-side mode check; raises without auto-chmod side-effect"
  - "Array-per-provider invariant (P1-7) enforced via dict[str, list[Credential]] + field_validator(mode='before')"
  - "Public re-exports from state_core.auth package for downstream phases"
affects:
  - "013-auth-refresh-filelock"
  - "014-anthropic-oauth-stealth"
  - "015-018 provider implementations"
  - "019-multi-credential-round-robin"
  - "021-opencode-import-first-run"
  - "022-cli-state-auth-status"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "POSIX atomic file write: os.open(O_WRONLY|O_CREAT|O_TRUNC, 0o600) + os.fchmod + os.fsync + os.close + os.replace"
    - "Pydantic field_validator(mode='before') for shape-coercion migration safety"
    - "Refuse-to-proceed posture for security-mode drift (no auto-chmod on read)"
    - "Path resolution mirroring state_core.database: env-override (STATE_AUTH_JSON) + cwd-relative default"

key-files:
  created:
    - "src/state_core/auth/store.py"
  modified:
    - "src/state_core/auth/__init__.py"

key-decisions:
  - "Sync API only — Phase 013 wraps load_vault/save_vault inside filelock; conflating sync I/O with async API would add overhead for ~1KB JSON."
  - "Refuse-to-proceed on chmod drift — no os.chmod side-effect in read path; AuthVaultPermissionError propagates to CLI (Phase 022) and daemon-boot (M-A6)."
  - "Literal '.tmp' suffix (no PID/random) — Phase 013's filelock guarantees single-writer; matches GSD-pi auth-storage.ts precedent."
  - "Symlink defense (Pitfall 6) deferred to Phase 022 audit — STORE-22 placeholder skipped with traceability note."
  - "Windows mode-check is a no-op (one-time structlog warning) — daemon-boot phase (M-A6) hard-blocks Windows per PROJECT.md 'Mac/Linux first'."
  - "field_validator(mode='before') coerces bare-dict provider values to 1-element list with structlog warning — observable migration path for Phase 021."

patterns-established:
  - "Atomic-write blueprint: os.open with mode arg + os.fchmod + memoryview EINTR-safe write loop + os.fsync + os.close + os.replace — to be reused by any future credential-adjacent vault."
  - "Defense-in-depth permissions: kernel applies mode at creation AND post-open fchmod AND read-side os.stat verification — all three layers."
  - "Pydantic invariant assertion before disk hit: belt-and-suspenders shape check (`assert all(isinstance(v, list) ...)`) in save_vault catches any future caller that sneaks past the validator."

requirements-completed:
  - AUTH-06
  - VAULT-01
  - VAULT-02
  - VAULT-03
  - VAULT-04
  - VAULT-05
  - VAULT-06
  - VAULT-07
  - VAULT-08
  - VAULT-09
  - VAULT-10
  - VAULT-11
  - VAULT-12
  - VAULT-13
  - VAULT-14
  - VAULT-15
  - VAULT-16
  - VAULT-17
  - VAULT-18
  - VAULT-19
  - VAULT-20
  - VAULT-21

# Metrics
duration: ~12min
completed: 2026-04-28
---

# Phase 012 Plan 02: AuthVault chmod-0600 store with array-per-provider invariant

**`.state/auth.json` vault with kernel-enforced chmod 0600 via os.open + os.fchmod + os.fsync + os.replace, refuse-to-proceed on mode drift, and Pydantic-enforced array-per-provider shape (P0-13/P1-7 owned).**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-28
- **Completed:** 2026-04-28
- **Tasks:** 2
- **Files modified:** 2 (store.py created/replaced, __init__.py updated)

## Accomplishments

- 21 STORE-XX tests driven RED → GREEN (1 SKIPPED is intentional symlink-defense placeholder for Phase 022)
- AUTH-06 satisfied: chmod 0o600 enforced at write (kernel via O_CREAT mode arg + os.fchmod) AND verified at read (os.stat & 0o777) AND on init (ensure_initialized rejects bad-mode existing files without auto-chmod)
- P0-13 owned: refuse-to-proceed posture — `AuthVaultPermissionError` raises with `.path` + `.observed_mode` for the CLI to render `chmod 600 <path>` remediation; no os.chmod side-effect anywhere in the read path
- P1-7 owned: `dict[str, list[Credential]]` strict shape + `field_validator(mode='before')` coerces bare-dict provider values to 1-element lists (with structlog warning) + pre-write `assert` in `save_vault` as belt-and-suspenders
- Atomic durability: `os.open(O_CREAT|O_TRUNC, 0o600)` → `os.fchmod` → EINTR-safe write loop → `os.fsync` → `os.close` → `os.replace` (same-fs rename via `path.with_name(name + '.tmp')`)
- Path resolution mirrors `state_core.database`: `STATE_AUTH_JSON` env override + `Path.cwd() / '.state' / 'auth.json'` default
- Mode isolation preserved: zero `state_build.*` / `state_teach.*` imports (STORE-17 verifies via `sys.modules` delta after reload)
- Determinism preserved: no `import time`, no `from datetime` (clock comes from caller per PROJECT.md cardinal rule)
- Phase 011 base re-exports preserved alongside 6 new Phase 012 names in `state_core.auth.__init__`

## Task Commits

1. **Task 1: Implement store.py (AuthVault + atomic primitives + public API)** — `f590d56` (feat)
2. **Task 2: Re-export Phase 012 surface from state_core.auth** — `9cb3350` (feat)

_Note: TDD per-task split (RED/GREEN/REFACTOR) was unnecessary — Plan 012-01 already authored the RED suite (22 skipped tests gated on `_STORE_AVAILABLE`). Each task here was a single GREEN commit landing the implementation that flips the gate._

## Files Created/Modified

- `src/state_core/auth/store.py` — full ~302-LOC implementation: VAULT_MODE/TMP_SUFFIX constants, AuthVaultPermissionError(PermissionError), AuthVault(BaseModel) with field_validator, get_auth_json_path, _verify_mode, _atomic_write, load_vault, save_vault, ensure_initialized
- `src/state_core/auth/__init__.py` — added 6 Phase 012 re-exports (AuthVault, AuthVaultPermissionError, ensure_initialized, get_auth_json_path, load_vault, save_vault) alongside existing Phase 011 names; private helpers (_atomic_write, _verify_mode) and constants (VAULT_MODE, TMP_SUFFIX) intentionally NOT re-exported

## Decisions Made

All key decisions were locked in by RESEARCH §Pattern 1-5 and Plan 012-02's `<action>` block (the plan included the complete module body). Implementation faithfully mirrored the blueprint with one minor cleanup:

- **Removed unused `sys` import** from the planned blueprint — the blueprint listed `import sys` in the imports block but never used it; mypy strict and ruff would flag this. Confirmed unused via `grep "sys\." src/state_core/auth/store.py` returning empty after implementation. Not tracked as a deviation — purely an editorial fix to match what the code actually requires.

## Deviations from Plan

None — plan executed exactly as written. The blueprint in `<action>` was a complete module body and turned RED tests GREEN on first run. No Rule 1/2/3 fixes triggered.

(See "Issues Encountered" for one mypy-config friction point that is pre-existing repo state, not a deviation.)

## Issues Encountered

**1. mypy import-untyped error when checking store.py in isolation (pre-existing repo issue, not introduced by this plan)**

- `python3 -m mypy --strict src/state_core/auth/store.py` reports: `Skipping analyzing "state_core.auth.base": module is installed, but missing library stubs or py.typed marker [import-untyped]`
- Root cause: the `state_core` package has no `py.typed` marker file anywhere in the source tree (verified via `find src -name py.typed`). Mypy treats imports of `state_core.auth.base` from `state_core.auth.store` as untyped third-party when run on a single file. The same error existed before this plan landed — `state_core/auth/__init__.py` (which already imported from `state_core.auth.base`) had it too.
- Verified clean: running `python3 -m mypy --strict state_core/auth/store.py` from inside `src/` (so mypy can resolve sibling modules through normal package discovery) reports `Success: no issues found in 1 source file`. The store.py code itself has zero strict-mode type errors — only the project-wide py.typed gap surfaces.
- Other source files (`src/state_core/projector.py`, `src/state_build/kernel.py`, `src/state_cli/main.py`, etc.) have 13 unrelated mypy errors all pre-existing the auth subsystem.
- **Resolution:** documented as pre-existing project state. Adding a `py.typed` marker to `src/state_core/` triggered a separate "Source file found twice under different module names" error from `explicit_package_bases` config, which is a project-wide mypy configuration issue beyond the scope of AUTH-06. Filing this as a hand-off note for the daemon-boot phase or a dedicated typing-cleanup phase.

**Verification matrix:**

| Check | Command | Expected | Actual |
|-------|---------|----------|--------|
| STORE suite | `pytest tests/auth/test_store.py -v` | 21 passed, 1 skipped | 21 passed, 1 skipped |
| Auth suite | `pytest tests/auth/ -q` | 32 passed, 1 skipped | 32 passed, 1 skipped (11 BASE + 21 STORE) |
| Non-auth suite | `pytest tests/ --ignore=tests/auth -q` | 321 passed | 321 passed (zero regressions) |
| Total | `pytest tests/ -q` | 353 passed, 1 skipped | 353 passed, 1 skipped |
| Determinism grep | `grep -nE "^import time\|^from datetime" src/state_core/auth/store.py` | empty | empty |
| Mode-isolation grep | `grep -nE "^from state_build\|^from state_teach\|^import state_build\|^import state_teach" src/state_core/auth/store.py` | empty | empty |
| Atomic-write primitives | `grep -E "os\.open\|os\.fchmod\|os\.fsync\|os\.replace" src/state_core/auth/store.py` | all 4 present | all 4 present |
| Smoke import (submodule) | `python3 -c "from state_core.auth.store import AuthVault, load_vault, save_vault, ensure_initialized, get_auth_json_path, AuthVaultPermissionError"` | ok | ok |
| Smoke import (package) | `python3 -c "from state_core.auth import ..."` (all 11 names) | ok | ok |
| LOC | `wc -l src/state_core/auth/store.py` | >= 150 | 302 |

## Self-Check

- [x] `src/state_core/auth/store.py` exists (302 LOC)
- [x] `src/state_core/auth/__init__.py` modified
- [x] `.planning/milestones/v2/phases/012-auth-json-vault-chmod-0600/012-02-SUMMARY.md` exists (this file)
- [x] Commit `f590d56` exists in `git log`
- [x] Commit `9cb3350` exists in `git log`
- [x] All 21 active STORE-XX tests pass; STORE-22 (symlink) skipped
- [x] Phase 011 BASE suite still passes (11 tests)
- [x] No regressions in 321 non-auth tests

## Self-Check: PASSED

## Next Phase Readiness

**Phase 013 (filelock-wrapped refresh) is unblocked.** Phase 013 will:
- Use `state_core.auth.store.get_auth_json_path()` to derive `auth.json.lock` location
- Wrap every `load_vault → mutate → save_vault` triple inside `filelock.FileLock`
- Implement double-check pattern (P0-6) for refresh races
- Reuse `_verify_mode` indirectly via `load_vault` (private import is the only legitimate consumer)

**Phases 014-018 (provider implementations) can begin in parallel:**
- Each provider's `login()` returns `OAuthCredential | ApiKeyCredential` and the dispatcher calls `save_vault` (under the Phase 013 lock)
- Array-shape preservation guaranteed by `field_validator` — provider authors don't need to wrap n=1 credentials manually

**Hand-off notes:**
- Phase 022 (CLI + audit) owns the symlink-attack mitigation (Pitfall 6) — STORE-22 placeholder is the visible-deferred test
- Daemon-boot phase (M-A6) owns the Windows hard-block decision (`_verify_mode` is a no-op on `os.name != "posix"` today)
- `.state/` parent-directory mode (currently uncontrolled — could be 0o755 world-listable) is a daemon-boot concern, not vault-layer
- Project-wide mypy `py.typed` marker / `explicit_package_bases` config cleanup is a separate dedicated typing phase

---
*Phase: 012-auth-json-vault-chmod-0600*
*Plan: 02*
*Completed: 2026-04-28*
